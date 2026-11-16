from enum import StrEnum

from pydantic import BaseModel, Field


class SquatPhase(StrEnum):
    STANDING = "STANDING"
    DESCENDING = "DESCENDING"
    BOTTOM = "BOTTOM"
    ASCENDING = "ASCENDING"


class SquatSessionRequest(BaseModel):
    target_repetitions: int = Field(ge=1, le=50)


class SquatSessionResponse(BaseModel):
    session_id: str
    exercise: str = "BODYWEIGHT_SQUAT"
    target_repetitions: int
    repetitions: int = 0
    phase: SquatPhase = SquatPhase.STANDING


class SquatFrameResponse(BaseModel):
    session_id: str
    pose_detected: bool
    repetitions: int
    target_repetitions: int
    phase: SquatPhase
    knee_angle: float | None = None
    hip_angle: float | None = None
    forward_lean_angle: float | None = None
    form_flags: list[str] = Field(default_factory=list)
    feedback: str


class SquatSummaryResponse(BaseModel):
    session_id: str
    exercise: str = "BODYWEIGHT_SQUAT"
    repetitions: int
    target_repetitions: int
    average_tempo_seconds: float | None = None
    form_flags: list[str] = Field(default_factory=list)
    score: float
    completed: bool
