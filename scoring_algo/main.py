from pathlib import Path

import typer
from rich import print
from rich.console import Console
from dotenv import load_dotenv

from src.evaluate import run_evaluation
from src.storage import get_scan_path, get_truth_path


from config import (
    REPOS_TO_RUN,
    MODEL,
    ITERATIONS,
    BATCH_SIZE,
    SCAN_SOURCE,
    DATA_ROOT,
    OUTPUT_ROOT,
    DEBUG_PROMPT,
)


app = typer.Typer(help="Standalone benchmark evaluator")
console = Console()


@app.command()
def main():
    load_dotenv()

    base_dir = Path(__file__).resolve().parent

    # Resolve configuration paths and values from config.py
    data_root = Path(DATA_ROOT)
    if not data_root.is_absolute():
        data_root = base_dir / data_root

    output_root = Path(OUTPUT_ROOT)
    if not output_root.is_absolute():
        output_root = base_dir / output_root

    model = MODEL
    iterations = ITERATIONS
    batch_size = BATCH_SIZE
    scan_source = SCAN_SOURCE
    debug_prompt = DEBUG_PROMPT

    def run_one(name: str):
        name = name.replace(".json", "")
        print(
            f"[bold green]Running evaluation[/bold green] repo={name} model={model} iter={iterations} batch={batch_size}"
        )
        output_dir = output_root

        # Strict existence checks; raise errors instead of skipping
        scan_path = get_scan_path(name, data_root, scan_source)
        if not scan_path.exists():
            raise FileNotFoundError(f"Scan results not found: {scan_path}")

        truth_path = get_truth_path(name, data_root)
        if not truth_path.exists():
            raise FileNotFoundError(f"Truth file not found: {truth_path}")

        run_evaluation(
            repo_name=name,
            data_root=data_root,
            scan_source=scan_source,
            output_root=output_dir,
            model=model,
            iterations=iterations,
            batch_size=batch_size,
            debug_prompt=debug_prompt,
        )

    # Only repos from config are used
    for r in REPOS_TO_RUN:
        run_one(r)


if __name__ == "__main__":
    app()
