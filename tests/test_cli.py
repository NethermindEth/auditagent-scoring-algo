"""Tests for the Typer CLI (the pure ``report`` command) and logging setup."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from scoring_algo.cli import app
from scoring_algo.core.logging_config import configure_logging


def test_configure_logging_accepts_levels_and_none():
    configure_logging("INFO")
    configure_logging("debug")  # case-insensitive
    configure_logging(None)  # falls back to INFO without raising


def test_cli_report_command_writes_markdown(tmp_path: Path):
    bench = tmp_path / "benchmarks"
    bench.mkdir()
    (bench / "repoA_results.json").write_text(
        json.dumps(
            [
                {
                    "is_match": True,
                    "is_partial_match": False,
                    "is_fp": False,
                    "severity_from_truth": "High",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(app, ["report", "--benchmarks", str(bench), "--out", "REPORT.md"])
    assert result.exit_code == 0, result.output
    assert (bench / "REPORT.md").exists()
