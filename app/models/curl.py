from enum import StrEnum

from pydantic import BaseModel, Field


class CurlPhase(StrEnum):
    EXTENDED = "EXTENDED"
    CURLING = "CURLING"
    CONTRACTED = "CONTRACTED"
    LOWERING = "LOWERING"


class CurlSessionRequest(BaseModel):
    target_repetitions: int = Field(ge=1, le=50)


class CurlSessionResponse(BaseModel):
    session_id: str
    exercise: str = "BICEP_CURL"
    target_repetitions: int
    repetitions: int = 0
    phase: CurlPhase = CurlPhase.EXTENDED


class CurlFrameResponse(BaseModel):
    session_id: str
    pose_detected: bool
    repetitions: int
    target_repetitions: int
    phase: CurlPhase
    elbow_angle: float | None = None
    upper_arm_angle: float | None = None
    form_flags: list[str] = Field(default_factory=list)
    feedback: str


class CurlSummaryResponse(BaseModel):
    session_id: str
    exercise: str = "BICEP_CURL"
    repetitions: int
    target_repetitions: int
    average_tempo_seconds: float | None = None
    form_flags: list[str] = Field(default_factory=list)
    score: float
    completed: bool
