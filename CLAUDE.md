# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python CLI tool that evaluates AI-generated smart contract security audit findings against ground truth data using LLM-based comparison. It compares "junior auditor" (AI scan) results against verified vulnerability reports and produces precision/recall/F1 metrics.

## Commands

### Setup
```bash
uv sync                   # install runtime + dev dependencies
```

### Run evaluation
```bash
scoring-algo evaluate [--no-telemetry] [--log-level INFO]
```

### Generate report (from existing benchmark results)
```bash
scoring-algo report --benchmarks ./benchmarks --scan-root ./data/baseline --out REPORT.md
```

### Linting & formatting
```bash
uv run ruff check scoring_algo/      # lint
uv run ruff check --fix scoring_algo/ # lint + autofix
uv run ruff format scoring_algo/     # format (black-compatible)
uv run mypy scoring_algo/            # type check
```

Pre-commit hooks run ruff (lint + format) and mypy automatically on commit.

## Code Style

- Line length: 100 (ruff lint + format aligned)
- Ruff handles linting (replaces flake8), import sorting (replaces isort), and formatting (replaces black)
- Type hints throughout; `from __future__ import annotations` in all modules
- Pydantic models for data validation and settings

## Architecture

### Entry Points
- `scoring_algo/cli.py` — Typer CLI with `evaluate` and `report` subcommands
- `scoring_algo/generate_report.py` — Standalone report generator (also registered as `scoring-algo-report`)

### Core Pipeline (`scoring_algo/core/`)

**Evaluation flow** (`evaluate.py`):
1. **Load data** (`storage.py`) — reads ground truth from `data/source_of_truth/<repo>.json` and scan results from `data/<scan_source>/<repo>_results.json`; normalizes diverse JSON formats into `Vulnerability` Pydantic models
2. **Batch** (`batching.py`) — splits scan findings into batches of `BATCH_SIZE` (default 10)
3. **LLM compare** (`llm.py`) — for each truth finding × batch, sends prompt to OpenAI API via `AsyncOpenAI` with structured output parsing; returns `Finding` objects
4. **Consensus** (`iteration.py`) — runs `ITERATIONS` (default 3) LLM calls per comparison; majority vote determines result (2-of-3 wins; 1-1-1 tie → partial match)
5. **Match resolution** (`evaluate.py`) — iterates batches until exact match found; removes matched findings from pool (one-to-one mapping); falls back to best partial
6. **Post-process** — suppresses duplicate partials, removes partials conflicting with exact matches, marks unmatched non-QA findings as false positives

**Key modules:**
- `types.py` — Pydantic models (`Vulnerability`, `Finding`, `EvaluatedFinding`) and enums (`Severity`, `Category`)
- `prompt.py` — LLM prompt template (role: security expert, structured JSON output)
- `telemetry.py` — Optional Langfuse integration (disable with `--no-telemetry`)
- `settings.py` — Pydantic `BaseSettings` with `SCORING_` env prefix; loads from `.env`

### Data Layout
```
data/
├── auditagent/          # AI-generated audit results
├── baseline/            # Baseline scan results
├── repos/               # Repository metadata
└── source_of_truth/     # Verified ground truth findings
```

Results are written to `benchmarks/<repo>_results.json`.

## Configuration

All runtime settings are in `scoring_algo/settings.py` via env vars (prefix `SCORING_`):
- `REPOS_TO_RUN` — repos to evaluate (edit defaults in `settings.py`)
- `MODEL` — OpenAI model (must be in `SUPPORTED_MODELS`)
- `ITERATIONS`, `BATCH_SIZE` — consensus and batching parameters
- `SCAN_SOURCE` — folder under data root (`auditagent` or `baseline`)
- `DATA_ROOT`, `OUTPUT_ROOT` — paths (relative paths resolve from `scoring_algo/` package dir)

Required env var: `OPENAI_API_KEY`. Optional: `OPENAI_BASE_URL` for third-party APIs.

## Key Design Decisions

- **Consensus via majority voting**: 3 LLM iterations per comparison with early exit when first 2 agree
- **Conservative tie-breaking**: a 1-exact + 1-partial + 1-false tie resolves to partial (not false)
- **One-to-one mapping**: matched scan findings are removed from the pool to prevent double-counting
- **QA exclusion**: Info and Best Practices severity findings are excluded from false positive counts
- **Async parallelism**: LLM calls run 2 in parallel with a conditional 3rd via `asyncio`
