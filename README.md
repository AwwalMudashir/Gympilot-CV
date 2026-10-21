# GymPilot Vision Service

Small Python service for pose-based exercise analysis. The Week 1 increment intentionally exposes only a health endpoint; squat and bicep-curl pipelines belong to Weeks 3 and 4.

## Prerequisites

- Python 3.11 or 3.12 (MediaPipe compatibility is most predictable on these versions)
- A virtual environment

## Setup (PowerShell)

With `uv` (recommended; uses the committed lockfile):

```powershell
uv sync
```

Or with standard Python tooling:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Run

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/health` or the interactive API documentation at `http://localhost:8000/docs`.

## Test and lint

```powershell
pytest
ruff check .
```

## Planned structure

Add shared landmark/angle utilities under `app/vision`, then exercise-specific state machines under `app/exercises`. The service should receive sampled frames or short recorded sets, return structured metrics, and never send raw video to Spring Boot or an LLM.

The planned session result contract is compact JSON similar to:

```json
{
  "exercise": "SQUAT",
  "repetitions": 10,
  "averageRepDuration": 3.2,
  "formWarnings": ["FORWARD_LEAN"]
}
```
