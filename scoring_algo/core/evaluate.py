from __future__ import annotations

import asyncio
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .batching import process_in_batches
from .storage import (
    get_evaluation_path,
    read_scan_results,
    read_truth_data,
    store_evaluation_result,
)
from .telemetry import observe
from .types import EvaluatedFinding, WorkingResult

console = Console()


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

    console.print(f"[cyan]Loaded[/cyan] truth={len(truth)} findings; scan={len(results)} findings")

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

    total = len(truth)

    async def _process_all() -> list[EvaluatedFinding]:
        out: list[EvaluatedFinding] = []
        for idx, finding in enumerate(truth):
            status_msg = f"Evaluating finding {idx + 1}/{total}…"
            console.print(f"  [dim]{status_msg}[/dim]", end="\r")

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
                if content.is_match and 0 <= working_index < len(working_results):
                    working_results.pop(working_index)

            # Print result line (overwrites the status message)
            truth_title = _truncate(finding.Issue, 60)
            prefix = f"  [dim][{idx + 1}/{total}][/dim] {truth_title}"
            if not content:
                console.print(f"{prefix} → [yellow]NO RESULT[/yellow]")
                continue

            # Enforce severity from truth
            truth_severity = str(getattr(finding.Severity, "value", finding.Severity))
            if content.severity_from_truth != truth_severity:
                content.severity_from_truth = truth_severity

            if content.is_match:
                tag = "[bold green]TP[/bold green]"
            elif content.is_partial_match:
                tag = "[bold yellow]PARTIAL[/bold yellow]"
            else:
                tag = "[bold red]FN[/bold red]"
            matched_info = ""
            if (content.is_match or content.is_partial_match) and 0 <= original_index < len(
                results
            ):
                matched_info = f" [dim]↔ scan #{original_index + 1}[/dim]"
            console.print(f"{prefix} → {tag}{matched_info}")

            out.append(
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
        return out

    evaluated = asyncio.run(_process_all())

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

    # Log false positives
    fp_count = sum(1 for ef in processed if ef.is_fp)
    if fp_count:
        console.print(f"\n  [red]False positives ({fp_count}):[/red]")
        for ef in processed:
            if ef.is_fp:
                idx = ef.index_of_finding_from_junior_auditor
                desc = _truncate(ef.finding_description_from_junior_auditor, 70)
                sev = ef.severity_from_junior_auditor
                console.print(f"    scan #{idx + 1} [{sev}] {desc}")

    # Summary table
    tp = sum(1 for ef in processed if ef.is_match)
    partial = sum(1 for ef in processed if ef.is_partial_match)
    fn = len(truth) - tp - partial
    console.print()
    table = Table(title=f"Results — {repo_name}", show_lines=False, pad_edge=False)
    table.add_column("Metric", style="bold")
    table.add_column("Count", justify="right")
    table.add_row("Truth findings", str(len(truth)))
    table.add_row("Scan findings", str(len(results)))
    table.add_row("[green]True Positives (TP)[/green]", f"[green]{tp}[/green]")
    table.add_row("[yellow]Partial matches[/yellow]", f"[yellow]{partial}[/yellow]")
    table.add_row("[red]False Negatives (FN)[/red]", f"[red]{fn}[/red]")
    table.add_row("[red]False Positives (FP)[/red]", f"[red]{fp_count}[/red]")
    console.print(table)

    store_evaluation_result(processed, repo_name, output_root)
    out_path = get_evaluation_path(repo_name, output_root)
    console.print(f"\n[green]Saved results to[/green] {out_path}")


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


def _truncate(text: str, max_len: int) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"
