import pytest

from app.vision.geometry import calculate_angle


def test_calculates_right_angle() -> None:
    assert calculate_angle((1, 0), (0, 0), (0, 1)) == pytest.approx(90)


def test_rejects_coincident_points() -> None:
    with pytest.raises(ValueError):
        calculate_angle((0, 0), (0, 0), (0, 1))
