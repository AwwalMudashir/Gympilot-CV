from fastapi import FastAPI

from app.api.routes.health import router as health_router

app = FastAPI(
    title="GymPilot Vision Service",
    description="Pose analysis service for supported GymPilot exercises.",
    version="0.1.0",
)
app.include_router(health_router)


@app.get("/", include_in_schema=False)
async def service_info() -> dict[str, str]:
    return {"service": "gympilot-vision", "docs": "/docs", "health": "/health"}
