from pathlib import Path

import typer
from dotenv import load_dotenv
from rich import print

from .core.evaluate import run_evaluation
from .core.logging_config import configure_logging
from .core.storage import get_scan_path, get_truth_path
from .core.telemetry import set_telemetry
from .generate_report import generate_markdown_report
from .settings import Settings

app = typer.Typer(help="Scoring Algo CLI")


@app.command("evaluate")
def evaluate(
    no_telemetry: bool = typer.Option(False, "--no-telemetry", help="Disable telemetry"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
):
    load_dotenv()
    if no_telemetry:
        set_telemetry(False)
    configure_logging(log_level)

    cfg = Settings()
    base_dir = Path(__file__).resolve().parent

    data_root = Path(cfg.DATA_ROOT)
    if not data_root.is_absolute():
        data_root = base_dir / data_root

    output_root = Path(cfg.OUTPUT_ROOT)
    if not output_root.is_absolute():
        output_root = base_dir / output_root

    def run_one(name: str):
        name = name.replace(".json", "")
        print(
            f"[bold green]Running evaluation[/bold green] repo={name} model={cfg.MODEL} iter={cfg.ITERATIONS} batch={cfg.BATCH_SIZE}"  # noqa E501
        )
        scan_path = get_scan_path(name, data_root, cfg.SCAN_SOURCE)
        truth_path = get_truth_path(name, data_root)
        if not scan_path.exists():
            raise typer.BadParameter(f"Scan results not found: {scan_path}")
        if not truth_path.exists():
            raise typer.BadParameter(f"Truth file not found: {truth_path}")

        run_evaluation(
            repo_name=name,
            data_root=data_root,
            scan_source=cfg.SCAN_SOURCE,
            output_root=output_root,
            model=cfg.MODEL,
            iterations=cfg.ITERATIONS,
            batch_size=cfg.BATCH_SIZE,
            debug_prompt=cfg.DEBUG_PROMPT,
        )

    for r in cfg.REPOS_TO_RUN:
        run_one(r)


@app.command("report")
def report(
    out: Path = typer.Option(Path("REPORT.md"), "--out", help="Report filename"),
    benchmarks: Path = typer.Option(
        Path("../benchmarks"), "--benchmarks", help="Benchmarks folder"
    ),
    scan_root: Path = typer.Option(
        Path("../data/baseline"), "--scan-root", help="Path to scan results root"
    ),
):
    load_dotenv()
    configure_logging("INFO")
    generate_markdown_report(benchmarks=benchmarks, out=out, scan_root=scan_root)


if __name__ == "__main__":
    app()
