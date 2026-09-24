"""
Social media feed simulation — ingest replayed posts for demo.
Implements the hashtag/keyword monitoring requirement from Section 2.
"""
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db, AsyncSessionLocal
from app.models.report import Report
from app.api.schemas import SocialPostCreate
from app.ml.scorer import score_report
from app.api.reports import _check_dedup

router = APIRouter(prefix="/social", tags=["Social Feed"])

# Simulated social posts corpus — replayed during demo
SAMPLE_POSTS = [
    {
        "platform": "twitter", "handle": "@weatherwatcher_mumbai",
        "text": "Massive flooding in Dharavi area! Streets completely submerged. #MumbaiFlood #FloodAlert",
        "hashtags": ["MumbaiFlood", "FloodAlert"],
        "lat": 19.039, "lon": 72.855, "age": 24, "verified": False,
    },
    {
        "platform": "twitter", "handle": "@imd_official",
        "text": "Cyclone Biparjoy landfall expected near Kutch coast within 6 hours. Wind speeds 150+ kmph. #CycloneAlert",
        "hashtags": ["CycloneAlert", "BiparjoyLandfall"],
        "lat": 23.059, "lon": 70.112, "age": 120, "verified": True,
    },
    {
        "platform": "twitter", "handle": "@delhi_citizen",
        "text": "Dense fog on NH-44 near Panipat. Visibility less than 10m. Drive carefully. #DelhiFog",
        "hashtags": ["DelhiFog", "FogAlert"],
        "lat": 29.389, "lon": 76.969, "age": 3, "verified": False,
    },
    {
        "platform": "twitter", "handle": "@rajasthan_news",
        "text": "Severe heatwave conditions in Churu — temperature touches 49°C. #HeatwaveAlert #Rajasthan",
        "hashtags": ["HeatwaveAlert", "Rajasthan"],
        "lat": 28.296, "lon": 74.969, "age": 18, "verified": False,
    },
    {
        "platform": "twitter", "handle": "@chennai_rain_watch",
        "text": "Heavy rain with thunderstorm lashing Chennai. AIADMK Nagar inundated. #ChennaiRains",
        "hashtags": ["ChennaiRains", "ThunderStorm"],
        "lat": 13.082, "lon": 80.271, "age": 8, "verified": False,
    },
    {
        "platform": "twitter", "handle": "@odisha_disaster",
        "text": "Cyclone landfall imminent near Puri. Evacuation of coastal villages underway. #OdishaFlood",
        "hashtags": ["OdishaFlood", "Cyclone"],
        "lat": 19.812, "lon": 85.831, "age": 60, "verified": True,
    },
    {
        "platform": "twitter", "handle": "@fake_account99",
        "text": "Snow falling in Mumbai! Unbelievable winter scene. #MumbaiSnow",
        "hashtags": ["MumbaiSnow"],
        "lat": 19.076, "lon": 72.877, "age": 0, "verified": False,
    },
    {
        "platform": "twitter", "handle": "@bengaluru_weather",
        "text": "Massive hailstorm hits Koramangala! Hailstones size of golf balls. Cars damaged. #BangaloreHail",
        "hashtags": ["BangaloreHail", "Hailstorm"],
        "lat": 12.934, "lon": 77.626, "age": 12, "verified": False,
    },
]

HASHTAG_MONITOR = [
    "#FloodAlert", "#CycloneAlert", "#HeatwaveAlert", "#DelhiFog",
    "#ChennaiRains", "#MumbaiFlood", "#OdishaFlood", "#BangaloreHail",
    "#WeatherWatch", "#IMDAlert", "#DisasterAlert",
]

# Map hashtag keywords to event categories
HASHTAG_CATEGORY_MAP = {
    "flood": "flood", "cyclone": "cyclone", "heatwave": "heatwave",
    "fog": "fog", "rain": "rain", "rains": "rain", "hail": "hailstorm",
    "hailstorm": "hailstorm", "thunder": "thunderstorm", "drought": "drought",
}


def infer_category_from_hashtags(hashtags: list[str], text: str) -> str:
    combined = " ".join(hashtags + [text]).lower()
    for kw, cat in HASHTAG_CATEGORY_MAP.items():
        if kw in combined:
            return cat
    return "unknown"


async def _ingest_post(post: dict) -> Report:
    """Convert a social post dict into a scored Report and persist it."""
    category = infer_category_from_hashtags(post.get("hashtags", []), post["text"])
    lat = post.get("lat") or 20.5937
    lon = post.get("lon") or 78.9629

    result = score_report(
        description=post["text"],
        event_category=category,
        latitude=lat,
        longitude=lon,
        account_age_months=post.get("age", 0),
        is_verified_account=post.get("verified", False),
        prior_verified_count=0,
    )

    report = Report(
        submitter_name=post["handle"],
        source_type="social_media",
        event_category=category,
        description=post["text"],
        severity="moderate",
        latitude=lat,
        longitude=lon,
        status=result.auto_status,
        classified_category=result.classified_category,
        classification_confidence=result.classification_confidence,
        credibility_score=result.credibility_score,
        score_breakdown=result.breakdown(),
        consent_given=True,  # assumed for social posts
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    bd = result.breakdown()
    geo = bd.get("step3_geo_temporal", {})
    report.nearest_imd_station = geo.get("nearest_station")
    report.imd_distance_km = geo.get("distance_km")
    report.imd_match = geo.get("event_known_at_station")
    report.geo_score_detail = geo.get("detail")

    async with AsyncSessionLocal() as db:
        db.add(report)
        await db.flush()
        await _check_dedup(report, db)
        await db.commit()

    return report


@router.post("/ingest")
async def ingest_social_post(payload: SocialPostCreate, background_tasks: BackgroundTasks):
    """Ingest a single social post through the scoring pipeline."""
    post = {
        "platform": payload.platform,
        "handle": payload.handle,
        "text": payload.text,
        "hashtags": payload.hashtags,
        "lat": payload.latitude or 20.5937,
        "lon": payload.longitude or 78.9629,
        "age": payload.account_age_months,
        "verified": payload.is_verified,
    }
    report = await _ingest_post(post)
    return {
        "message": "Post ingested",
        "report_id": report.id,
        "credibility_score": report.credibility_score,
        "status": report.status,
        "classified_as": report.classified_category,
    }


@router.post("/replay-demo")
async def replay_demo_feed(background_tasks: BackgroundTasks):
    """
    Replay all sample posts from the demo corpus.
    Each post is scored and stored — demonstrates hashtag monitoring requirement.
    """
    results = []
    for post in SAMPLE_POSTS:
        r = await _ingest_post(post)
        results.append({
            "handle": post["handle"],
            "report_id": r.id,
            "score": r.credibility_score,
            "status": r.status,
        })
    return {"ingested": len(results), "reports": results}


@router.get("/monitored-hashtags")
async def get_monitored_hashtags():
    """Return the list of hashtags/keywords currently being monitored."""
    return {
        "hashtags": HASHTAG_MONITOR,
        "total": len(HASHTAG_MONITOR),
        "category_map": HASHTAG_CATEGORY_MAP,
    }
