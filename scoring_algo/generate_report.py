# flake8: noqa E501
# generate_report.py
# Usage examples:
#   python generate_report.py --benchmarks ../external-benchmark/benchmarks --out REPORT.md
#   python generate_report.py --benchmarks ./benchmarks --scan-root ../external-benchmark/auditagent --out REPORT.md
# Notes:
# - If --scan-root is provided and <scan-root>/<repo>_results.json exists, we will use its length for scanFindings.
# - If not provided (or file missing), scanFindings is derived as matched + partial + fp + qaFindings so that adjustedScanFindings = matched + partial + fp (same effect as the UI).

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scoring_algo.core.types import RepoStats


def _norm_sev(value: str) -> str:
    if not isinstance(value, str):
        return "unknown"
    s = value.strip().lower()
    if s in ("best practices", "best practice", "best_practices", "bp", "bestpractices"):
        return "bestpractices"
    if s.startswith("crit") or "critical" in s:
        return "high"
    if "high" in s:
        return "high"
    if "medium" in s or "mod" in s:
        return "medium"
    if "low" in s:
        return "low"
    if "info" in s or "note" in s or "hint" in s:
        return "info"
    return s or "unknown"


def _is_qa_severity(sev: str) -> bool:
    sev = _norm_sev(sev)
    return sev in ("info", "bestpractices")


def _load_json(path: Path) -> Optional[object]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _parse_repo_name(file_path: Path) -> str:
    # <repo>_results.json -> <repo>
    name = file_path.stem
    if name.endswith("_results"):
        name = name[: -len("_results")]
    return name


def _calc_confusion_metrics(
    actual_findings: int, scan_findings: int, matched: int, partial: int, qa_findings: int
) -> Tuple[int, int, float, float, float, float, float, float]:
    # Base metrics ("real" F1):
    # - Do NOT exclude QA from scan results (use raw scan_findings)
    # - Do NOT count partial as TP (and also not as FP)
    raw_scan = max(0, scan_findings)

    true_positives = matched
    false_negatives = max(0, actual_findings - true_positives)
    false_positives = max(0, raw_scan - matched - partial)

    precision = (true_positives / raw_scan) if raw_scan > 0 else 0.0
    recall = (true_positives / actual_findings) if actual_findings > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    # With partial metrics:
    # - Include partial in TP
    # - Exclude QA from scan results
    adjusted_scan = max(0, scan_findings - qa_findings)
    tp_with_partial = matched + partial
    _fn_with_partial = max(0, actual_findings - tp_with_partial)  # noqa F841
    precision_with_partial = (tp_with_partial / adjusted_scan) if adjusted_scan > 0 else 0.0
    recall_with_partial = (tp_with_partial / actual_findings) if actual_findings > 0 else 0.0
    f1_with_partial = (
        2
        * precision_with_partial
        * recall_with_partial
        / (precision_with_partial + recall_with_partial)
        if (precision_with_partial + recall_with_partial) > 0
        else 0.0
    )

    return (
        false_positives,
        false_negatives,
        precision,
        recall,
        f1,
        precision_with_partial,
        recall_with_partial,
        f1_with_partial,
    )


def _format_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _summarize_truth_from_eval(evaluated: List[dict]) -> Tuple[int, int, Dict[str, int]]:
    # actual_findings = total count of truth issues (ALL severities), excluding only FP rows
    # qa_findings_truth = count of truth issues that are QA severities (for info table only)
    truth_counts: Dict[str, int] = defaultdict(int)
    actual = 0
    qa_truth = 0
    for f in evaluated:
        if f.get("is_fp") is True:
            continue
        sev_truth = f.get("severity_from_truth") or ""
        truth_counts[_norm_sev(sev_truth)] += 1
        if _is_qa_severity(sev_truth):
            qa_truth += 1
        # Count ALL severities toward the total truth count
        actual += 1
    return actual, qa_truth, dict(truth_counts)


def _count_matched_partial_fp(evaluated: List[dict]) -> Tuple[int, int, int]:
    matched = 0
    partial = 0
    fps = 0
    for f in evaluated:
        if f.get("is_fp") is True:
            fps += 1
            continue
        if f.get("is_match") is True:
            matched += 1
        elif f.get("is_partial_match") is True:
            partial += 1
    return matched, partial, fps


def _scan_counts_from_scan_file(scan_items: List[dict]) -> Dict[str, int]:
    out: Dict[str, int] = defaultdict(int)
    for it in scan_items:
        sev = _norm_sev(it.get("Severity") or it.get("severity") or "")
        out[sev] += 1
    return dict(out)


