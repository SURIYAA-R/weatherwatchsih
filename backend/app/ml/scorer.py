"""
Section 3 — Fake/Misinformation Detection Scoring Pipeline.

Implements the exact 3-step algorithm from the master prompt:

  Step 1: Source credibility score    (0–40 pts)
  Step 2: Content consistency score   (0–30 pts)
  Step 3: Geo-temporal cross-ref score(0–30 pts)
  Total:  0–100 — reports < 40 are auto-flagged for admin review.

All scoring is deterministic, offline, and fully traceable.
"""
from __future__ import annotations
import re
import math
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from app.ml.classifier import classify_event, keyword_match_score
from app.ml.imd_stations import geo_temporal_score

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
AUTO_FLAG_THRESHOLD = 40.0   # Reports below this go to admin review queue
AUTO_PUBLISH_THRESHOLD = 70.0  # Reports above this auto-publish


# ─────────────────────────────────────────────────────────────
# Step 1 — Source Credibility (0–40 pts)
# ─────────────────────────────────────────────────────────────
def _step1_source_credibility(
    account_age_months: int,
    is_verified_account: bool,
    prior_verified_count: int,
) -> dict:
    """
    +10  Account age > 6 months
    +15  Verified / official account
    +15  Prior verified reports (scaled, capped at 15)
    """
    pts_age = 10.0 if account_age_months >= 6 else round(account_age_months / 6 * 10, 2)
    pts_verified = 15.0 if is_verified_account else 0.0
    # Scale: 1 prior → 3 pts, 5 prior → 15 pts (cap)
    pts_history = round(min(prior_verified_count * 3.0, 15.0), 2)

    total = pts_age + pts_verified + pts_history
    return {
        "step": 1,
        "name": "Source Credibility",
        "max_pts": 40,
        "pts_account_age": pts_age,
        "pts_verified": pts_verified,
        "pts_prior_history": pts_history,
        "total": round(total, 2),
        "detail": (
            f"Account age {account_age_months}mo → +{pts_age}pts; "
            f"Verified={is_verified_account} → +{pts_verified}pts; "
            f"Prior verified reports={prior_verified_count} → +{pts_history}pts."
        ),
    }


# ─────────────────────────────────────────────────────────────
# Step 2 — Content Consistency (0–30 pts)
# ─────────────────────────────────────────────────────────────
def _step2_content_consistency(
    claimed_category: str,
    description: str,
    image_url: Optional[str],
    image_exif_valid: Optional[bool],
) -> dict:
    """
    +15  Claimed category matches NLP keyword extraction from description
    +15  Image EXIF timestamp valid (or no image: neutral 7.5 pts)
    """
    kw_score = keyword_match_score(claimed_category, description)
    pts_nlp = round(kw_score * 15.0, 2)

    if image_url:
        pts_image = 15.0 if image_exif_valid else 0.0
        image_detail = f"Image present, EXIF valid={image_exif_valid} → +{pts_image}pts."
    else:
        pts_image = 7.5  # No image — neutral, neither bonus nor penalty
        image_detail = "No image submitted → neutral +7.5pts."

    total = pts_nlp + pts_image
    classified, conf = classify_event(description)
    return {
        "step": 2,
        "name": "Content Consistency",
        "max_pts": 30,
        "pts_nlp_match": pts_nlp,
        "pts_image_forensic": pts_image,
        "total": round(total, 2),
        "nlp_classified_as": classified,
        "nlp_confidence": round(conf, 3),
        "detail": (
            f"NLP classified as '{classified}' (conf={conf:.2f}); "
            f"claimed='{claimed_category}'; keyword match → +{pts_nlp}pts. "
            + image_detail
        ),
    }


# ─────────────────────────────────────────────────────────────
# Step 3 — Geo-Temporal Cross-Reference (0–30 pts)
# ─────────────────────────────────────────────────────────────
def _step3_geo_temporal(lat: float, lon: float, event_category: str) -> dict:
    geo = geo_temporal_score(lat, lon, event_category)
    return {
        "step": 3,
        "name": "Geo-Temporal Cross-Reference",
        "max_pts": 30,
        "total": geo["score"],
        "nearest_station": geo["station_name"],
        "nearest_station_state": geo.get("station_state", ""),
        "station_lat": geo.get("station_lat"),
        "station_lon": geo.get("station_lon"),
        "distance_km": geo["distance_km"],
        "event_known_at_station": geo["event_known_at_station"],
        "detail": geo["detail"],
    }


