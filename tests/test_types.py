"""Tests for the pydantic models: enum coercion and default values."""

from __future__ import annotations

from scoring_algo.core.types import CategoryEnum, Finding, Severity, Vulnerability


def test_vulnerability_defaults_to_other_category():
    v = Vulnerability(Issue="i", Severity="High", Contracts=["C"], Description="d")
    assert v.Category is CategoryEnum.OTHER
    assert v.Severity is Severity.HIGH


def test_vulnerability_coerces_category_by_value():
    v = Vulnerability(
        Issue="i", Severity="Medium", Contracts=["C"], Description="d", Category="Reentrancy"
    )
    assert v.Category is CategoryEnum.REENTRANCY
    assert v.Severity is Severity.MEDIUM


def test_finding_roundtrip():
    f = Finding(
        is_match=True,
        is_partial_match=False,
        explanation="e",
        severity_from_junior_auditor="High",
        severity_from_truth="Medium",
        index_of_finding_from_junior_auditor=3,
    )
    dumped = f.model_dump()
    assert dumped["is_match"] is True
    assert dumped["index_of_finding_from_junior_auditor"] == 3
