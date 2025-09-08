from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Optional

from .iteration import get_best_response
from .llm import LLMClient
from .prompt import CALCULATE_PROMPT
from .storage import store_debug_prompt
from .types import Finding, Vulnerability, WorkingResult


def build_batches(findings: List[WorkingResult], batch_size: int) -> List[List[WorkingResult]]:
    return [findings[i : i + batch_size] for i in range(0, len(findings), batch_size)]  # noqa: E203


async def process_in_batches_async(
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

        # run first two iterations concurrently, then conditionally run a third
        async def _run_two() -> List[Finding]:
            r1, r2 = await asyncio.gather(
                client.generate_async(prompt), client.generate_async(prompt)
            )
            out: List[Finding] = []
            if r1:
                out.append(r1)
            if r2:
                out.append(r2)
            return out

        def _agree(a: Finding, b: Finding) -> bool:
            if a.is_match and b.is_match:
                return True
            if a.is_partial_match and b.is_partial_match:
                return True
            if (
                not a.is_match
                and not a.is_partial_match
                and not b.is_match
                and not b.is_partial_match
            ):
                return True
            return False

        responses: List[Finding] = []
        if iterations <= 1:
            r = await client.generate_async(prompt)
            if r:
                responses.append(r)
        elif iterations == 2:
            responses = await _run_two()
        else:
            # iterations >= 3
            first_two = await _run_two()
            responses.extend(first_two)
            need_third = True
            if len(first_two) == 2 and _agree(first_two[0], first_two[1]):
                need_third = False
            if need_third:
                r3 = await client.generate_async(prompt)
                if r3:
                    responses.append(r3)
        if not responses:
            continue

        content = get_best_response(responses, len(responses))

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
    # Backward-compatible sync wrapper; prefer reusing a single Runner in callers
    return asyncio.run(
        process_in_batches_async(
            all_findings=all_findings,
            repo_name=repo_name,
            truth_finding=truth_finding,
            model=model,
            iterations=iterations,
            batch_size=batch_size,
            debug_prompt=debug_prompt,
            output_root=output_root,
        )
    )
