"""
FastAPI application entry point.
"""
from fastapi import FastAPI
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


@app.get("/", tags=["Health"])
async def root():
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
