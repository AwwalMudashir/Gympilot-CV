from dataclasses import dataclass
from statistics import fmean

from app.models.squat import SquatFrameResponse, SquatPhase, SquatSummaryResponse

INSUFFICIENT_DEPTH = "INSUFFICIENT_DEPTH"
EXCESSIVE_FORWARD_LEAN = "EXCESSIVE_FORWARD_LEAN"


@dataclass(frozen=True)
class SquatMeasurement:
    knee_angle: float
    hip_angle: float
    forward_lean_angle: float
    captured_at: float


class SquatTracker:
    standing_angle = 160.0
    descent_angle = 150.0
    bottom_angle = 115.0
    direction_hysteresis = 5.0
    forward_lean_limit = 42.0

    def __init__(self, session_id: str, target_repetitions: int) -> None:
        self.session_id = session_id
        self.target_repetitions = target_repetitions
        self.phase = SquatPhase.STANDING
        self.repetitions = 0
        self.last_knee_angle: float | None = None
        self.minimum_knee_angle = 180.0
        self.rep_started_at: float | None = None
        self.rep_tempos: list[float] = []
        self.form_flag_counts: dict[str, int] = {}
        self.current_rep_flags: set[str] = set()
        self.reached_bottom = False

    def update(self, measurement: SquatMeasurement) -> SquatFrameResponse:
        knee_angle = measurement.knee_angle
        self.minimum_knee_angle = min(self.minimum_knee_angle, knee_angle)
        if measurement.forward_lean_angle > self.forward_lean_limit:
            self.current_rep_flags.add(EXCESSIVE_FORWARD_LEAN)

        if self.phase == SquatPhase.STANDING and knee_angle < self.descent_angle:
            self.phase = SquatPhase.DESCENDING
            self.rep_started_at = measurement.captured_at
            self.minimum_knee_angle = knee_angle
            self.reached_bottom = False
            self.current_rep_flags = set()
            if measurement.forward_lean_angle > self.forward_lean_limit:
                self.current_rep_flags.add(EXCESSIVE_FORWARD_LEAN)

        elif self.phase == SquatPhase.DESCENDING:
            if knee_angle <= self.bottom_angle:
                self.phase = SquatPhase.BOTTOM
                self.reached_bottom = True
            elif self._is_rising(knee_angle):
                self.phase = SquatPhase.ASCENDING
                self.current_rep_flags.add(INSUFFICIENT_DEPTH)

        elif self.phase == SquatPhase.BOTTOM and self._is_rising(knee_angle):
            self.phase = SquatPhase.ASCENDING

        elif self.phase == SquatPhase.ASCENDING and knee_angle >= self.standing_angle:
            self._finish_attempt(measurement.captured_at)
            self.phase = SquatPhase.STANDING

        self.last_knee_angle = knee_angle
        return self.frame_response(measurement)

    def pose_missing_response(self) -> SquatFrameResponse:
        return SquatFrameResponse(
            session_id=self.session_id,
            pose_detected=False,
            repetitions=self.repetitions,
            target_repetitions=self.target_repetitions,
            phase=self.phase,
            form_flags=self.form_flags,
            feedback="Step back until your shoulders, hips, knees and ankles are visible.",
        )

    def frame_response(self, measurement: SquatMeasurement) -> SquatFrameResponse:
        return SquatFrameResponse(
            session_id=self.session_id,
            pose_detected=True,
            repetitions=self.repetitions,
            target_repetitions=self.target_repetitions,
            phase=self.phase,
            knee_angle=round(measurement.knee_angle, 1),
            hip_angle=round(measurement.hip_angle, 1),
            forward_lean_angle=round(measurement.forward_lean_angle, 1),
            form_flags=self.form_flags,
            feedback=self._feedback(),
        )

    def summary(self) -> SquatSummaryResponse:
        average_tempo = round(fmean(self.rep_tempos), 2) if self.rep_tempos else None
        penalty = (
            self.form_flag_counts.get(INSUFFICIENT_DEPTH, 0) * 15
            + self.form_flag_counts.get(EXCESSIVE_FORWARD_LEAN, 0) * 8
        )
        return SquatSummaryResponse(
            session_id=self.session_id,
            repetitions=self.repetitions,
            target_repetitions=self.target_repetitions,
            average_tempo_seconds=average_tempo,
            form_flags=self.form_flags,
            score=float(max(0, 100 - penalty)),
            completed=self.repetitions >= self.target_repetitions,
        )

    @property
    def form_flags(self) -> list[str]:
        return sorted(self.form_flag_counts | {flag: 1 for flag in self.current_rep_flags})

    def _is_rising(self, knee_angle: float) -> bool:
        return (
            self.last_knee_angle is not None
            and knee_angle >= self.last_knee_angle + self.direction_hysteresis
        )

    def _finish_attempt(self, captured_at: float) -> None:
        if self.reached_bottom:
            self.repetitions += 1
            if self.rep_started_at is not None:
                self.rep_tempos.append(max(0.1, captured_at - self.rep_started_at))
        else:
            self.current_rep_flags.add(INSUFFICIENT_DEPTH)

        for flag in self.current_rep_flags:
            self.form_flag_counts[flag] = self.form_flag_counts.get(flag, 0) + 1

        self.current_rep_flags = set()
        self.reached_bottom = False
        self.minimum_knee_angle = 180.0
        self.rep_started_at = None

    def _feedback(self) -> str:
        if EXCESSIVE_FORWARD_LEAN in self.current_rep_flags:
            return "Keep your chest lifted and brace your core."
        if INSUFFICIENT_DEPTH in self.current_rep_flags:
            return "Sit a little deeper before driving back up."
        if self.phase == SquatPhase.DESCENDING:
            return "Lower with control and keep your knees tracking over your feet."
        if self.phase == SquatPhase.BOTTOM:
            return "Good depth. Drive through your feet."
        if self.phase == SquatPhase.ASCENDING:
            return "Stand tall to finish the repetition."
        return "Stand tall, brace your core, then begin the next repetition."
