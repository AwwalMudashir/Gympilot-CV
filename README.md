# GymBro Vision Service

Small Python service for pose-based exercise analysis. It includes the health endpoint, the prerecorded-video landmark spike and the Week 3 sampled-frame squat pipeline. Bicep-curl tracking remains a Week 4 item.

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

### Run with Docker

The image installs MediaPipe/OpenCV and downloads the Pose Landmarker model at
build time, so the running container does not depend on a model file from the
host machine:

```powershell
docker compose up --build
```

The service is then available at `http://localhost:8000`.

## Deploy the vision service to Render

1. Push this vision-service repository to GitHub.
2. In Render, select **New > Blueprint** and connect this repository.
3. Render reads `render.yaml`, builds the Dockerfile, and checks `/health`.
4. Verify `https://YOUR-VISION-SERVICE.onrender.com/docs` after deployment.

The service binds to Render's automatically supplied `PORT`. MediaPipe is CPU
and memory intensive, so a free Render instance is suitable for development
and demonstrations but should be load-tested before production use.

## Week 2 MediaPipe video spike

Download Google's Pose Landmarker Lite task model once, then run the spike with a prerecorded MP4. It uses the current MediaPipe Tasks video API, detects pose landmarks, draws the skeleton and writes a new annotated video without changing the source file:

```powershell
New-Item -ItemType Directory -Force .\models
Invoke-WebRequest -Uri "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task" -OutFile ".\models\pose_landmarker_lite.task"
uv run python scripts/pose_video_spike.py .\samples\squat.mp4 --output .\output\squat-skeleton.mp4
```

For a quick check, add `--max-frames 120`. Add `--display` to preview the output and press `q` to stop. Use `--model` if the `.task` file is elsewhere. The script prints the number of processed frames and the number in which a pose was detected.

## Test and lint

```powershell
pytest
ruff check .
```

## Week 3 squat API

Download the Pose Landmarker model as shown above, then start the service. The phone creates an analysis session, uploads a sampled JPEG frame roughly once per second, and finishes the session to receive a compact summary. Raw frames are processed only by this service and are not forwarded to Spring Boot or an LLM.

```text
POST   /api/v1/squat/sessions
POST   /api/v1/squat/sessions/{sessionId}/frames
POST   /api/v1/squat/sessions/{sessionId}/finish
DELETE /api/v1/squat/sessions/{sessionId}
```

For the classroom demo, use a side or three-quarter view with the phone approximately 2.5–3.5 metres away. Place it around hip height and keep the shoulders, hips, knees and ankles visible under even lighting.

The state machine follows `STANDING -> DESCENDING -> BOTTOM -> ASCENDING -> STANDING`. A repetition is counted only after reaching the bottom threshold and returning to standing. The initial form flags are `INSUFFICIENT_DEPTH` and `EXCESSIVE_FORWARD_LEAN`.

The final session contract is compact JSON similar to:

```json
{
  "exercise": "BODYWEIGHT_SQUAT",
  "repetitions": 10,
  "average_tempo_seconds": 3.2,
  "form_flags": ["EXCESSIVE_FORWARD_LEAN"],
  "score": 92
}
```
