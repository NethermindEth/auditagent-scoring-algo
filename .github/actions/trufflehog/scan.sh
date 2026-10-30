#!/usr/bin/env bash
# Scans the repository for secrets using TruffleHog.
#
# SCAN_MODE selects what gets scanned:
#   git         commits. With BASE_SHA and HEAD_SHA set, only the commits in
#               BASE_SHA..HEAD_SHA (push/PR): every commit is checked, so a
#               secret added in one commit and removed in the next is still
#               caught. Without them, the full history: deleting a secret does
#               not remove it from git, so this finds already-leaked credentials
#               that still need rotating. Requires a full clone (fetch-depth: 0).
#   filesystem  every file under the current directory, including untracked and
#               gitignored ones. Used by the action's canary self-test.
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; NC='\033[0m'

REPO_ROOT=$(git rev-parse --show-toplevel)
SCAN_MODE="${SCAN_MODE:-git}"
BASE_SHA="${BASE_SHA:-}"
HEAD_SHA="${HEAD_SHA:-}"

# A push that creates a branch reports an all-zero "before" SHA, and a force
# push reports one that may no longer exist. Both fall back to the full history
# rather than scanning nothing.
if [[ -n "$BASE_SHA" ]] && ! git cat-file -e "${BASE_SHA}^{commit}" 2>/dev/null; then
  echo -e "  ${YELLOW}⚠${NC}  Base ${BASE_SHA} not found, scanning full history instead" >&2
  BASE_SHA=""
fi

case "$SCAN_MODE" in
  filesystem)
    SCAN_TARGET=(filesystem .)
    SCAN_LABEL="all files in the working tree" ;;
  git)
    SCAN_TARGET=(git "file://$REPO_ROOT")
    if [[ -n "$BASE_SHA" && -n "$HEAD_SHA" ]]; then
      SCAN_TARGET+=(--since-commit "$BASE_SHA" --branch "$HEAD_SHA")
      SCAN_LABEL="commits ${BASE_SHA:0:7}..${HEAD_SHA:0:7}"
    else
      SCAN_LABEL="full commit history"
    fi ;;
  *)
    echo "SCAN_MODE must be 'filesystem' or 'git', got '$SCAN_MODE'" >&2; exit 1 ;;
esac

echo -e "\n${CYAN}🔒 ${BOLD}Secret Detection${NC}  ${DIM}(TruffleHog · ${SCAN_MODE} scan)${NC}\n" >&2

EXCLUDE_FILE=$(mktemp)
RAW_OUTPUT=$(mktemp)
SCAN_ERR=$(mktemp)
trap 'rm -f "$EXCLUDE_FILE" "$RAW_OUTPUT" "$SCAN_ERR"' EXIT

# --exclude-paths entries are unanchored regexes: a bare `\.git` would also
# match `.github/` and `.gitignore` and silently skip every workflow file.
echo '(^|/)\.git/' > "$EXCLUDE_FILE"
[[ -f "$REPO_ROOT/.trufflehogignore" ]] && cat "$REPO_ROOT/.trufflehogignore" >> "$EXCLUDE_FILE"

EXTRA_FLAGS=(--exclude-paths "$EXCLUDE_FILE")
[[ -f "$REPO_ROOT/.trufflehog.yaml" ]] && EXTRA_FLAGS+=(--config "$REPO_ROOT/.trufflehog.yaml")

echo -e "  ${DIM}Scanning ${SCAN_LABEL}…${NC}" >&2

# Fail closed. TruffleHog exits 0 when it finds secrets (183 is only returned
# with --fail, which we deliberately don't pass — we format findings ourselves),
# so a non-zero status here always means the scan itself broke: missing binary,
# an uncompilable regex in .trufflehogignore, a bad --config, OOM, etc.
# Never let any of those be reported as "all clear".
if ! trufflehog "${SCAN_TARGET[@]}" \
  --no-update \
  --no-verification \
  --json \
  "${EXTRA_FLAGS[@]+"${EXTRA_FLAGS[@]}"}" >"$RAW_OUTPUT" 2>"$SCAN_ERR"; then
  echo -e "  ${RED}✖${NC}  ${RED}${BOLD}TruffleHog failed to run${NC} — scan did NOT complete\n" >&2
  cat "$SCAN_ERR" >&2
  echo -e "\n  ${YELLOW}⚠${NC}  This is a scan failure, not a clean result. Fix the error above." >&2
  echo -e "      A common cause is a non-regex pattern in ${YELLOW}.trufflehogignore${NC}" >&2
  echo -e "      (globs like ${YELLOW}*.pem${NC} are invalid regexes — use ${YELLOW}\\.pem\$${NC})." >&2
  exit 1
