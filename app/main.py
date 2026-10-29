from fastapi import FastAPI

from app.core.config import settings
from app.auth.router import router as auth_router
from app.groups.router import router as groups_router
from app.places.router import router as places_router
from app.taxonomy.router import router as taxonomy_router

app = FastAPI(
    title=settings.app_name,
    description=(
        "Backend API for creating personal locations "
        "and sharing them with private groups."
    ),
    version=settings.app_version,
    docs="/docs",
    redoc="/redoc",
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(groups_router, prefix=settings.api_v1_prefix)
app.include_router(places_router, prefix=settings.api_v1_prefix)
app.include_router(taxonomy_router, prefix=settings.api_v1_prefix)


@app.get(settings.api_v1_prefix, tags=["health"])
async def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "Spots API",
        "environment": "production",
        "docs": f"{settings.api_v1_prefix}/docs"
    }
