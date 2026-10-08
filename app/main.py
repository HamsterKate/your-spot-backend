from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for creating personal locations "
        "and sharing them with private groups."
    ),
    version=settings.app_version,
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
