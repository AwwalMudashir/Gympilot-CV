from collections import deque

from fastapi.testclient import TestClient

from app.api.routes.curl import get_curl_session_service
from app.exercises.curl_tracker import CurlMeasurement
from app.main import app
from app.services.curl_session_service import CurlSessionService


class FakePoseAnalyzer:
    def __init__(self) -> None:
        self.measurements = deque(
            [
                CurlMeasurement(130, 8, 0.5),
                CurlMeasurement(50, 8, 1.0),
                CurlMeasurement(90, 8, 1.5),
                CurlMeasurement(160, 8, 2.5),
            ]
        )

    def analyse_curl_frame(self, _frame_bytes: bytes, _captured_at: float):
        return self.measurements.popleft()


def test_runs_sampled_frame_curl_session() -> None:
    service = CurlSessionService(FakePoseAnalyzer())
    app.dependency_overrides[get_curl_session_service] = lambda: service
    try:
        client = TestClient(app)
        created = client.post("/api/v1/curl/sessions", json={"target_repetitions": 1})
        assert created.status_code == 201
        session_id = created.json()["session_id"]

        last = None
        for _ in range(4):
            last = client.post(
                f"/api/v1/curl/sessions/{session_id}/frames",
                files={"frame": ("frame.jpg", b"sample", "image/jpeg")},
            )
            assert last.status_code == 200

        assert last is not None
        assert last.json()["repetitions"] == 1
        assert last.json()["phase"] == "EXTENDED"

        finished = client.post(f"/api/v1/curl/sessions/{session_id}/finish")
        assert finished.status_code == 200
        assert finished.json()["exercise"] == "BICEP_CURL"
        assert finished.json()["completed"] is True
    finally:
        app.dependency_overrides.clear()


def test_rejects_invalid_curl_target() -> None:
    client = TestClient(app)

    response = client.post("/api/v1/curl/sessions", json={"target_repetitions": 0})

    assert response.status_code == 422
