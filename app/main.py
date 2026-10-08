from fastapi import FastAPI

from app.core.config import settings
from app.auth.router import router as auth_router

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for creating personal locations "
        "and sharing them with private groups."
    ),
    version=settings.app_version,
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
