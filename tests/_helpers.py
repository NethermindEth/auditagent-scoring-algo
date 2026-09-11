"""Test helpers: small factory functions and a deterministic fake LLM client."""

from __future__ import annotations

import json
from pathlib import Path

from scoring_algo.core.types import EvaluatedFinding, Finding, WorkingResult


def make_finding(
    *,
    is_match: bool = False,
    is_partial_match: bool = False,
    index: int = -1,
    explanation: str = "expl",
    sev_junior: str = "High",
    sev_truth: str = "High",
) -> Finding:
    return Finding(
        is_match=is_match,
        is_partial_match=is_partial_match,
        explanation=explanation,
        severity_from_junior_auditor=sev_junior,
        severity_from_truth=sev_truth,
        index_of_finding_from_junior_auditor=index,
    )


def make_evaluated(
    *,
    is_match: bool = False,
    is_partial_match: bool = False,
    is_fp: bool = False,
    index: int = -1,
    description: str = "desc",
    explanation: str = "expl",
) -> EvaluatedFinding:
    return EvaluatedFinding(
        is_match=is_match,
        is_partial_match=is_partial_match,
        is_fp=is_fp,
        explanation=explanation,
        severity_from_junior_auditor="High",
        severity_from_truth="High",
        index_of_finding_from_junior_auditor=index,
        finding_description_from_junior_auditor=description,
    )


def make_working_result(
    index: int,
    issue: str = "Issue",
    severity: str = "High",
    description: str = "desc",
    contracts: list[str] | None = None,
) -> WorkingResult:
    return WorkingResult(
        Issue=issue,
        Severity=severity,
        Description=description,
        Contracts=contracts or ["C.sol"],
        Index=index,
    )


class FakeLLMClient:
    """Deterministic stand-in for ``LLMClient``.

    Returns scripted ``Finding`` objects in call order (clamped to the last one)
    and records how many times it was called, so the otherwise-stochastic
    3-iteration majority-vote pipeline can be tested reproducibly.
    """

    def __init__(self, model: str = "o4-mini", responses: list[Finding] | None = None) -> None:
        self.model = model
        self._responses = list(responses or [])
        self.calls = 0
        self.prompts: list[str] = []

    async def generate_async(self, prompt: str) -> Finding | None:
        self.calls += 1
        self.prompts.append(prompt)
        if not self._responses:
            return None
        idx = min(self.calls - 1, len(self._responses) - 1)
        return self._responses[idx]


def write_dataset(
    data_root: Path,
    repo: str,
    truth: list[dict],
    scan: list[dict],
    scan_source: str = "auditagent",
) -> None:
    (data_root / "source_of_truth").mkdir(parents=True, exist_ok=True)
    (data_root / scan_source).mkdir(parents=True, exist_ok=True)
    (data_root / "source_of_truth" / f"{repo}.json").write_text(
        json.dumps({"project_id": repo, "vulnerabilities": truth}), encoding="utf-8"
    )
    (data_root / scan_source / f"{repo}_results.json").write_text(
        json.dumps(scan), encoding="utf-8"
    )
