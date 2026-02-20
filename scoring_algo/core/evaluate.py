from __future__ import annotations

import asyncio
from pathlib import Path

from rich import print
from rich.progress import BarColumn, Progress, TimeElapsedColumn, TimeRemainingColumn

from .batching import process_in_batches
from .storage import (
    get_evaluation_path,
    read_scan_results,
    read_truth_data,
    store_evaluation_result,
)
from .telemetry import observe
from .types import EvaluatedFinding, Finding, WorkingResult


@observe(name="[ScoringAlgo] Run scoring algo")
def run_evaluation(
    repo_name: str,
    data_root: Path,
    scan_source: str,
    output_root: Path,
    model: str,
    iterations: int,
    batch_size: int,
    debug_prompt: bool,
) -> None:
    truth = read_truth_data(repo_name, data_root)
    results = read_scan_results(repo_name, data_root, scan_source)

    print(f"[cyan]Loaded[/cyan] truth={len(truth)} findings; junior report={len(results)} findings")

    # working copy with original index mapping
    working_results: list[WorkingResult] = []
    for i, r in enumerate(results):
        working_results.append(
            WorkingResult(
                Issue=r.Issue,
                Category=r.Category,
                Description=r.Description,
                Contracts=r.Contracts,
                Severity=r.Severity,
                Index=i,
            )
        )

    evaluated: list[EvaluatedFinding] = []
    with Progress(
        "{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "|",
        TimeElapsedColumn(),
        "<",
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task(f"Evaluating {repo_name} ({len(truth)} issues)", total=len(truth))

        async def _process_all():
            out: list[tuple[int, int, Finding | None]] = []
            for idx, finding in enumerate(truth):
                content = await process_in_batches(
                    all_findings=working_results,
                    repo_name=repo_name,
                    truth_finding=finding,
                    model=model,
                    iterations=iterations,
                    batch_size=batch_size,
                    debug_prompt=debug_prompt,
                    output_root=output_root,
                )

                # Resolve working index → original scan index BEFORE any pop
                original_index = -1
                if content:
                    working_index = content.index_of_finding_from_junior_auditor
                    if 0 <= working_index < len(working_results):
                        original_index = working_results[working_index].Index

                    # Remove matched finding NOW to enforce one-to-one mapping
                    # for subsequent truth findings
                    if content.is_match and 0 <= working_index < len(working_results):
                        working_results.pop(working_index)

                out.append((idx, original_index, content))
                progress.update(task, advance=1)
            return out

        # Run the whole evaluation in one event loop to avoid loop churn
        results_async = asyncio.run(_process_all())
        for idx, original_index, content in results_async:
            if not content:
                continue

            # Enforce severity from truth (string form)
            truth_item = truth[idx]
            truth_severity = getattr(truth_item.Severity, "value", truth_item.Severity)
            if content.severity_from_truth != truth_severity:
                content.severity_from_truth = truth_severity

            evaluated.append(
                EvaluatedFinding(
                    is_match=content.is_match,
                    is_partial_match=content.is_partial_match,
                    is_fp=False,
                    explanation=content.explanation,
                    severity_from_junior_auditor=content.severity_from_junior_auditor,
                    severity_from_truth=content.severity_from_truth,
                    index_of_finding_from_junior_auditor=original_index,
                    finding_description_from_junior_auditor=(
                        results[original_index].Description
                        if 0 <= original_index < len(results)
                        else "NOT FOUND"
                    ),
                )
            )

    processed = post_process_partial_matches(evaluated)

    # add FPs: all remaining scan items not used by matches/partials
    skip_indices = set()
    for ef in processed:
        if ef.index_of_finding_from_junior_auditor >= 0:
            skip_indices.add(ef.index_of_finding_from_junior_auditor)

    for i, r in enumerate(results):
        if i in skip_indices:
            continue
        r_severity = getattr(r.Severity, "value", r.Severity)
        if r_severity in ("Info", "Best Practices"):
            continue
        processed.append(
            EvaluatedFinding(
                is_match=False,
                is_partial_match=False,
                is_fp=True,
                explanation="The source of truth report does not contain this issue.",
                severity_from_junior_auditor=r.Severity.value,
                severity_from_truth="N/A",
                index_of_finding_from_junior_auditor=i,
                finding_description_from_junior_auditor=r.Description,
            )
        )

    store_evaluation_result(processed, repo_name, output_root)
    out_path = get_evaluation_path(repo_name, output_root)
    print(f"[green]Saved results to[/green] {out_path}")


def post_process_partial_matches(results: list[EvaluatedFinding]) -> list[EvaluatedFinding]:
    true_indices = set()
    for f in results:
        if f.is_match and f.index_of_finding_from_junior_auditor >= 0:
            true_indices.add(f.index_of_finding_from_junior_auditor)

    partial_indices = set()
    processed: list[EvaluatedFinding] = []
    for f in results:
        idx = f.index_of_finding_from_junior_auditor
        if idx < 0 or f.is_match:
            processed.append(f)
            continue
        if f.is_partial_match:
            if idx in true_indices:
                f = EvaluatedFinding(
                    **{
                        **f.model_dump(),
                        "is_partial_match": False,
                        "explanation": f.explanation
                        + " (Already counted as TP elsewhere, so not counted as partial here.)",
                    }
                )
            elif idx in partial_indices:
                f = EvaluatedFinding(
                    **{
                        **f.model_dump(),
                        "is_partial_match": False,
                        "explanation": f.explanation
                        + " (Already counted as partial elsewhere, so not counted here.)",
                    }
                )
            else:
                partial_indices.add(idx)
        processed.append(f)
    return processed
