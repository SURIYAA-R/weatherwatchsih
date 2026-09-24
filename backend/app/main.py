from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import init_db
from app.api.reports import router as reports_router
from app.api.social import router as social_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="WeatherWatch — National Weather Big Data Analytics Platform",
    description=(
        "Citizen crowdsourcing + automated IMD/satellite cross-verification. "
        "Every report is scored 0–100 for credibility before reaching the public map."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reports_router)
app.include_router(social_router)

# Locations for the frontend UI file (robust Path resolution)
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_INDEX = BASE_DIR / "static" / "index.html"
PARENT_INDEX = BASE_DIR.parent / "frontend" / "index.html"


def get_index_path() -> Path | None:
    for p in [STATIC_INDEX, PARENT_INDEX]:
        if p.is_file():
            return p
    return None


@app.get("/", tags=["UI & Health"], response_class=HTMLResponse)
async def root(format: str | None = None):
    # If explicitly requested format=json, return the service info JSON
    if format == "json":
        return JSONResponse(content={
            "service": "WeatherWatch API",
            "version": "1.0.0",
            "status": "operational",
            "disclaimer": (
                "Crowdsourced supplementary data — not an official IMD alert. "
                "Verify with official sources before acting."
            ),
        })

    # By default, serve the complete interactive WeatherWatch map & web application!
    index_file = get_index_path()
    if index_file:
        return FileResponse(index_file, media_type="text/html")

    return JSONResponse(content={
        "service": "WeatherWatch API",
        "version": "1.0.0",
        "status": "operational",
        "message": "Frontend index.html not found on server."
    })


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
