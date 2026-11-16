from app.exercises.squat_tracker import (
    EXCESSIVE_FORWARD_LEAN,
    INSUFFICIENT_DEPTH,
    SquatMeasurement,
    SquatTracker,
)
from app.models.squat import SquatPhase


def measurement(knee: float, captured_at: float, lean: float = 12) -> SquatMeasurement:
    return SquatMeasurement(knee, 120, lean, captured_at)


def test_counts_full_squat_and_records_tempo() -> None:
    tracker = SquatTracker("session-1", 1)

    assert tracker.update(measurement(170, 0)).phase == SquatPhase.STANDING
    assert tracker.update(measurement(145, 0.5)).phase == SquatPhase.DESCENDING
    assert tracker.update(measurement(110, 1.0)).phase == SquatPhase.BOTTOM
    assert tracker.update(measurement(125, 1.5)).phase == SquatPhase.ASCENDING
    result = tracker.update(measurement(165, 2.5))

    assert result.repetitions == 1
    assert result.phase == SquatPhase.STANDING
    assert tracker.summary().average_tempo_seconds == 2.0
    assert tracker.summary().completed is True


def test_does_not_count_shallow_attempt() -> None:
    tracker = SquatTracker("session-2", 1)

    for sample in [
        measurement(170, 0),
        measurement(145, 0.5),
        measurement(130, 1.0),
        measurement(140, 1.5),
        measurement(165, 2.0),
    ]:
        tracker.update(sample)

    summary = tracker.summary()
    assert summary.repetitions == 0
    assert INSUFFICIENT_DEPTH in summary.form_flags
    assert summary.score == 85


def test_records_excessive_forward_lean() -> None:
    tracker = SquatTracker("session-3", 1)

    for sample in [
        measurement(145, 0.5, lean=50),
        measurement(110, 1.0, lean=50),
        measurement(125, 1.5),
        measurement(165, 2.0),
    ]:
        tracker.update(sample)

    summary = tracker.summary()
    assert summary.repetitions == 1
    assert EXCESSIVE_FORWARD_LEAN in summary.form_flags
    assert summary.score == 92