# ─────────────────────────────────────────────────────────────
# Main scoring entry point
# ─────────────────────────────────────────────────────────────
@dataclass
class ScoringResult:
    credibility_score: float          # 0–100
    step1: dict
    step2: dict
    step3: dict
    auto_status: str                  # 'published' | 'flagged' | 'pending'
    classified_category: str
    classification_confidence: float
    flags: list[str] = field(default_factory=list)

    def breakdown(self) -> dict:
        return {
            "total_score": self.credibility_score,
            "auto_status": self.auto_status,
            "threshold_flag": AUTO_FLAG_THRESHOLD,
            "threshold_publish": AUTO_PUBLISH_THRESHOLD,
            "step1_source_credibility": self.step1,
            "step2_content_consistency": self.step2,
            "step3_geo_temporal": self.step3,
            "flags": self.flags,
            "classified_category": self.classified_category,
            "classification_confidence": self.classification_confidence,
        }


def score_report(
    *,
    description: str,
    event_category: str,
    latitude: float,
    longitude: float,
    account_age_months: int = 0,
    is_verified_account: bool = False,
    prior_verified_count: int = 0,
    image_url: Optional[str] = None,
    image_exif_valid: Optional[bool] = None,
) -> ScoringResult:
    """
    Run the full 3-step credibility scoring pipeline.
    Returns a ScoringResult with all breakdown details.
    """
    s1 = _step1_source_credibility(account_age_months, is_verified_account, prior_verified_count)
    s2 = _step2_content_consistency(event_category, description, image_url, image_exif_valid)
    s3 = _step3_geo_temporal(latitude, longitude, event_category)

    total = round(s1["total"] + s2["total"] + s3["total"], 2)
    total = min(100.0, max(0.0, total))

    # Determine auto-status
    flags = []
    if total < AUTO_FLAG_THRESHOLD:
        auto_status = "flagged"
        flags.append(f"Score {total} < threshold {AUTO_FLAG_THRESHOLD} — sent to admin review.")
    elif total >= AUTO_PUBLISH_THRESHOLD:
        auto_status = "published"
    else:
        auto_status = "pending"

    # NLP classification (independent of claimed category)
    classified, conf = classify_event(description)
    if classified != event_category and classified != "unknown":
        flags.append(
            f"Submitted category '{event_category}' differs from NLP classification '{classified}' "
            f"(confidence {conf:.0%})."
        )

    return ScoringResult(
        credibility_score=total,
        step1=s1,
        step2=s2,
        step3=s3,
        auto_status=auto_status,
        classified_category=classified,
        classification_confidence=conf,
        flags=flags,
    )


# ─────────────────────────────────────────────────────────────
# Deduplication check
# ─────────────────────────────────────────────────────────────
from app.ml.imd_stations import haversine_km  # noqa: E402

DEDUP_RADIUS_KM = 15.0
DEDUP_TIME_WINDOW_SECONDS = 3600  # 1 hour


def is_duplicate(
    new_lat: float, new_lon: float, new_category: str, new_time: datetime,
    existing_lat: float, existing_lon: float, existing_category: str, existing_time: datetime,
) -> bool:
    """
    Returns True if two reports are near-duplicates:
      - Same event category
      - Within DEDUP_RADIUS_KM of each other
      - Within DEDUP_TIME_WINDOW_SECONDS of each other
    """
    if new_category.lower() != existing_category.lower():
        return False
    dist = haversine_km(new_lat, new_lon, existing_lat, existing_lon)
    if dist > DEDUP_RADIUS_KM:
        return False
    if new_time.tzinfo is None:
        new_time = new_time.replace(tzinfo=timezone.utc)
    if existing_time.tzinfo is None:
        existing_time = existing_time.replace(tzinfo=timezone.utc)
    time_diff = abs((new_time - existing_time).total_seconds())
    return time_diff <= DEDUP_TIME_WINDOW_SECONDS
