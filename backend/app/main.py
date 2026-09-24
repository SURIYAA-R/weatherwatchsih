import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
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

# Locations for the frontend UI file
STATIC_INDEX = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html")
PARENT_INDEX = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "index.html"))


@app.get("/", tags=["Health"])
async def root(request: Request):
    accept = request.headers.get("accept", "")
    # When opened in a web browser, serve the interactive WeatherWatch dashboard!
    if "text/html" in accept:
        for path in [STATIC_INDEX, PARENT_INDEX]:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())

    return {
        "service": "WeatherWatch API",
        "version": "1.0.0",
        "status": "operational",
        "disclaimer": (
            "Crowdsourced supplementary data — not an official IMD alert. "
            "Verify with official sources before acting."
        ),
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
