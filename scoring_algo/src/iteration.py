from __future__ import annotations

from typing import List

from .types import Finding


class MatchType:
    FALSE = 0
    PARTIAL = 1
    EXACT = 2


def pick_type(responses: List[Finding], match_type: int) -> Finding:
    if match_type == MatchType.FALSE:
        for r in responses:
            if not r.is_match and not r.is_partial_match:
                return r
    elif match_type == MatchType.PARTIAL:
        for r in responses:
            if r.is_partial_match:
                return r
    elif match_type == MatchType.EXACT:
        for r in responses:
            if r.is_match:
                return r
    return responses[0]


def get_best_response(responses: List[Finding], num_iterations: int) -> Finding:
    partial_matches = sum(1 for r in responses if r.is_partial_match)
    exact_matches = sum(1 for r in responses if r.is_match)
    false_matches = num_iterations - partial_matches - exact_matches

    if partial_matches == num_iterations:
        return responses[0]
    if exact_matches == num_iterations:
        return responses[0]
    if false_matches == num_iterations:
        return responses[0]

    if exact_matches == 2:
        return pick_type(responses, MatchType.EXACT)
    elif partial_matches == 2:
        return pick_type(responses, MatchType.PARTIAL)
    elif false_matches == 2:
        return pick_type(responses, MatchType.FALSE)

    if exact_matches == 1 and partial_matches == 1 and false_matches == 1:
        return pick_type(responses, MatchType.PARTIAL)

    return responses[0]
