from fastapi import FastAPI


app = FastAPI(
    title="Your Spot API",
    description=(
        "Backend API for creating personal locations "
        "and sharing them with private groups."
    ),
    version="0.1.0",
)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
