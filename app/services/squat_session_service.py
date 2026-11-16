from threading import RLock
from time import monotonic
from uuid import UUID, uuid4

from app.exercises.squat_tracker import SquatTracker
from app.models.squat import SquatFrameResponse, SquatSummaryResponse
from app.vision.pose_analyzer import PoseAnalyzer


class SquatSessionNotFoundError(LookupError):
    pass


class SquatSessionService:
    def __init__(self, pose_analyzer: PoseAnalyzer | None = None) -> None:
        self.pose_analyzer = pose_analyzer or PoseAnalyzer()
        self._sessions: dict[UUID, SquatTracker] = {}
        self._lock = RLock()

    def start(self, target_repetitions: int) -> SquatSummaryResponse:
        session_id = uuid4()
        tracker = SquatTracker(str(session_id), target_repetitions)
        with self._lock:
            self._sessions[session_id] = tracker
        return tracker.summary()

    def analyse(self, session_id: UUID, frame_bytes: bytes) -> SquatFrameResponse:
        with self._lock:
            tracker = self._require(session_id)
            measurement = self.pose_analyzer.analyse_squat_frame(frame_bytes, monotonic())
            if measurement is None:
                return tracker.pose_missing_response()
            return tracker.update(measurement)

    def finish(self, session_id: UUID) -> SquatSummaryResponse:
        with self._lock:
            tracker = self._require(session_id)
            summary = tracker.summary()
            del self._sessions[session_id]
            return summary

    def cancel(self, session_id: UUID) -> None:
        with self._lock:
            if self._sessions.pop(session_id, None) is None:
                raise SquatSessionNotFoundError("Squat analysis session was not found")

    def _require(self, session_id: UUID) -> SquatTracker:
        tracker = self._sessions.get(session_id)
        if tracker is None:
            raise SquatSessionNotFoundError("Squat analysis session was not found")
        return tracker
