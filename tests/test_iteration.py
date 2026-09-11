"""Tests for the 2-of-3 majority-vote logic: get_best_response and pick_type."""

from __future__ import annotations

import pytest

from scoring_algo.core.iteration import MatchType, get_best_response, pick_type
from tests._helpers import make_finding

EXACT = {"is_match": True, "is_partial_match": False}
PARTIAL = {"is_match": False, "is_partial_match": True}
FALSE = {"is_match": False, "is_partial_match": False}


def _f(kind: dict, index: int):
    return make_finding(index=index, **kind)


@pytest.mark.parametrize(
    ("kinds", "expect_match", "expect_partial"),
    [
        ([EXACT, EXACT, EXACT], True, False),
        ([PARTIAL, PARTIAL, PARTIAL], False, True),
        ([FALSE, FALSE, FALSE], False, False),
        ([EXACT, EXACT, FALSE], True, False),
        ([EXACT, EXACT, PARTIAL], True, False),
        ([PARTIAL, PARTIAL, FALSE], False, True),
        ([FALSE, FALSE, EXACT], False, False),
        ([EXACT, PARTIAL, FALSE], False, True),  # 1-1-1 tie -> partial match
    ],
)
def test_get_best_response_majority(kinds, expect_match, expect_partial):
    responses = [_f(k, i) for i, k in enumerate(kinds)]
    best = get_best_response(responses, len(responses))
    assert best.is_match is expect_match
    assert best.is_partial_match is expect_partial


def test_get_best_response_selects_the_winning_member_not_just_index_zero():
    # index 0 is FALSE, but two EXACT votes win: the returned finding must be exact.
    responses = [_f(FALSE, 0), _f(EXACT, 1), _f(EXACT, 2)]
    best = get_best_response(responses, 3)
    assert best.is_match is True
    assert best.index_of_finding_from_junior_auditor in (1, 2)


def test_pick_type_returns_first_of_kind():
    responses = [_f(FALSE, 0), _f(PARTIAL, 1), _f(EXACT, 2)]
    assert pick_type(responses, MatchType.EXACT).index_of_finding_from_junior_auditor == 2
    assert pick_type(responses, MatchType.PARTIAL).index_of_finding_from_junior_auditor == 1
    assert pick_type(responses, MatchType.FALSE).index_of_finding_from_junior_auditor == 0


def test_pick_type_falls_back_to_first_when_kind_absent():
    responses = [_f(FALSE, 7)]
    assert pick_type(responses, MatchType.EXACT).index_of_finding_from_junior_auditor == 7
