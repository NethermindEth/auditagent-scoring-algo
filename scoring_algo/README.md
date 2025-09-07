## Python Benchmark Runner

Minimal standalone Python CLI to run the same evaluation pipeline as the Next.js app, but able to work against an external data repo. It:

- Targets an external data root with folders like: `auditagent/`, `hound/`, `repos/`, `source of truth/`
- Reads scan results from `<data_root>/<scan_source>/<repo>_results.json` (e.g., `auditagent/` or `hound/`)
- Reads source-of-truth findings from `<data_root>/source of truth/<repo>.json`
- Evaluates per-batch with the same prompt, running two iterations per batch by default
- Post-processes partial matches and appends false positives
- Writes results to `benchmarks/<benchmark-date>/<repo>_results.json`

### Prerequisites

- Python 3.10+ recommended
- API keys as environment variables (set only what you need):
  - `OPENAI_API_KEY`
  - `GEMINI_API_KEY`

### Install

```bash
cd python-benchmark
python -m venv .venv
. .venv/Scripts/activate  # Windows Git Bash / PowerShell equivalent
pip install -r requirements.txt
```

### Usage

```bash
# Single repo (name without .json)
python main.py --repo cantina_minimal-delegation_2025_04 \
  --data-root ../external-benchmark \
  --scan-source auditagent \
  --output-root ../external-benchmark/benchmarks \
  --model o4-mini --iterations 2 --batch-size 10 --debug-prompt false

# Multiple repos from a list file (comments allowed) or from a directory of .json files
python main.py --repos-file ../external-benchmark/repos/repos.txt \
  --data-root ../external-benchmark --scan-source hound --output-root ../external-benchmark/benchmarks

# Or pass the repos directory; stems of files (without .json) are used as repo names
python main.py --repos-file ../external-benchmark/repos \
  --data-root ../external-benchmark --scan-source auditagent --output-root ../external-benchmark/benchmarks
```

Flags:

- `--repo`: single repo name (without `.json`) to evaluate
- `--repos-file`: either (1) a directory whose file stems become repo names, (2) a JSON/JSONC array of strings or `{ name, disabled }` objects, or (3) a newline list (`.txt`) supporting comments with `#` or `//`
- `--data-root`: the external repo root containing `auditagent/`, `hound/`, `repos/`, `source of truth/`
- `--scan-source`: which folder under data-root to read scan results from (`auditagent` or `hound`)
- `--output-root`: where to write `<repo>_results.json` (you can point it inside the external repo)
- `--model` (optional): LLM model name (default: `o4-mini`); provider is auto-detected. Supports OpenAI (incl. `o4-*`, `gpt-4o*`) and Gemini.
- `--iterations` (optional): number of LLM runs per batch prompt (default: 2)
- `--batch-size` (optional): number of scan findings per batch (default: 10)
- `--debug-prompt` (optional): store prompts alongside results (default: false)

Examples:

```bash
# Evaluate a single repo using auditagent results and write next to the external repo
python main.py --repo cantina_minimal-delegation_2025_04 \
  --data-root ../external-benchmark --scan-source auditagent --output-root ../external-benchmark/benchmarks

# Evaluate all repos listed by file names in the repos directory using hound results
python main.py --repos-file ../external-benchmark/repos \
  --data-root ../external-benchmark --scan-source hound --output-root ../external-benchmark/benchmarks
```

### Notes

- Output JSON structure matches the frontend (`EvaluatedFinding` array), including partial-match post-processing and false-positive entries.
- If using OpenAI `o4-*` models, the runner uses the Responses API; for `gpt-4o*`, it uses Chat Completions with JSON mode.
- When using `--repos-file` as a directory, repo names are derived from file stems; `.json` is stripped automatically. You can “comment out” by renaming files with a leading `#`, `//`, or `_`.
- When using `--repos-file` as a list file, lines starting with `#` or `//` are ignored; for JSON arrays, objects with `{ disabled: true }` are skipped.