def _count_qa_from_scan_counts(scan_counts: Dict[str, int]) -> int:
    # QA is derived from the scan results (Info + Best Practices), matching the frontend
    return int(scan_counts.get("info", 0)) + int(scan_counts.get("bestpractices", 0))


def compute_repo_stats(eval_path: Path, scan_root: Optional[Path]) -> RepoStats:
    evaluated = _load_json(eval_path) or []
    if not isinstance(evaluated, list):
        evaluated = []

    repo = _parse_repo_name(eval_path)

    matched, partial, fps = _count_matched_partial_fp(evaluated)
    actual, _qa_from_truth, truth_counts = _summarize_truth_from_eval(evaluated)

    scan_findings = 0
    scan_counts: Dict[str, int] = {}
    if scan_root:
        scan_path = scan_root / f"{repo}_results.json"
        scan_items = _load_json(scan_path)
        if isinstance(scan_items, list):
            scan_findings = len(scan_items)
            scan_counts = _scan_counts_from_scan_file(scan_items)

    # QA findings are sourced from the scan severities (Info + Best Practices)
    qa_from_scan = _count_qa_from_scan_counts(scan_counts) if scan_counts else 0

    if scan_findings == 0:
        # If we don't have the scan file, approximate scan length so that
        # adjustedScanFindings = matched + partial + fps (same effect as UI)
        # Since qa_from_scan is unknown, set it to 0 and fold all into scan length
        scan_findings = matched + partial + fps

    false_positives, false_negatives, precision, recall, f1, p_w, r_w, f1_w = (
        _calc_confusion_metrics(
            actual_findings=actual,
            scan_findings=scan_findings,
            matched=matched,
            partial=partial,
            qa_findings=qa_from_scan,
        )
    )

    totals = {
        "actual_findings": actual,
        "scan_findings": scan_findings,
        "matched": matched,
        "partial": partial,
        "qa_findings": qa_from_scan,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }

    return RepoStats(
        repo=repo,
        actual_findings=actual,
        scan_findings=scan_findings,
        matched=matched,
        partial=partial,
        qa_findings=qa_from_scan,
        false_positives=false_positives,
        false_negatives=false_negatives,
        precision=precision,
        recall=recall,
        f1=f1,
        precision_with_partial=p_w,
        recall_with_partial=r_w,
        f1_with_partial=f1_w,
        truth_severity_counts=truth_counts,
        scan_severity_counts=scan_counts,
        totals=totals,
    )


def aggregate_overall(stats: List[RepoStats]) -> RepoStats:
    agg = RepoStats(
        repo="ALL",
        actual_findings=0,
        scan_findings=0,
        matched=0,
        partial=0,
        qa_findings=0,
        false_positives=0,
        false_negatives=0,
        precision=0.0,
        recall=0.0,
        f1=0.0,
        precision_with_partial=0.0,
        recall_with_partial=0.0,
        f1_with_partial=0.0,
        truth_severity_counts={},
        scan_severity_counts={},
        totals={},
    )
    truth_counts: Dict[str, int] = defaultdict(int)
    scan_counts: Dict[str, int] = defaultdict(int)

    for s in stats:
        agg.actual_findings += s.actual_findings
        agg.scan_findings += s.scan_findings
        agg.matched += s.matched
        agg.partial += s.partial
        agg.qa_findings += s.qa_findings
        for k, v in s.truth_severity_counts.items():
            truth_counts[k] += v
        for k, v in s.scan_severity_counts.items():
            scan_counts[k] += v

    fp, fn, p, r, f1, p_w, r_w, f1_w = _calc_confusion_metrics(
        actual_findings=agg.actual_findings,
        scan_findings=agg.scan_findings,
        matched=agg.matched,
        partial=agg.partial,
        qa_findings=agg.qa_findings,
    )
    agg.false_positives = fp
    agg.false_negatives = fn
    agg.precision = p
    agg.recall = r
    agg.f1 = f1
    agg.precision_with_partial = p_w
    agg.recall_with_partial = r_w
    agg.f1_with_partial = f1_w
    agg.truth_severity_counts = dict(truth_counts)
    agg.scan_severity_counts = dict(scan_counts)
    agg.totals = {
        "actual_findings": agg.actual_findings,
        "scan_findings": agg.scan_findings,
        "matched": agg.matched,
        "partial": agg.partial,
        "qa_findings": agg.qa_findings,
        "false_positives": agg.false_positives,
        "false_negatives": agg.false_negatives,
    }
    return agg


