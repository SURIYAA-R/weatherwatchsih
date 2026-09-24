"""
SQLAlchemy ORM models for weather reports.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, JSON
from app.db.database import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)

    # Submitter identity
    submitter_name = Column(String(120), nullable=False)
    submitter_email = Column(String(200), nullable=True)
    source_type = Column(String(40), default="citizen")  # citizen | social_media | official
    account_age_months = Column(Integer, default=0)
    is_verified_account = Column(Boolean, default=False)
    prior_verified_count = Column(Integer, default=0)

    # Event details
    event_category = Column(String(80), nullable=False)  # flood|cyclone|heatwave|rain|fog|hailstorm|drought|thunderstorm
    description = Column(Text, nullable=False)
    severity = Column(String(20), default="moderate")  # low|moderate|high|extreme

    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)

    # Media
    image_url = Column(String(500), nullable=True)
    image_exif_valid = Column(Boolean, nullable=True)

    # Status & review
    status = Column(String(20), default="pending")   # pending | published | flagged | rejected | merged
    merged_into_id = Column(Integer, nullable=True)
    admin_note = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # ML outputs
    classified_category = Column(String(80), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    credibility_score = Column(Float, nullable=True)       # 0–100
    score_breakdown = Column(JSON, nullable=True)           # step1, step2, step3 details
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, nullable=True)

    # Geo-verification
    nearest_imd_station = Column(String(200), nullable=True)
    imd_distance_km = Column(Float, nullable=True)
    imd_match = Column(Boolean, nullable=True)
    geo_score_detail = Column(Text, nullable=True)

    # Timestamps
    event_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Consent
    consent_given = Column(Boolean, default=False)
