"""Tests for batching: batch construction, agreement, index offsets, and the
async early-exit generation loop (iteration 3 runs only on disagreement)."""

from __future__ import annotations

import pytest

from scoring_algo.core import batching
from scoring_algo.core.batching import _agree, _apply_index_offset, build_batches
from tests._helpers import FakeLLMClient, make_finding, make_working_result

EXACT = {"is_match": True, "is_partial_match": False}
PARTIAL = {"is_match": False, "is_partial_match": True}
FALSE = {"is_match": False, "is_partial_match": False}


def test_build_batches():
    assert build_batches([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert build_batches([], 3) == []
    assert build_batches([1, 2], 10) == [[1, 2]]


def test_agree():
    assert _agree(make_finding(**EXACT), make_finding(**EXACT)) is True
    assert _agree(make_finding(**PARTIAL), make_finding(**PARTIAL)) is True
    assert _agree(make_finding(**FALSE), make_finding(**FALSE)) is True
    assert _agree(make_finding(**EXACT), make_finding(**PARTIAL)) is False
    assert _agree(make_finding(**EXACT), make_finding(**FALSE)) is False
    assert _agree(make_finding(**PARTIAL), make_finding(**FALSE)) is False


def test_apply_index_offset():
    f = make_finding(index=-1)
    _apply_index_offset(f, batch_number=2, batch_size=10)
    assert f.index_of_finding_from_junior_auditor == -1  # sentinel unchanged

    g = make_finding(index=3)
    _apply_index_offset(g, batch_number=2, batch_size=10)
    assert g.index_of_finding_from_junior_auditor == 23


@pytest.mark.parametrize(
    ("iterations", "responses", "expected_calls", "expected_len"),
    [
        (1, [make_finding(**EXACT)], 1, 1),
        (2, [make_finding(**EXACT), make_finding(**EXACT)], 2, 2),
        # 3 iterations, first two agree -> early exit, no third call
        (3, [make_finding(**EXACT), make_finding(**EXACT)], 2, 2),
        # 3 iterations, first two disagree -> third call happens
        (3, [make_finding(**EXACT), make_finding(**PARTIAL), make_finding(**FALSE)], 3, 3),
    ],
)
async def test_generate_responses_early_exit(iterations, responses, expected_calls, expected_len):
    client = FakeLLMClient(responses=responses)
    out = await batching._generate_responses_for_prompt(client, "prompt", iterations)
    assert client.calls == expected_calls
    assert len(out) == expected_len


async def test_process_in_batches_returns_first_exact_match(monkeypatch):
    fake = FakeLLMClient(responses=[make_finding(index=0, **EXACT)] * 3)
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)
    result = await batching.process_in_batches(
        all_findings=[make_working_result(0), make_working_result(1)],
        repo_name="r",
        truth_finding=make_working_result(0),
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
        output_root=None,
    )
    assert result is not None
    assert result.is_match is True


async def test_process_in_batches_returns_none_when_no_findings(monkeypatch):
    fake = FakeLLMClient(responses=[])  # always returns None
    monkeypatch.setattr(batching, "LLMClient", lambda _model: fake)
    result = await batching.process_in_batches(
        all_findings=[make_working_result(0)],
        repo_name="r",
        truth_finding=make_working_result(0),
        model="o4-mini",
        iterations=3,
        batch_size=10,
        debug_prompt=False,
        output_root=None,
    )
    assert result is None
