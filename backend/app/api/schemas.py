"""
Pydantic schemas for request/response validation.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, EmailStr, field_validator


# ── Submission ──────────────────────────────────────────────
class ReportCreate(BaseModel):
    submitter_name: str = Field(..., min_length=2, max_length=120)
    submitter_email: Optional[str] = None
    source_type: str = Field(default="citizen")
    account_age_months: int = Field(default=0, ge=0)
    is_verified_account: bool = Field(default=False)
    prior_verified_count: int = Field(default=0, ge=0)

    event_category: str = Field(..., description="flood|cyclone|heatwave|rain|fog|hailstorm|drought|thunderstorm")
    description: str = Field(..., min_length=10, max_length=2000)
    severity: str = Field(default="moderate")

    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    city: Optional[str] = None
    state: Optional[str] = None

    image_url: Optional[str] = None
    image_exif_valid: Optional[bool] = None

    event_time: Optional[datetime] = None
    consent_given: bool = Field(..., description="Submitter must give explicit consent")

    @field_validator("event_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        allowed = {"flood", "cyclone", "heatwave", "rain", "fog", "hailstorm", "drought", "thunderstorm", "unknown"}
        if v.lower() not in allowed:
            raise ValueError(f"event_category must be one of {allowed}")
        return v.lower()

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"low", "moderate", "high", "extreme"}
        if v.lower() not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v.lower()


# ── Score breakdown (nested) ─────────────────────────────────
class ScoreStep(BaseModel):
    step: int
    name: str
    max_pts: int
    total: float
    detail: str


class ScoreBreakdown(BaseModel):
    total_score: float
    auto_status: str
    threshold_flag: float
    threshold_publish: float
    step1_source_credibility: dict[str, Any]
    step2_content_consistency: dict[str, Any]
    step3_geo_temporal: dict[str, Any]
    flags: list[str]
    classified_category: str
    classification_confidence: float


# ── Report response ──────────────────────────────────────────
class ReportOut(BaseModel):
    id: int
    submitter_name: str
    event_category: str
    classified_category: Optional[str]
    classification_confidence: Optional[float]
    description: str
    severity: str
    latitude: float
    longitude: float
    city: Optional[str]
    state: Optional[str]
    image_url: Optional[str]
    status: str
    credibility_score: Optional[float]
    score_breakdown: Optional[dict[str, Any]]
    nearest_imd_station: Optional[str]
    imd_distance_km: Optional[float]
    imd_match: Optional[bool]
    geo_score_detail: Optional[str]
    is_duplicate: bool
    duplicate_of_id: Optional[int]
    merged_into_id: Optional[int]
    admin_note: Optional[str]
    event_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Admin review ─────────────────────────────────────────────
class AdminReviewAction(BaseModel):
    action: str = Field(..., description="approve | reject | merge")
    admin_note: Optional[str] = None
    reviewed_by: str = Field(..., min_length=2)
    merge_target_id: Optional[int] = None   # for merge action


# ── Filters ──────────────────────────────────────────────────
class ReportFilter(BaseModel):
    event_category: Optional[str] = None
    status: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    severity: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=200)


# ── Social feed (simulated ingest) ───────────────────────────
class SocialPostCreate(BaseModel):
    platform: str = "twitter"
    handle: str
    text: str
    hashtags: list[str] = []
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    account_age_months: int = 0
    is_verified: bool = False
