from fastapi import FastAPI

from app.api.routes.curl import router as curl_router
from app.api.routes.health import router as health_router
from app.api.routes.squat import router as squat_router

app = FastAPI(
    title="GymBro Vision Service",
    description="Pose analysis service for supported GymBro exercises.",
    version="0.1.0",
)
app.include_router(health_router)
app.include_router(squat_router)
app.include_router(curl_router)


@app.get("/", include_in_schema=False)
async def service_info() -> dict[str, str]:
    return {"service": "gymbro-vision", "docs": "/docs", "health": "/health"}
