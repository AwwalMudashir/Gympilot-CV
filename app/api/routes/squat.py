from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.models.squat import (
    SquatFrameResponse,
    SquatSessionRequest,
    SquatSessionResponse,
    SquatSummaryResponse,
)
from app.services.squat_session_service import SquatSessionNotFoundError, SquatSessionService
from app.vision.pose_analyzer import InvalidFrameError, PoseModelUnavailableError

router = APIRouter(prefix="/api/v1/squat", tags=["squat"])
session_service = SquatSessionService()


def get_squat_session_service() -> SquatSessionService:
    return session_service


Service = Annotated[SquatSessionService, Depends(get_squat_session_service)]


@router.post("/sessions", response_model=SquatSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(body: SquatSessionRequest, service: Service) -> SquatSessionResponse:
    summary = service.start(body.target_repetitions)
    return SquatSessionResponse(
        session_id=summary.session_id,
        target_repetitions=summary.target_repetitions,
    )


@router.post("/sessions/{session_id}/frames", response_model=SquatFrameResponse)
async def analyse_frame(
    session_id: UUID,
    frame: Annotated[UploadFile, File(description="Sampled JPEG or PNG camera frame")],
    service: Service,
) -> SquatFrameResponse:
    if frame.content_type not in {"image/jpeg", "image/jpg", "image/png"}:
        raise HTTPException(status_code=415, detail="Only JPEG and PNG frames are supported")
    frame_bytes = await frame.read()
    if not frame_bytes or len(frame_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Frame must be between 1 byte and 8 MB")
    try:
        return service.analyse(session_id, frame_bytes)
    except SquatSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidFrameError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PoseModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/sessions/{session_id}/finish", response_model=SquatSummaryResponse)
async def finish_session(session_id: UUID, service: Service) -> SquatSummaryResponse:
    try:
        return service.finish(session_id)
    except SquatSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_session(session_id: UUID, service: Service) -> Response:
    try:
        service.cancel(session_id)
    except SquatSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
