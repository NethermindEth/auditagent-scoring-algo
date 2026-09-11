"""Tests for the benchmark report generator: confusion-matrix math, aggregation,
and markdown rendering (all pure, no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scoring_algo import generate_report as gr
from scoring_algo.core.types import RepoStats


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("critical", "high"),
        ("High", "high"),
        ("medium", "medium"),
        ("moderate", "medium"),
        ("low", "low"),
        ("informational", "info"),
        ("note", "info"),
        ("Best Practices", "bestpractices"),
        ("", "unknown"),
        ("weird", "weird"),
    ],
)
def test_norm_sev(raw, expected):
    assert gr._norm_sev(raw) == expected


def test_norm_sev_non_string():
    assert gr._norm_sev(None) == "unknown"


def test_is_qa_severity():
    assert gr._is_qa_severity("Info") is True
    assert gr._is_qa_severity("Best Practices") is True
    assert gr._is_qa_severity("High") is False


def test_calc_confusion_metrics_basic():
    fp, fn, p, r, f1, p_w, r_w, f1_w = gr._calc_confusion_metrics(
        actual_findings=10, scan_findings=8, matched=6, partial=1, qa_findings=0
    )
    assert fp == 2  # adjusted_scan(8) - matched(6)
    assert fn == 4  # actual(10) - tp(6)
    assert p == pytest.approx(0.75)
    assert r == pytest.approx(0.6)
    assert f1 == pytest.approx(2 * 0.75 * 0.6 / (0.75 + 0.6))
    assert p_w == pytest.approx(7 / 8)  # partial counts as TP
    assert r_w == pytest.approx(0.7)


def test_calc_confusion_metrics_excludes_qa_from_scan_total():
    fp, fn, p, r, *_ = gr._calc_confusion_metrics(
        actual_findings=5, scan_findings=10, matched=3, partial=0, qa_findings=4
    )
    # adjusted_scan = 10 - 4 = 6 ; fp = 6 - 3
    assert fp == 3
    assert fn == 2
    assert p == pytest.approx(0.5)
    assert r == pytest.approx(0.6)


def test_calc_confusion_metrics_zero_guards_no_zerodivision():
    fp, fn, p, r, f1, p_w, r_w, f1_w = gr._calc_confusion_metrics(0, 0, 0, 0, 0)
    assert (fp, fn) == (0, 0)
    assert (p, r, f1, p_w, r_w, f1_w) == (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_count_matched_partial_fp():
    evaluated = [
        {"is_fp": True},
        {"is_match": True, "is_fp": False},
        {"is_partial_match": True, "is_fp": False},
        {"is_match": False, "is_partial_match": False, "is_fp": False},
    ]
    assert gr._count_matched_partial_fp(evaluated) == (1, 1, 1)


def test_summarize_truth_from_eval_excludes_fp_rows():
    evaluated = [
        {"is_fp": True, "severity_from_truth": "High"},
        {"is_fp": False, "severity_from_truth": "High"},
        {"is_fp": False, "severity_from_truth": "Info"},
    ]
    actual, qa_truth, counts = gr._summarize_truth_from_eval(evaluated)
    assert actual == 2
    assert qa_truth == 1
    assert counts == {"high": 1, "info": 1}


def _write_eval(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps(rows), encoding="utf-8")


def test_compute_repo_stats_without_scan_file(tmp_path: Path):
    eval_path = tmp_path / "repoA_results.json"
    _write_eval(
        eval_path,
        [
            {
                "is_match": True,
                "is_partial_match": False,
                "is_fp": False,
                "severity_from_truth": "High",
            },
            {
                "is_match": False,
                "is_partial_match": True,
                "is_fp": False,
                "severity_from_truth": "Medium",
            },
            {
                "is_match": False,
                "is_partial_match": False,
                "is_fp": True,
                "severity_from_junior_auditor": "Low",
            },
        ],
    )
    stats = gr.compute_repo_stats(eval_path, scan_root=None)
    assert stats.repo == "repoA"
    assert stats.matched == 1
    assert stats.partial == 1
    assert stats.actual_findings == 2  # non-FP rows
    # no scan file -> scan_findings approximated as matched + partial + fps = 3
    assert stats.scan_findings == 3
    assert stats.false_positives == 2  # adjusted_scan(3) - matched(1)


def test_compute_repo_stats_with_scan_file(tmp_path: Path):
    (tmp_path / "baseline").mkdir()
    _write_eval(
        tmp_path / "repoB_results.json",
        [
            {
                "is_match": True,
                "is_partial_match": False,
                "is_fp": False,
                "severity_from_truth": "High",
            }
        ],
    )
    (tmp_path / "baseline" / "repoB_results.json").write_text(
        json.dumps(
            [
                {"Issue": "a", "Severity": "High"},
                {"Issue": "b", "Severity": "Info"},  # QA -> excluded from adjusted scan total
            ]
        ),
        encoding="utf-8",
    )
    stats = gr.compute_repo_stats(tmp_path / "repoB_results.json", scan_root=tmp_path / "baseline")
    assert stats.scan_findings == 2
    assert stats.qa_findings == 1  # the Info finding
    assert stats.scan_severity_counts == {"high": 1, "info": 1}


def test_aggregate_overall_sums_repos(tmp_path: Path):
    e1, e2 = tmp_path / "a_results.json", tmp_path / "b_results.json"
    _write_eval(e1, [{"is_match": True, "is_fp": False, "severity_from_truth": "High"}])
    _write_eval(e2, [{"is_match": True, "is_fp": False, "severity_from_truth": "High"}])
    agg = gr.aggregate_overall([gr.compute_repo_stats(e1, None), gr.compute_repo_stats(e2, None)])
    assert agg.repo == "ALL"
    assert agg.matched == 2
    assert agg.actual_findings == 2


def test_generate_markdown_report_end_to_end(tmp_path: Path):
    bench = tmp_path / "benchmarks"
    bench.mkdir()
    _write_eval(
        bench / "repoA_results.json",
        [
            {
                "is_match": True,
                "is_partial_match": False,
                "is_fp": False,
                "severity_from_truth": "High",
            },
            {
                "is_match": False,
                "is_partial_match": False,
                "is_fp": True,
                "severity_from_junior_auditor": "High",
            },
        ],
    )
    gr.generate_markdown_report(benchmarks=bench, out=Path("REPORT.md"))
    report = (bench / "REPORT.md").read_text()
    assert "# Benchmark Report" in report
    assert "| repoA |" in report
    assert "| ALL |" in report


def test_generate_markdown_report_raises_on_missing_dir(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        gr.generate_markdown_report(benchmarks=tmp_path / "nope", out=Path("REPORT.md"))


def test_generate_markdown_report_raises_on_empty_dir(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        gr.generate_markdown_report(benchmarks=empty, out=Path("REPORT.md"))


def test_render_markdown_includes_per_repo_severity_tables():
    stats = RepoStats(
        repo="repoA",
        actual_findings=2,
        scan_findings=3,
        matched=1,
        partial=0,
        qa_findings=0,
        false_positives=2,
        false_negatives=1,
        precision=0.33,
        recall=0.5,
        f1=0.4,
        precision_with_partial=0.33,
        recall_with_partial=0.5,
        f1_with_partial=0.4,
        truth_severity_counts={"high": 1, "medium": 1},
        scan_severity_counts={"high": 2, "low": 1},
        totals={},
    )
    md = gr.render_markdown([stats], stats)
    assert "| repoA |" in md
    assert "Truth severity counts:" in md
    assert "Scan severity counts (from scan source):" in md


def test_compute_repo_stats_on_empty_eval_is_all_zeros(tmp_path: Path):
    eval_path = tmp_path / "repoZ_results.json"
    eval_path.write_text("[]", encoding="utf-8")
    stats = gr.compute_repo_stats(eval_path, scan_root=None)
    assert stats.actual_findings == 0
    assert stats.matched == 0
    assert stats.precision == 0.0 and stats.recall == 0.0 and stats.f1 == 0.0  # no ZeroDivision


def test_generate_markdown_report_with_empty_eval_file(tmp_path: Path):
    bench = tmp_path / "benchmarks"
    bench.mkdir()
    (bench / "repoZ_results.json").write_text("[]", encoding="utf-8")
    gr.generate_markdown_report(benchmarks=bench, out=Path("REPORT.md"))
    report = (bench / "REPORT.md").read_text()
    assert "# Benchmark Report" in report
    assert "| repoZ |" in report  # renders a zero-row without crashing
