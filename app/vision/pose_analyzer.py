import os
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

from app.exercises.squat_tracker import SquatMeasurement
from app.vision.geometry import calculate_angle


class PoseModelUnavailableError(RuntimeError):
    pass


class InvalidFrameError(ValueError):
    pass


class PoseAnalyzer:
    minimum_visibility = 0.55

    def __init__(self, model_path: str | Path | None = None) -> None:
        configured_path = model_path or os.getenv(
            "GYMBRO_POSE_MODEL_PATH", "models/pose_landmarker_lite.task"
        )
        self.model_path = Path(configured_path)
        self._landmarker = None

    def analyse_squat_frame(
        self,
        frame_bytes: bytes,
        captured_at: float,
    ) -> SquatMeasurement | None:
        encoded = np.frombuffer(frame_bytes, dtype=np.uint8)
        frame = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if frame is None:
            raise InvalidFrameError("The uploaded frame is not a readable JPEG or PNG image")

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._pose_landmarker().detect(image)
        if not result.pose_landmarks:
            return None

        landmarks = result.pose_landmarks[0]
        side = self._most_visible_side(landmarks)
        if side is None:
            return None

        shoulder, hip, knee, ankle = side
        knee_angle = calculate_angle(self._point(hip), self._point(knee), self._point(ankle))
        hip_angle = calculate_angle(self._point(shoulder), self._point(hip), self._point(knee))
        vertical_above_hip = (hip.x, hip.y - 1.0)
        forward_lean = calculate_angle(self._point(shoulder), self._point(hip), vertical_above_hip)
        return SquatMeasurement(knee_angle, hip_angle, forward_lean, captured_at)

    def close(self) -> None:
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None

    def _pose_landmarker(self):
        if self._landmarker is not None:
            return self._landmarker
        if not self.model_path.is_file():
            raise PoseModelUnavailableError(
                f"Pose model not found at {self.model_path}. "
                "Download pose_landmarker_lite.task first."
            )

        base_options = mp.tasks.BaseOptions(model_asset_path=str(self.model_path))
        options = mp.tasks.vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
        )
        self._landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(options)
        return self._landmarker

    def _most_visible_side(self, landmarks):
        pose_landmark = mp.tasks.vision.PoseLandmark
        sides = (
            (
                landmarks[pose_landmark.LEFT_SHOULDER],
                landmarks[pose_landmark.LEFT_HIP],
                landmarks[pose_landmark.LEFT_KNEE],
                landmarks[pose_landmark.LEFT_ANKLE],
            ),
            (
                landmarks[pose_landmark.RIGHT_SHOULDER],
                landmarks[pose_landmark.RIGHT_HIP],
                landmarks[pose_landmark.RIGHT_KNEE],
                landmarks[pose_landmark.RIGHT_ANKLE],
            ),
        )
        visible_sides = [
            side for side in sides if min(landmark.visibility or 0.0 for landmark in side)
            >= self.minimum_visibility
        ]
        if not visible_sides:
            return None
        return max(visible_sides, key=lambda side: sum(item.visibility or 0.0 for item in side))

    @staticmethod
    def _point(landmark) -> tuple[float, float]:
        return landmark.x, landmark.y
