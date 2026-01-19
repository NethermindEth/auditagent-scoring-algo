<div align="center">

<img src="./auditagent_logo.svg" width="200" alt="Scoring Algorithm | Python version" />
<br><br>

<h1><strong>Scoring Algorithm | Python version</strong></h1>

<br>
</div>


Minimal standalone Python CLI to run the same evaluation pipeline as the AuditAgent benchmark, but able to work against an external data repo as well. It:

- Targets an external data root with folders like: `auditagent/`, `baseline/`, `repos/`, `source_of_truth/`
- Reads scan results from `<data_root>/<scan_source>/<repo>_results.json` (e.g., `auditagent/` or `baseline/`)
- Reads source-of-truth findings from `<data_root>/source_of_truth/<repo>.json`
- Evaluates per-batch with the same prompt, running `ITERATIONS` per batch (default: 3 via `config.py`)
- Post-processes partial matches and appends false positives
- Writes results to `<output_root>/<repo>_results.json` (configured in `config.py`)

### Prerequisites

- Python 3.12+ recommended
- API keys as environment variables:
  - `OPENAI_API_KEY`
  - Optional (third-party APIs): `OPENAI_BASE_URL`
  - Optional (telemetry): `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_USER_ID`

### Install

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows Git Bash / PowerShell equivalent
pip install -e .  # or: pip install -e .[dev]
```

### Configuration

All runtime options are set in `scoring_algo/settings.py` (env prefix `SCORING_`):

- `REPOS_TO_RUN`: list of repo names (without `.json`) to evaluate
- `MODEL`: OpenAI model name (must be in `SUPPORTED_MODELS`)
- `ITERATIONS`: number of LLM runs per batch prompt (default: 3)
- `BATCH_SIZE`: number of scan findings per batch (default: 10)
- `SCAN_SOURCE`: which folder under data-root to read scan results from (`auditagent` or `baseline`)
- `DATA_ROOT`: base directory containing `auditagent/`, `baseline/`, `repos/`, `source_of_truth/`
- `OUTPUT_ROOT`: directory where `<repo>_results.json` will be written
- `DEBUG_PROMPT`: whether to write the rendered prompt beside results

Notes on paths:
- If `DATA_ROOT` or `OUTPUT_ROOT` are relative, they resolve relative to the `scoring_algo/` package directory.

### Run (pipeline)

Subcommands are available via Typer CLI:

```bash
scoring-algo evaluate [--no-telemetry] [--log-level INFO]
```

The runner validates the presence of: `<DATA_ROOT>/<SCAN_SOURCE>/<repo>_results.json` and `<DATA_ROOT>/source_of_truth/<repo>.json`. Results are written to `<OUTPUT_ROOT>/<repo>_results.json`.

### Run (report only)

Generate a Markdown report from existing results in `OUTPUT_ROOT` (or any benchmarks folder) without re-running evaluation. When `--out` is relative, it is written inside `--benchmarks`:

```bash
scoring-algo-report --benchmarks ./benchmarks --scan-root ./data/baseline --out REPORT.md
```

Module alternative:

```bash
python -m scoring_algo.generate_report --benchmarks ./benchmarks --scan-root ./data/baseline --out REPORT.md
```

### Quickstart

```bash
python -m venv .venv
. .venv/Scripts/activate
pip install -e .
setx OPENAI_API_KEY YOUR_KEY_HERE  # Windows permanent env; or set in .env
scoring-algo evaluate --no-telemetry --log-level INFO
scoring-algo report --benchmarks ./benchmarks --scan-root ./data/baseline --out REPORT.md
```

### Scoring behavior

For each truth finding (`source_of_truth/<repo>.json`):

1) The junior report is split into batches of `BATCH_SIZE` in original order.
2) For each batch:
   - The prompt includes the single truth finding and the current batch of junior findings.
   - The LLM is called `ITERATIONS` times and responses are aggregated by majority:
     - 2-of-3 exact matches → select a matching response
     - 2-of-3 partial matches → select a partial response
     - 2-of-3 false (neither match nor partial) → select a false response
     - With 3 iterations, a 1 exact + 1 partial + 1 false tie resolves to partial
     - Otherwise the first response is used as fallback
   - If the consensus is a true match, it is returned immediately for this truth. The matched junior finding is removed from future comparisons (one-to-one mapping).
   - Otherwise, the algorithm keeps the first partial found (if any) as the current best for this truth.
3) After all batches, if no exact match was found, the best partial (if any) is used; otherwise, a representative non-match is recorded.

Post-processing and false positives:

- Partials reusing a junior index already used by a true match are suppressed. Multiple partials pointing to the same junior index are de-duplicated (only the first remains).
- All remaining junior findings not used by matches/partials are appended as false positives, except severities `Info` and `Best Practices`.

Output format:

- Results are an array of `EvaluatedFinding` with fields: `is_match`, `is_partial_match`, `is_fp`, `explanation`, `severity_from_junior_auditor`, `severity_from_truth`, `index_of_finding_from_junior_auditor`, and `finding_description_from_junior_auditor`.


