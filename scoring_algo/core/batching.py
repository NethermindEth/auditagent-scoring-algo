from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from .iteration import get_best_response
from .llm import LLMClient
from .prompt import CALCULATE_PROMPT
from .storage import store_debug_prompt
from .types import Finding, Vulnerability, WorkingResult


def build_batches(findings: List[WorkingResult], batch_size: int) -> List[List[WorkingResult]]:
    return [findings[i : i + batch_size] for i in range(0, len(findings), batch_size)]


def process_in_batches(
    all_findings: List[WorkingResult],
    repo_name: str,
    truth_finding: Vulnerability,
    model: str,
    iterations: int,
    batch_size: int,
    debug_prompt: bool,
    output_root: Path,
) -> Optional[Finding]:
    batches = build_batches(all_findings, batch_size)
    client = LLMClient(model)

    current_best: Optional[Finding] = None

    for batch_number, batch in enumerate(batches):
        working_results = [
            {
                "Issue": b.Issue,
                "Category": b.Category.value if hasattr(b.Category, "value") else b.Category,
                "Description": b.Description,
                "Contracts": b.Contracts,
                "Severity": b.Severity.value if hasattr(b.Severity, "value") else b.Severity,
                "Index": i,
            }
            for i, b in enumerate(batch)
        ]

        stringified_truth = truth_finding.model_dump_json(indent=2)
        stringified_results = json.dumps(working_results, indent=2)

        prompt = (
            CALCULATE_PROMPT.replace("{truth_finding}", stringified_truth)
            .replace("{junior_findings}", stringified_results)
            .strip()
        )
        if debug_prompt:
            store_debug_prompt(prompt, repo_name, output_root)

        # run N iterations and pick best response
        responses: List[Finding] = []
        for _ in range(iterations):
            resp = client.generate(prompt)
            if resp:
                responses.append(resp)
        if not responses:
            continue

        content = get_best_response(responses, iterations)

        if content.index_of_finding_from_junior_auditor != -1:
            index_wrt_working = (
                content.index_of_finding_from_junior_auditor + batch_number * batch_size
            )
            content.index_of_finding_from_junior_auditor = int(index_wrt_working)

        if current_best is None:
            current_best = content

        if content.is_match:
            return content
        elif content.is_partial_match and not (current_best and current_best.is_partial_match):
            current_best = content

    return current_best
