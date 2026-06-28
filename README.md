# LLM PR Security Classifier

A pipeline that classifies GitHub Pull Request discussions into [OWASP Top 10 (2025)](https://owasp.org/Top10/2025/) categories using Large Language Models (Gemini), and synthesizes the results into project-specific security guidelines.

This repository contains the code and artifacts behind the study *"Automatically Generating Security Guidelines from Pull Request Discussions: The Case of Django Framework"*.

## How it works

The pipeline is organized as a multi-stage flow, adapted from the [PRIMES](https://arxiv.org/abs/2411.09974) methodology:

1. **Format** — raw PR dumps from the GitHub API are converted into a compact, unified JSON schema (`PRFormatter`).
2. **Classify** — batches of formatted PRs are sent to the LLM with a security-focused system prompt; each PR is mapped to an OWASP category and a "nature" (`FIX/PREVENTION` or `VULNERABILITY_INTRODUCTION`) (`LLMRunner` + `GeminiHandler`).
3. **Validate** — a controlled pilot dataset is used to measure classification quality (accuracy, macro precision/recall/F1, Cohen's kappa, confusion matrix) and to refine the prompt (`PilotStatistics`).
4. **Aggregate** — multiple runs are combined via majority voting for self-consistency (`notebooks/majority_voting.ipynb`).
5. **Export / analyze** — results are exported to spreadsheets for manual evaluation (`exporter.py`) and analyzed in notebooks.

## Project structure

```
.
├── src/
│   ├── main.py                     # Entry point: runs the batch classifier
│   ├── runner.py                   # LLMRunner: batch orchestration, retries, timeouts, incremental save, reprocess
│   ├── pr_formatter.py             # PRFormatter: GitHub PR dump -> unified JSON schema
│   ├── exporter.py                 # Exports classification results to an evaluation .xlsx
│   ├── utils.py                    # Robust JSON extraction from (messy) LLM responses
│   ├── llm/
│   │   ├── prompt.py               # PromptRepository: system/user prompts + OWASP constraints
│   │   ├── llm_factory.py          # LLMFactory: picks Gemini or Ollama handler by model name
│   │   ├── rich_api_log.py         # Console logging/spinners for API calls
│   │   └── handler/
│   │       ├── base_handler.py     # LLMHandler abstract interface (generate)
│   │       ├── gemini_handler.py   # Gemini implementation (google-genai)
│   │       └── ollama_handler.py   # Ollama implementation
│   ├── pilot/
│   │   ├── statistics.py           # PilotStatistics: prompt validation metrics (CLI)
│   │   ├── pilot_prs.json          # Controlled pilot PRs (input)
│   │   ├── pilot_human.json        # Human ground-truth labels
│   │   ├── pilot_llm_batch.json    # LLM predictions for the pilot set
│   │   └── plots/                  # Generated confusion matrices
│   └── tests/                      # pytest unit tests
├── notebooks/
│   ├── majority_voting.ipynb       # Combines 3 runs into a final file by majority vote
│   ├── gemini_analysis.ipynb       # Category distribution and analysis
│   └── evaluation_sample.xlsx
├── data/                           # Classification artifacts and generated guidelines
├── requirements.txt
└── README.md
```

## Setup

Requirements: Python 3.10+ and a Google Gemini API key.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the repository root:

```
GEMINI_API_KEY=your_key_here
```

PR dumps and the `django/` folder are git-ignored; place your PR JSON files locally (e.g. `django/prs/`).

## Running

### 1. Classify PRs in batch

The entry point is `src/main.py`. Configure the model, output file, and PR folder there:

```python
runner = LLMRunner(
    model="gemini-3.1-flash-lite",
    api_key=os.getenv("GEMINI_API_KEY"),
    output_file_path="django_gemini_3.1-flash-lite_1.json",
    pr_folder_path="django/prs",
)
runner.run(batch_size=20, max_batches=2000, timeout=300)
```

Run it as a module from the repo root:

```bash
python -m src.main
```

`run()` parameters:
- `batch_size` — number of PRs per LLM request.
- `max_batches` — cap the number of batches (useful for quick tests; `None` = no limit).
- `timeout` — per-request timeout in seconds.

Re-running the same command resumes from where it stopped (already-classified PRs are skipped).

To generate the multiple runs used for majority voting, point `output_file_path` to a different file (e.g. `_0`, `_1`, `_2`) and run again.

### 2. Reprocess specific PRs

Use `LLMRunner.execute_reprocess` to re-run a known set of PR IDs and overwrite their entries:

```python
from src.runner import LLMRunner
import os
from dotenv import load_dotenv
load_dotenv()

runner = LLMRunner(
    model="gemini-3.1-flash-lite",
    api_key=os.getenv("GEMINI_API_KEY"),
    output_file_path="django_gemini_3.1-flash-lite_1.json",
    pr_folder_path="django/prs",
)
runner.execute_reprocess(["PR_ID_1", "PR_ID_2"], batch_size=20, timeout=300)
```

### 3. Validate the prompt on the pilot set

`src/pilot/statistics.py` exposes a CLI via flags:

```bash
# Generate LLM predictions for the pilot set (one batched request)
python -m src.pilot.statistics --create_llm_pilot_prs_batch

# Compute metrics + confusion matrix for the batched predictions
python -m src.pilot.statistics --calculate_statistics_batch

# Per-PR (non-batched) variants:
python -m src.pilot.statistics --create_llm_pilot_prs
python -m src.pilot.statistics --calculate_statistics
```

Metrics are printed to stdout; confusion matrices are saved under `src/pilot/plots/`.

### 4. Aggregate runs (majority voting)

Open `notebooks/majority_voting.ipynb`, set `EXECUTION_FILES` to your run outputs, and execute all cells. For each `pr_id` it picks the OWASP category with at least 2 of 3 votes and writes the consolidated file to `OUTPUT_FILE`.

### 5. Export results for manual evaluation

`src/exporter.py` turns a classification JSON into an `.xlsx` with one row per PR (ID, category, summary, formatted PR, LLM output, and empty evaluation columns):

```bash
python -m src.exporter -i path/to/results.json -o evaluation_output.xlsx
```

### 6. Run the tests

```bash
pytest
```

## Data artifacts (`data/`)

Outputs produced by the pipeline. All classification JSONs share the same per-PR schema:

```json
{
  "pr_id": "MDExOlB1bGxSZXF1ZXN0NTQ0OTQ5OTUy",
  "owasp_category": "A02: Security Misconfiguration",
  "nature": "VULNERABILITY_INTRODUCTION",
  "summary": "Short justification for the classification"
}
```

| File | Description |
| --- | --- |
| `django_gemini_3.1-flash-lite_0.json` | Raw output of run #0 over the Django PRs. |
| `django_gemini_3.1-flash-lite_1.json` | Raw output of run #1 (used for majority voting). |
| `django_gemini_3.1-flash-lite_0_clean.json` | Run #0 after schema cleaning/normalization (one entry per PR). |
| `django_gemini_3.1-flash-lite_0_clean_only_classified.json` | Subset containing only PRs classified as security-related (category ≠ `NONE`). |
| `django_security_user_guidelines.md` | The generated, project-specific security guidelines synthesized from the classifications. |
| `form_responses.csv` | Raw responses from the expert evaluation questionnaire of the generated guidelines. |
