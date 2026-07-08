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
- Evaluates per-batch with the same prompt, running 3 iterations per batch (hardcoded in `settings.py`)
- Post-processes partial matches and appends false positives
- Writes results to `<output_root>/<repo>_results.json` (configured in `settings.py`)

### Prerequisites

- Python 3.12+ recommended
- API keys as environment variables:
  - `OPENAI_API_KEY`
  - Optional (third-party APIs): `OPENAI_BASE_URL`
  - Optional (telemetry): `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_USER_ID`

### Install

```bash
uv sync  # install runtime + dev dependencies
```

### Tests

```bash
uv run pytest        # run the test suite
```

The suite mocks the LLM judge, so it runs fully offline and needs no `OPENAI_API_KEY`.

### Configuration

All runtime options are set in `scoring_algo/settings.py` (env prefix `SCORING_`):

- `REPOS_TO_RUN`: list of repo names (without `.json`) to evaluate
- `MODEL`: OpenAI model name (must be in `SUPPORTED_MODELS`)
- `BATCH_SIZE`: number of scan findings per batch (default: 10)
- `SCAN_SOURCE`: which folder under data-root to read scan results from (`auditagent` or `baseline`)
- `DATA_ROOT`: base directory containing `auditagent/`, `baseline/`, `repos/`, `source_of_truth/`
- `OUTPUT_ROOT`: directory where `<repo>_results.json` will be written
- `DEBUG_PROMPT`: whether to write the rendered prompt beside results

Notes on paths:
- If `DATA_ROOT` or `OUTPUT_ROOT` are relative, they resolve relative to the `scoring_algo/` package directory.

### Run

Subcommands are available via the Typer CLI:

```bash
# Run the evaluation pipeline
scoring-algo evaluate [--no-telemetry] [--log-level INFO]

# Generate a Markdown report from existing benchmark results
scoring-algo report --benchmarks ./benchmarks --scan-root ./data/baseline --out REPORT.md
```

The `evaluate` command validates the presence of `<DATA_ROOT>/<SCAN_SOURCE>/<repo>_results.json` and `<DATA_ROOT>/source_of_truth/<repo>.json`. Results are written to `<OUTPUT_ROOT>/<repo>_results.json`.

The `report` command generates a Markdown report from existing results without re-running evaluation. When `--out` is relative, it is written inside `--benchmarks`.

### Quickstart

```bash
uv sync
cp .env.example .env  # then fill in your OPENAI_API_KEY
scoring-algo evaluate --no-telemetry --log-level INFO
scoring-algo report --benchmarks ./benchmarks --scan-root ./data/baseline --out REPORT.md
```

### Scoring behavior

For each truth finding (`source_of_truth/<repo>.json`):

1) The junior report is split into batches of `BATCH_SIZE` in original order.
2) For each batch:
   - The prompt includes the single truth finding and the current batch of junior findings.
   - The LLM is called 3 times and responses are aggregated by majority:
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


