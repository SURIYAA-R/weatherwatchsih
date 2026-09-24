"""
Reports API — CRUD + scoring pipeline integration.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.models.report import Report
from app.api.schemas import ReportCreate, ReportOut, AdminReviewAction
from app.ml.scorer import score_report, is_duplicate

router = APIRouter(prefix="/reports", tags=["Reports"])


# ─────────────────────────────────────────────────────────────
# Helper: run ML pipeline and persist to ORM object
# ─────────────────────────────────────────────────────────────
async def _apply_scoring(report: Report, db: AsyncSession) -> None:
    result = score_report(
        description=report.description,
        event_category=report.event_category,
        latitude=report.latitude,
        longitude=report.longitude,
        account_age_months=report.account_age_months or 0,
        is_verified_account=report.is_verified_account or False,
        prior_verified_count=report.prior_verified_count or 0,
        image_url=report.image_url,
        image_exif_valid=report.image_exif_valid,
    )
    report.classified_category = result.classified_category
    report.classification_confidence = result.classification_confidence
    report.credibility_score = result.credibility_score
    report.score_breakdown = result.breakdown()
    report.status = result.auto_status

    bd = result.breakdown()
    geo = bd.get("step3_geo_temporal", {})
    report.nearest_imd_station = geo.get("nearest_station")
    report.imd_distance_km = geo.get("distance_km")
    report.imd_match = geo.get("event_known_at_station")
    report.geo_score_detail = geo.get("detail")


async def _check_dedup(report: Report, db: AsyncSession) -> None:
    """Flag as duplicate if a near-identical recent report exists."""
    stmt = select(Report).where(
        and_(
            Report.event_category == report.event_category,
            Report.status.notin_(["rejected", "merged"]),
            Report.id != report.id,
        )
    )
    rows = (await db.execute(stmt)).scalars().all()
    new_time = report.event_time or report.created_at or datetime.now(timezone.utc)

    for existing in rows:
        ex_time = existing.event_time or existing.created_at or datetime.now(timezone.utc)
        if is_duplicate(
            report.latitude, report.longitude, report.event_category, new_time,
            existing.latitude, existing.longitude, existing.event_category, ex_time,
        ):
            report.is_duplicate = True
            report.duplicate_of_id = existing.id
            if report.status != "flagged":
                report.status = "flagged"
            break


# ─────────────────────────────────────────────────────────────
# POST /reports — Submit a new citizen report
# ─────────────────────────────────────────────────────────────
@router.post("/", response_model=ReportOut, status_code=201)
async def submit_report(payload: ReportCreate, db: AsyncSession = Depends(get_db)):
    if not payload.consent_given:
        raise HTTPException(status_code=422, detail="Consent must be given to submit a report.")

    report = Report(**payload.model_dump())
    report.created_at = datetime.now(timezone.utc)
    report.updated_at = datetime.now(timezone.utc)

    db.add(report)
    await db.flush()  # get ID before scoring

    await _apply_scoring(report, db)
    await _check_dedup(report, db)
    await db.commit()
    await db.refresh(report)
    return report


# ─────────────────────────────────────────────────────────────
# GET /reports — List with filters
# ─────────────────────────────────────────────────────────────
@router.get("/", response_model=list[ReportOut])
async def list_reports(
    event_category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    min_score: Optional[float] = Query(None),
    max_score: Optional[float] = Query(None),
    severity: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    conditions = []
    if event_category:
        conditions.append(Report.event_category == event_category)
    if status:
        conditions.append(Report.status == status)
    if state:
        conditions.append(Report.state.ilike(f"%{state}%"))
    if city:
        conditions.append(Report.city.ilike(f"%{city}%"))
    if date_from:
        conditions.append(Report.created_at >= date_from)
    if date_to:
        conditions.append(Report.created_at <= date_to)
    if min_score is not None:
        conditions.append(Report.credibility_score >= min_score)
    if max_score is not None:
        conditions.append(Report.credibility_score <= max_score)
    if severity:
        conditions.append(Report.severity == severity)

    stmt = (
        select(Report)
        .where(and_(*conditions) if conditions else True)
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return rows


# ─────────────────────────────────────────────────────────────
# GET /reports/{id} — Detail
# ─────────────────────────────────────────────────────────────
@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    report = await db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


# ─────────────────────────────────────────────────────────────
# POST /reports/{id}/review — Admin approve/reject/merge
# ─────────────────────────────────────────────────────────────
@router.post("/{report_id}/review", response_model=ReportOut)
async def review_report(
    report_id: int, action: AdminReviewAction, db: AsyncSession = Depends(get_db)
):
    report = await db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if action.action == "approve":
        report.status = "published"
    elif action.action == "reject":
        report.status = "rejected"
    elif action.action == "merge":
        if not action.merge_target_id:
            raise HTTPException(status_code=422, detail="merge_target_id required for merge action")
        target = await db.get(Report, action.merge_target_id)
        if not target:
            raise HTTPException(status_code=404, detail="Merge target not found")
        report.status = "merged"
        report.merged_into_id = action.merge_target_id
    else:
        raise HTTPException(status_code=422, detail="action must be approve | reject | merge")

    report.admin_note = action.admin_note
    report.reviewed_by = action.reviewed_by
    report.reviewed_at = datetime.now(timezone.utc)
    report.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(report)
    return report


# ─────────────────────────────────────────────────────────────
# GET /reports/admin/queue — Flagged reports queue
# ─────────────────────────────────────────────────────────────
@router.get("/admin/queue", response_model=list[ReportOut])
async def admin_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Report)
        .where(Report.status == "flagged")
        .order_by(Report.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return rows


# ─────────────────────────────────────────────────────────────
# GET /reports/stats/summary — Dashboard stats
# ─────────────────────────────────────────────────────────────
@router.get("/stats/summary")
async def stats_summary(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    total = (await db.execute(select(func.count(Report.id)))).scalar()
    published = (await db.execute(select(func.count(Report.id)).where(Report.status == "published"))).scalar()
    flagged = (await db.execute(select(func.count(Report.id)).where(Report.status == "flagged"))).scalar()
    rejected = (await db.execute(select(func.count(Report.id)).where(Report.status == "rejected"))).scalar()
    pending = (await db.execute(select(func.count(Report.id)).where(Report.status == "pending"))).scalar()
    duplicates = (await db.execute(select(func.count(Report.id)).where(Report.is_duplicate == True))).scalar()
    avg_score = (await db.execute(select(func.avg(Report.credibility_score)))).scalar()

    return {
        "total": total,
        "published": published,
        "flagged": flagged,
        "rejected": rejected,
        "pending": pending,
        "duplicates": duplicates,
        "avg_credibility_score": round(avg_score or 0, 2),
    }
