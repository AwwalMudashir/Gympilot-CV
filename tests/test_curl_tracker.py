from app.exercises.curl_tracker import (
    ELBOW_DRIFT,
    INCOMPLETE_RANGE,
    CurlMeasurement,
    CurlTracker,
)
from app.models.curl import CurlPhase


def measurement(elbow: float, captured_at: float, upper_arm: float = 8) -> CurlMeasurement:
    return CurlMeasurement(elbow, upper_arm, captured_at)


def test_counts_full_curl_and_records_tempo() -> None:
    tracker = CurlTracker("session-1", 1)

    assert tracker.update(measurement(165, 0)).phase == CurlPhase.EXTENDED
    assert tracker.update(measurement(130, 0.5)).phase == CurlPhase.CURLING
    assert tracker.update(measurement(50, 1.2)).phase == CurlPhase.CONTRACTED
    assert tracker.update(measurement(85, 1.6)).phase == CurlPhase.LOWERING
    result = tracker.update(measurement(160, 2.5))

    assert result.repetitions == 1
    assert result.phase == CurlPhase.EXTENDED
    assert tracker.summary().average_tempo_seconds == 2.0
    assert tracker.summary().completed is True


def test_does_not_count_incomplete_curl() -> None:
    tracker = CurlTracker("session-2", 1)

    for sample in [
        measurement(165, 0),
        measurement(130, 0.5),
        measurement(85, 1.0),
        measurement(105, 1.5),
        measurement(160, 2.0),
    ]:
        tracker.update(sample)

    summary = tracker.summary()
    assert summary.repetitions == 0
    assert INCOMPLETE_RANGE in summary.form_flags
    assert summary.score == 85


def test_records_elbow_drift() -> None:
    tracker = CurlTracker("session-3", 1)

    for sample in [
        measurement(130, 0.5, upper_arm=35),
        measurement(50, 1.0, upper_arm=35),
        measurement(90, 1.5),
        measurement(160, 2.0),
    ]:
        tracker.update(sample)

    summary = tracker.summary()
    assert summary.repetitions == 1
    assert ELBOW_DRIFT in summary.form_flags
    assert summary.score == 90


def test_low_confidence_response_does_not_change_rep_state() -> None:
    tracker = CurlTracker("session-4", 2)

    response = tracker.pose_missing_response()

    assert response.pose_detected is False
    assert response.repetitions == 0
    assert "visible" in response.feedback
