"""Tests for the evaluation pipeline: text truncation, partial-match
post-processing, and an end-to-end ``run_evaluation`` over a mocked judge."""

from __future__ import annotations

import json
from pathlib import Path

from scoring_algo.core import batching, evaluate
from scoring_algo.core.evaluate import _truncate, post_process_partial_matches
from tests._helpers import FakeLLMClient, make_evaluated, make_finding, write_dataset

EXACT = {"is_match": True, "is_partial_match": False}
FALSE = {"is_match": False, "is_partial_match": False}


def test_truncate():
    assert _truncate("short", 60) == "short"
    out = _truncate("a" * 100, 10)
    assert len(out) == 10 and out.endswith("…")


def test_post_process_demotes_partial_conflicting_with_tp():
    results = [
        make_evaluated(is_match=True, index=1),
        make_evaluated(is_partial_match=True, index=1),
    ]
    processed = post_process_partial_matches(results)
    assert processed[0].is_match is True
    assert processed[1].is_partial_match is False  # already a TP at index 1


def test_post_process_dedupes_repeated_partials():
    results = [
        make_evaluated(is_partial_match=True, index=2),
        make_evaluated(is_partial_match=True, index=2),
    ]
    processed = post_process_partial_matches(results)
    assert processed[0].is_partial_match is True
    assert processed[1].is_partial_match is False


def test_post_process_keeps_unique_partial():
    results = [make_evaluated(is_partial_match=True, index=3)]
    processed = post_process_partial_matches(results)
    assert processed[0].is_partial_match is True


def test_run_evaluation_end_to_end_with_mocked_judge(tmp_path: Path, monkeypatch):
    data_root = tmp_path / "data"
    out_root = tmp_path / "bench"
    write_dataset(
        data_root,
        "repoA",
        truth=[
            {"title": "T1", "severity": "high", "description": "d1", "file": "C.sol"},
            {"title": "T2", "severity": "medium", "description": "d2", "file": "C.sol"},
        ],
        scan=[
            {"Issue": "S1", "Severity": "High", "Description": "d1", "Contracts": ["C.sol"]},
            {"Issue": "S2", "Severity": "Low", "Description": "d2", "Contracts": ["C.sol"]},
            {"Issue": "S3", "Severity": "High", "Description": "fp", "Contracts": ["C.sol"]},
        ],
    )
    # Scripted judge: truth[0] -> exact match at scan index 0; truth[1] -> no match (FN).
    # Each truth finding consumes two agreeing calls (early-exit on the 3rd).
    script = [
        make_finding(index=0, **EXACT),
        make_finding(index=0, **EXACT),
        make_finding(index=-1, **FALSE),
        make_finding(index=-1, **FALSE),
    ]
    fake = FakeLLMClient(responses=script)
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)

    evaluate.run_evaluation(
        repo_name="repoA",
        data_root=data_root,
        scan_source="auditagent",
        output_root=out_root,
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
    )

    result = json.loads((out_root / "repoA_results.json").read_text())
    tp = sum(1 for r in result if r["is_match"])
    fp = sum(1 for r in result if r["is_fp"])
    fn = sum(
        1 for r in result if not r["is_match"] and not r["is_partial_match"] and not r["is_fp"]
    )
    assert tp == 1  # T1 matched
    assert fn == 1  # T2 unmatched
    assert fp == 2  # scan S2 (Low) and S3 (High), both unmatched and non-Info


def test_run_evaluation_skips_info_severity_false_positive(tmp_path: Path, monkeypatch):
    """An unmatched Info/Best-Practices scan finding is QA noise, not a false positive."""
    data_root = tmp_path / "data"
    out_root = tmp_path / "bench"
    write_dataset(
        data_root,
        "repoI",
        truth=[{"title": "T1", "severity": "high", "description": "d1", "file": "C.sol"}],
        scan=[
            {"Issue": "S1", "Severity": "High", "Description": "d1", "Contracts": ["C.sol"]},
            {"Issue": "Snote", "Severity": "Info", "Description": "n", "Contracts": ["C.sol"]},
        ],
    )
    fake = FakeLLMClient(responses=[make_finding(index=0, **EXACT), make_finding(index=0, **EXACT)])
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)

    evaluate.run_evaluation(
        repo_name="repoI",
        data_root=data_root,
        scan_source="auditagent",
        output_root=out_root,
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
    )

    result = json.loads((out_root / "repoI_results.json").read_text())
    assert sum(1 for r in result if r["is_match"]) == 1
    assert sum(1 for r in result if r["is_fp"]) == 0  # the Info finding was skipped