def render_markdown(stats: List[RepoStats], overall: RepoStats) -> str:
    dt = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: List[str] = []
    lines.append("# Benchmark Report")
    lines.append("")
    lines.append(f"_Generated: {dt}_")
    lines.append("")

    # Overview table
    lines.append("## Overview")
    lines.append("")
    lines.append(
        "| Repo | Truth | AI Scan | QA | TP | Partial | FP | FN | Precision | Recall | F1 | P(w/partial) | R(w/partial) | F1(w/partial) |"
    )
    lines.append(
        "|------|--------|------|----|----|---------|----|----|-----------|--------|----|--------------|--------------|---------------|"
    )
    for s in stats + [overall]:
        lines.append(
            f"| {s.repo} | {s.actual_findings} | {s.scan_findings} | {s.qa_findings} | {s.matched} | {s.partial} | {s.false_positives} | {s.false_negatives} | "
            f"{_format_pct(s.precision)} | {_format_pct(s.recall)} | {_format_pct(s.f1)} | {_format_pct(s.precision_with_partial)} | "
            f"{_format_pct(s.recall_with_partial)} | {_format_pct(s.f1_with_partial)} |"
        )
    lines.append("")

    # Per-repo sections
    for s in stats:
        lines.append(f"## {s.repo}")
        lines.append("")
        lines.append("- **actual findings (truth, all severities)**: " + str(s.actual_findings))
        lines.append("- **scan findings (raw)**: " + str(s.scan_findings))
        lines.append("- **QA findings (from scan: Info + Best Practices)**: " + str(s.qa_findings))
        lines.append("- **true positives (exact matches)**: " + str(s.matched))
        lines.append("- **partial matches**: " + str(s.partial))
        lines.append("- **false positives (adjusted)**: " + str(s.false_positives))
        lines.append("- **false negatives**: " + str(s.false_negatives))
        lines.append("- **precision**: " + _format_pct(s.precision))
        lines.append("- **recall**: " + _format_pct(s.recall))
        lines.append("- **F1**: " + _format_pct(s.f1))
        lines.append("- **precision w/ partial**: " + _format_pct(s.precision_with_partial))
        lines.append("- **recall w/ partial**: " + _format_pct(s.recall_with_partial))
        lines.append("- **F1 w/ partial**: " + _format_pct(s.f1_with_partial))
        lines.append("")
        if s.truth_severity_counts:
            lines.append("Truth severity counts:")
            lines.append("")
            lines.append("| high | medium | low | info | bestpractices |")
            lines.append("|------|--------|-----|------|----------------|")
            lines.append(
                "| "
                + " | ".join(
                    str(s.truth_severity_counts.get(k, 0))
                    for k in ("high", "medium", "low", "info", "bestpractices")
                )
                + " |"
            )
            lines.append("")
        if s.scan_severity_counts:
            lines.append("Scan severity counts (from scan source):")
            lines.append("")
            lines.append("| high | medium | low | info | bestpractices |")
            lines.append("|------|--------|-----|------|----------------|")
            lines.append(
                "| "
                + " | ".join(
                    str(s.scan_severity_counts.get(k, 0))
                    for k in ("high", "medium", "low", "info", "bestpractices")
                )
                + " |"
            )
            lines.append("")
    return "\n".join(lines)


def generate_markdown_report(benchmarks: Path, out: Path, scan_root: Optional[Path] = None) -> None:
    bench_dir: Path = benchmarks
    if not bench_dir.exists() or not bench_dir.is_dir():
        raise FileNotFoundError(f"Benchmarks directory not found: {bench_dir}")

    results_files = sorted(
        p for p in bench_dir.iterdir() if p.is_file() and p.name.endswith("_results.json")
    )
    if not results_files:
        raise FileNotFoundError(f"No *_results.json files found in {bench_dir}")

    stats: List[RepoStats] = []
    for p in results_files:
        stats.append(compute_repo_stats(p, scan_root))

    overall = aggregate_overall(stats)
    md = render_markdown(stats, overall)
    final_out = out if out.is_absolute() else (bench_dir / out)
    final_out.write_text(md, encoding="utf-8")
    print(f"Wrote report to {final_out}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate Markdown benchmark report from evaluated results."
    )
    parser.add_argument(
        "--benchmarks",
        type=Path,
        required=True,
        help="Path to benchmarks folder with *_results.json files",
    )
    parser.add_argument(
        "--scan-root",
        type=Path,
        default=None,
        help="Optional path to original scan results (e.g., auditagent/ or hound/)",
    )
    parser.add_argument(
        "--out", type=Path, default=Path("REPORT.md"), help="Output Markdown file path"
    )
    args = parser.parse_args()

    generate_markdown_report(args.benchmarks, args.out, args.scan_root)


if __name__ == "__main__":
    main()
