from dataclasses import dataclass
from statistics import fmean

from app.models.curl import CurlFrameResponse, CurlPhase, CurlSummaryResponse

ELBOW_DRIFT = "ELBOW_DRIFT"
INCOMPLETE_RANGE = "INCOMPLETE_RANGE"


@dataclass(frozen=True)
class CurlMeasurement:
    elbow_angle: float
    upper_arm_angle: float
    captured_at: float


class CurlTracker:
    extended_angle = 155.0
    curl_started_angle = 145.0
    contracted_angle = 55.0
    direction_hysteresis = 4.0
    elbow_drift_limit = 28.0

    def __init__(self, session_id: str, target_repetitions: int) -> None:
        self.session_id = session_id
        self.target_repetitions = target_repetitions
        self.phase = CurlPhase.EXTENDED
        self.repetitions = 0
        self.last_elbow_angle: float | None = None
        self.rep_started_at: float | None = None
        self.rep_tempos: list[float] = []
        self.form_flag_counts: dict[str, int] = {}
        self.current_rep_flags: set[str] = set()
        self.reached_contraction = False

    def update(self, measurement: CurlMeasurement) -> CurlFrameResponse:
        elbow_angle = measurement.elbow_angle

        if self.phase == CurlPhase.EXTENDED and elbow_angle < self.curl_started_angle:
            self.phase = CurlPhase.CURLING
            self.rep_started_at = measurement.captured_at
            self.reached_contraction = False
            self.current_rep_flags = set()

        if (
            self.phase != CurlPhase.EXTENDED
            and measurement.upper_arm_angle > self.elbow_drift_limit
        ):
            self.current_rep_flags.add(ELBOW_DRIFT)

        if self.phase == CurlPhase.CURLING:
            if elbow_angle <= self.contracted_angle:
                self.phase = CurlPhase.CONTRACTED
                self.reached_contraction = True
            elif self._is_lowering(elbow_angle):
                self.phase = CurlPhase.LOWERING
                self.current_rep_flags.add(INCOMPLETE_RANGE)

        elif self.phase == CurlPhase.CONTRACTED and self._is_lowering(elbow_angle):
            self.phase = CurlPhase.LOWERING

        elif self.phase == CurlPhase.LOWERING and elbow_angle >= self.extended_angle:
            self._finish_attempt(measurement.captured_at)
            self.phase = CurlPhase.EXTENDED

        self.last_elbow_angle = elbow_angle
        return self.frame_response(measurement)

    def pose_missing_response(self) -> CurlFrameResponse:
        return CurlFrameResponse(
            session_id=self.session_id,
            pose_detected=False,
            repetitions=self.repetitions,
            target_repetitions=self.target_repetitions,
            phase=self.phase,
            form_flags=self.form_flags,
            feedback=(
                "Keep one full arm and the same-side hip visible, "
                "then hold the camera steady."
            ),
        )

    def frame_response(self, measurement: CurlMeasurement) -> CurlFrameResponse:
        return CurlFrameResponse(
            session_id=self.session_id,
            pose_detected=True,
            repetitions=self.repetitions,
            target_repetitions=self.target_repetitions,
            phase=self.phase,
            elbow_angle=round(measurement.elbow_angle, 1),
            upper_arm_angle=round(measurement.upper_arm_angle, 1),
            form_flags=self.form_flags,
            feedback=self._feedback(),
        )

    def summary(self) -> CurlSummaryResponse:
        average_tempo = round(fmean(self.rep_tempos), 2) if self.rep_tempos else None
        penalty = (
            self.form_flag_counts.get(INCOMPLETE_RANGE, 0) * 15
            + self.form_flag_counts.get(ELBOW_DRIFT, 0) * 10
        )
        return CurlSummaryResponse(
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

    def _is_lowering(self, elbow_angle: float) -> bool:
        return (
            self.last_elbow_angle is not None
            and elbow_angle >= self.last_elbow_angle + self.direction_hysteresis
        )

    def _finish_attempt(self, captured_at: float) -> None:
        if self.reached_contraction:
            self.repetitions += 1
            if self.rep_started_at is not None:
                self.rep_tempos.append(max(0.1, captured_at - self.rep_started_at))
        else:
            self.current_rep_flags.add(INCOMPLETE_RANGE)

        for flag in self.current_rep_flags:
            self.form_flag_counts[flag] = self.form_flag_counts.get(flag, 0) + 1

        self.current_rep_flags = set()
        self.reached_contraction = False
        self.rep_started_at = None

    def _feedback(self) -> str:
        if ELBOW_DRIFT in self.current_rep_flags:
            return "Keep your elbow close to your side and avoid lifting your upper arm."
        if INCOMPLETE_RANGE in self.current_rep_flags:
            return "Curl the weight closer to your shoulder before lowering."
        if self.phase == CurlPhase.CURLING:
            return "Curl with control while keeping your wrist neutral."
        if self.phase == CurlPhase.CONTRACTED:
            return "Good contraction. Lower the weight slowly."
        if self.phase == CurlPhase.LOWERING:
            return "Keep lowering until your arm is fully extended."
        return "Stand tall, keep your elbow by your side, then begin the curl."
