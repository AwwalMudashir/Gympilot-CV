"""Week 2 MediaPipe spike: draw pose landmarks on a prerecorded video."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import mediapipe as mp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect a person in a prerecorded video and render the MediaPipe pose skeleton."
    )
    parser.add_argument("input", type=Path, help="Path to the source video")
    parser.add_argument("--output", type=Path, required=True, help="Path for the annotated MP4")
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("models/pose_landmarker_lite.task"),
        help="Path to a MediaPipe Pose Landmarker .task model",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Preview frames while processing; press q to stop",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Optional frame limit for a quick spike run",
    )
    return parser.parse_args()


def process_video(
    input_path: Path,
    output_path: Path,
    *,
    model_path: Path,
    display: bool = False,
    max_frames: int | None = None,
) -> tuple[int, int]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Input video does not exist: {input_path}")
    if not model_path.is_file():
        raise FileNotFoundError(f"Pose Landmarker model does not exist: {model_path}")
    if input_path.resolve() == output_path.resolve():
        raise ValueError("Output path must be different from the input path")

    capture = cv2.VideoCapture(str(input_path))
    if not capture.isOpened():
        raise RuntimeError(f"OpenCV could not open the input video: {input_path}")

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = capture.get(cv2.CAP_PROP_FPS)
    if width <= 0 or height <= 0:
        capture.release()
        raise RuntimeError("The input video has invalid dimensions")
    if fps <= 0:
        fps = 30.0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )
    if not writer.isOpened():
        capture.release()
        raise RuntimeError(f"OpenCV could not create the output video: {output_path}")

    vision = mp.tasks.vision
    drawing = vision.drawing_utils
    options = vision.PoseLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    processed = 0
    detected = 0
    try:
        with vision.PoseLandmarker.create_from_options(options) as pose:
            while capture.isOpened():
                ok, frame = capture.read()
                if not ok:
                    break
                if max_frames is not None and processed >= max_frames:
                    break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                media_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = int(processed * 1000 / fps)
                result = pose.detect_for_video(media_image, timestamp_ms)
                if result.pose_landmarks:
                    detected += 1
                    drawing.draw_landmarks(
                        frame,
                        result.pose_landmarks[0],
                        vision.PoseLandmarksConnections.POSE_LANDMARKS,
                        landmark_drawing_spec=drawing.DrawingSpec(
                            color=(63, 163, 108), thickness=2, circle_radius=2
                        ),
                        connection_drawing_spec=drawing.DrawingSpec(
                            color=(201, 242, 107), thickness=2, circle_radius=1
                        ),
                    )

                writer.write(frame)
                processed += 1
                if display:
                    cv2.imshow("GymBro MediaPipe spike", frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
    finally:
        capture.release()
        writer.release()
        if display:
            cv2.destroyAllWindows()

    return processed, detected


def main() -> int:
    args = parse_args()
    try:
        processed, detected = process_video(
            args.input,
            args.output,
            model_path=args.model,
            display=args.display,
            max_frames=args.max_frames,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Error: {error}")
        return 1
    print(
        f"Processed {processed} frames; pose detected in {detected} frames. "
        f"Annotated video: {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
