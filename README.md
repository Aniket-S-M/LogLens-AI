# LogLens AI — Intelligent Log Analysis & Failure Triage

LogLens AI is a Python-based log analysis and failure triage tool that uses a local large language model to identify failures, explain likely causes, recommend debugging actions, and support analysis with historical incident retrieval.

## Features

- **Log parsing:** Extracts log levels, timestamps, and failure information.
- **AI-powered diagnosis:** Uses Ollama with `phi3:mini` to generate structured triage reports.
- **Evidence verification:** Checks that diagnosis excerpts and line numbers correspond to the supplied logs.
- **Historical incident retrieval:** Uses ChromaDB and sentence-transformer embeddings to retrieve potentially relevant past incidents.
- **Failure grouping:** Groups repeated errors using normalized signatures.
- **REST API:** Provides endpoints for log analysis, incident search, regression grouping, and RAG-based analysis.
- **Evaluation:** Includes synthetic evaluation cases and retrieval benchmarks.
- **Web interface:** Provides a Streamlit interface for interacting with the analysis features.

## Tech Stack

- Python 3.12
- FastAPI and Uvicorn
- Ollama (`phi3:mini`)
- Pydantic
- ChromaDB
- Sentence Transformers
- Streamlit
- Pytest

## Architecture

1. Logs are submitted through the API or web interface.
2. The parser and analysis pipeline process the log content.
3. The local LLM generates a structured diagnosis.
4. Evidence verification checks the diagnosis against the original logs.
5. The retrieval component searches historical incidents for potentially relevant context.
6. The API returns the report and available runtime metrics.

Historical similarity is supporting context, not proof of the root cause. Model-generated diagnoses should be reviewed by an engineer.

## Setup

### Prerequisites

- Python 3.12
- Git
- Ollama
- The `phi3:mini` model

### Install

Clone the repository and enter the project directory:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_PROJECT_DIRECTORY>
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project's dependencies using the repository's dependency configuration, then download the model:

```bash
ollama pull phi3:mini
```

Set the Python import path in PowerShell:

```powershell
$env:PYTHONPATH = "src"
```

### Run the API

```powershell
python -m uvicorn loglens.api:app --reload
```

Open `http://127.0.0.1:8000/docs` to explore the API.

### Run the tests

```powershell
$env:PYTHONPATH = "src"
python -m pytest -v
```

## Evaluation

The project includes synthetic evaluation cases and a small historical-incident retrieval benchmark. These are useful for regression testing but do not establish production-level accuracy. Evaluation results should be reported alongside dataset size and test conditions.

## Current Limitations

- Local inference latency depends on the machine and model configuration.
- Historical incident retrieval depends on the quality and coverage of the incident dataset.
- The root cause suggested by an LLM may be uncertain.
- This version has not yet been fully production-hardened or deployed to a cloud environment.

## Roadmap

- Containerized deployment
- Continuous integration with GitHub Actions
- Expanded LLM evaluation and regression testing
- Operational monitoring and improved error handling

## Disclaimer

LogLens AI is a debugging aid. Its output is not a substitute for verifying system behavior and reviewing logs directly.