fi

# A jq failure (malformed output, jq missing) is likewise a broken scan.
if ! FINDINGS=$(jq -c 'select(.DetectorName != null)' <"$RAW_OUTPUT"); then
  echo -e "  ${RED}✖${NC}  ${RED}${BOLD}Could not parse TruffleHog output${NC} — scan did NOT complete\n" >&2
  head -n 20 "$RAW_OUTPUT" >&2
  exit 1
fi

if [[ -z "$FINDINGS" ]]; then
  echo -e "  ${GREEN}✔${NC}  ${GREEN}${BOLD}No secrets detected${NC} — all clear!\n" >&2
  exit 0
fi

COUNT=$(echo "$FINDINGS" | jq -s 'length')
echo -e "  ${RED}✖${NC}  ${RED}${BOLD}${COUNT} secret(s) detected${NC}\n" >&2
echo -e "${RED}┌──────────────────────────────────────────────────────┐${NC}" >&2
if [[ "$SCAN_MODE" == "git" && -z "$HEAD_SHA" ]]; then
  echo -e "${RED}│           SECRETS FOUND IN COMMIT HISTORY            │${NC}" >&2
else
  echo -e "${RED}│              PR BLOCKED — SECRETS FOUND              │${NC}" >&2
fi
echo -e "${RED}└──────────────────────────────────────────────────────┘${NC}\n" >&2

while IFS= read -r finding; do
  TYPE=$(echo "$finding" | jq -r '.DetectorName')
  RAW=$(echo "$finding"  | jq -r '(.Raw // "")[0:50]')
  # Filesystem and git sources report location under different keys — read both
  # so a history scan doesn't print "?" for every file and line.
  FILE=$(echo "$finding" | jq -r '.SourceMetadata.Data.Filesystem.file // .SourceMetadata.Data.Git.file // "?"')
  LINE=$(echo "$finding" | jq -r '.SourceMetadata.Data.Filesystem.line // .SourceMetadata.Data.Git.line // "?"')
  COMMIT=$(echo "$finding" | jq -r '.SourceMetadata.Data.Git.commit // ""')

  echo -e "  ${RED}▸${NC} ${BOLD}${TYPE}${NC}" >&2
  echo -e "    ${DIM}File  :${NC} ${FILE}${DIM} (line ${LINE})${NC}" >&2
  [[ -n "$COMMIT" ]] && echo -e "    ${DIM}Commit:${NC} ${COMMIT}" >&2
  echo -e "    ${DIM}Secret:${NC} ${YELLOW}${RAW:0:6}...${RAW: -4}${NC}\n" >&2
done <<< "$FINDINGS"

echo -e "  ${YELLOW}⚠${NC}  ${BOLD}What to do:${NC}" >&2
if [[ "$SCAN_MODE" == "git" ]]; then
  # These are already-committed secrets. They are readable by anyone with repo
  # access and by anyone who cloned earlier, so deleting the file changes
  # nothing — rotation is the only action that actually closes the exposure.
  echo -e "      1. ${BOLD}Rotate the credential now${NC} — it is in history and must be" >&2
  echo -e "         treated as compromised, even if the file was deleted since" >&2
  echo -e "      2. Replace it with an env var or a secrets-manager reference" >&2
  echo -e "      3. Optionally purge the blob (git-filter-repo / BFG) — disruptive," >&2
  echo -e "         requires a coordinated force-push; rotation matters more" >&2
else
  echo -e "      1. Remove the secret and rewrite the commit (git rebase -i)" >&2
  echo -e "      2. Use env vars or a secrets manager instead" >&2
fi
echo -e "      • False positive? Add ${YELLOW}trufflehog:ignore${NC} as a comment on that line" >&2
echo -e "        or add the path to ${YELLOW}.trufflehogignore${NC}" >&2
exit 1
