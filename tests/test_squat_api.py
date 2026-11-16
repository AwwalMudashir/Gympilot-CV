from collections import deque

from fastapi.testclient import TestClient

from app.api.routes.squat import get_squat_session_service
from app.exercises.squat_tracker import SquatMeasurement
from app.main import app
from app.services.squat_session_service import SquatSessionService


class FakePoseAnalyzer:
    def __init__(self) -> None:
        self.measurements = deque(
            [
                SquatMeasurement(145, 120, 10, 0.5),
                SquatMeasurement(110, 90, 15, 1.0),
                SquatMeasurement(125, 105, 15, 1.5),
                SquatMeasurement(165, 165, 10, 2.5),
            ]
        )

    def analyse_squat_frame(self, _frame_bytes: bytes, _captured_at: float):
        return self.measurements.popleft()


def test_runs_sampled_frame_session() -> None:
    service = SquatSessionService(FakePoseAnalyzer())
    app.dependency_overrides[get_squat_session_service] = lambda: service
    try:
        client = TestClient(app)
        created = client.post("/api/v1/squat/sessions", json={"target_repetitions": 1})
        assert created.status_code == 201
        session_id = created.json()["session_id"]

        last = None
        for _ in range(4):
            last = client.post(
                f"/api/v1/squat/sessions/{session_id}/frames",
                files={"frame": ("frame.jpg", b"sample", "image/jpeg")},
            )
            assert last.status_code == 200

        assert last is not None
        assert last.json()["repetitions"] == 1
        assert last.json()["phase"] == "STANDING"

        finished = client.post(f"/api/v1/squat/sessions/{session_id}/finish")
        assert finished.status_code == 200
        assert finished.json()["completed"] is True
    finally:
        app.dependency_overrides.clear()


def test_rejects_unsupported_frame_type() -> None:
    service = SquatSessionService(FakePoseAnalyzer())
    app.dependency_overrides[get_squat_session_service] = lambda: service
    try:
        client = TestClient(app)
        session_id = client.post(
            "/api/v1/squat/sessions", json={"target_repetitions": 1}
        ).json()["session_id"]
        response = client.post(
            f"/api/v1/squat/sessions/{session_id}/frames",
            files={"frame": ("frame.txt", b"sample", "text/plain")},
        )
        assert response.status_code == 415
    finally:
        app.dependency_overrides.clear()
