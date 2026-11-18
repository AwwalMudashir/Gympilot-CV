from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from app.models.curl import (
    CurlFrameResponse,
    CurlSessionRequest,
    CurlSessionResponse,
    CurlSummaryResponse,
)
from app.services.curl_session_service import CurlSessionNotFoundError, CurlSessionService
from app.vision.pose_analyzer import InvalidFrameError, PoseModelUnavailableError

router = APIRouter(prefix="/api/v1/curl", tags=["bicep curl"])
session_service = CurlSessionService()


def get_curl_session_service() -> CurlSessionService:
    return session_service


Service = Annotated[CurlSessionService, Depends(get_curl_session_service)]


@router.post("/sessions", response_model=CurlSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(body: CurlSessionRequest, service: Service) -> CurlSessionResponse:
    summary = service.start(body.target_repetitions)
    return CurlSessionResponse(
        session_id=summary.session_id,
        target_repetitions=summary.target_repetitions,
    )


@router.post("/sessions/{session_id}/frames", response_model=CurlFrameResponse)
async def analyse_frame(
    session_id: UUID,
    frame: Annotated[UploadFile, File(description="Sampled JPEG or PNG camera frame")],
    service: Service,
) -> CurlFrameResponse:
    if frame.content_type not in {"image/jpeg", "image/jpg", "image/png"}:
        raise HTTPException(status_code=415, detail="Only JPEG and PNG frames are supported")
    frame_bytes = await frame.read()
    if not frame_bytes or len(frame_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Frame must be between 1 byte and 8 MB")
    try:
        return service.analyse(session_id, frame_bytes)
    except CurlSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except InvalidFrameError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except PoseModelUnavailableError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.post("/sessions/{session_id}/finish", response_model=CurlSummaryResponse)
async def finish_session(session_id: UUID, service: Service) -> CurlSummaryResponse:
    try:
        return service.finish(session_id)
    except CurlSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_session(session_id: UUID, service: Service) -> Response:
    try:
        service.cancel(session_id)
    except CurlSessionNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