def test_run_evaluation_handles_no_result_from_judge(tmp_path: Path, monkeypatch):
    """When the judge returns nothing, the truth item is skipped (no crash); the
    unmatched scan finding still becomes a false positive."""
    data_root = tmp_path / "data"
    out_root = tmp_path / "bench"
    write_dataset(
        data_root,
        "repoN",
        truth=[{"title": "T1", "severity": "high", "description": "d1", "file": "C.sol"}],
        scan=[{"Issue": "S1", "Severity": "High", "Description": "d1", "Contracts": ["C.sol"]}],
    )
    fake = FakeLLMClient(responses=[])  # every call returns None
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)

    evaluate.run_evaluation(
        repo_name="repoN",
        data_root=data_root,
        scan_source="auditagent",
        output_root=out_root,
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
    )

    result = json.loads((out_root / "repoN_results.json").read_text())
    assert sum(1 for r in result if r["is_match"]) == 0  # NO RESULT -> no TP
    assert sum(1 for r in result if r["is_fp"]) == 1  # S1 unmatched -> FP


def test_run_evaluation_with_empty_truth(tmp_path: Path, monkeypatch):
    """No ground-truth findings: nothing matches, every non-QA scan finding is a FP."""
    data_root = tmp_path / "data"
    out_root = tmp_path / "bench"
    write_dataset(
        data_root,
        "repoE",
        truth=[],
        scan=[
            {"Issue": "S1", "Severity": "High", "Description": "d", "Contracts": ["C.sol"]},
            {"Issue": "S2", "Severity": "Info", "Description": "n", "Contracts": ["C.sol"]},
        ],
    )
    fake = FakeLLMClient(responses=[])  # judge is never consulted when truth is empty
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)

    evaluate.run_evaluation(
        repo_name="repoE",
        data_root=data_root,
        scan_source="auditagent",
        output_root=out_root,
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
    )

    result = json.loads((out_root / "repoE_results.json").read_text())
    assert fake.calls == 0  # no truth -> no LLM calls
    assert sum(1 for r in result if r["is_match"]) == 0
    assert sum(1 for r in result if r["is_fp"]) == 1  # S1 only; S2 (Info) skipped


def test_run_evaluation_with_empty_scan(tmp_path: Path, monkeypatch):
    """No scan findings: every truth finding is unmatched and there are no FPs."""
    data_root = tmp_path / "data"
    out_root = tmp_path / "bench"
    write_dataset(
        data_root,
        "repoS",
        truth=[{"title": "T1", "severity": "high", "description": "d", "file": "C.sol"}],
        scan=[],
    )
    fake = FakeLLMClient(responses=[])
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)

    evaluate.run_evaluation(
        repo_name="repoS",
        data_root=data_root,
        scan_source="auditagent",
        output_root=out_root,
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
    )

    result = json.loads((out_root / "repoS_results.json").read_text())
    assert result == []  # no matches, no partials, no FPs


def test_run_evaluation_one_to_one_mapping_prevents_double_count(tmp_path: Path, monkeypatch):
    """Two truth findings that both report scan index 0 must resolve to two DISTINCT
    scan findings, because a matched finding is popped from the pool (one-to-one)."""
    data_root = tmp_path / "data"
    out_root = tmp_path / "bench"
    write_dataset(
        data_root,
        "repoO",
        truth=[
            {"title": "T1", "severity": "high", "description": "d1", "file": "C.sol"},
            {"title": "T2", "severity": "high", "description": "d2", "file": "C.sol"},
        ],
        scan=[
            {"Issue": "S0", "Severity": "High", "Description": "d1", "Contracts": ["C.sol"]},
            {"Issue": "S1", "Severity": "High", "Description": "d2", "Contracts": ["C.sol"]},
        ],
    )
    # Both truths report a match at working index 0; after T1 pops scan[0], T2's
    # index 0 must map to the remaining finding (original index 1).
    script = [
        make_finding(index=0, **EXACT),
        make_finding(index=0, **EXACT),
        make_finding(index=0, **EXACT),
        make_finding(index=0, **EXACT),
    ]
    fake = FakeLLMClient(responses=script)
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)

    evaluate.run_evaluation(
        repo_name="repoO",
        data_root=data_root,
        scan_source="auditagent",
        output_root=out_root,
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
    )

    result = json.loads((out_root / "repoO_results.json").read_text())
    matched_indices = {r["index_of_finding_from_junior_auditor"] for r in result if r["is_match"]}
    assert sum(1 for r in result if r["is_match"]) == 2
    assert matched_indices == {0, 1}  # distinct scan findings, not index 0 twice
    assert sum(1 for r in result if r["is_fp"]) == 0  # both scan findings consumed
