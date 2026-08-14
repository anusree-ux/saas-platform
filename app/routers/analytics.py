from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_current_tenant, get_db
from app.models import EventAggregate, Tenant


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("/events")
def get_event_analytics(
    since: str = Query(default="24h"),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    if since == "1h":
        delta = timedelta(hours=1)
    elif since == "24h":
        delta = timedelta(hours=24)
    elif since == "7d":
        delta = timedelta(days=7)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid since value. Use 1h, 24h, or 7d.",
        )

    since_time = datetime.now(timezone.utc) - delta

    results = (
        db.query(
            EventAggregate.event_name,
            func.sum(EventAggregate.count).label("count"),
        )
        .filter(
            EventAggregate.tenant_id == tenant.id,
            EventAggregate.time_bucket >= since_time,
        )
        .group_by(EventAggregate.event_name)
        .order_by(func.sum(EventAggregate.count).desc())
        .all()
    )

    total_events = sum(row.count for row in results)

    return {
        "since": since,
        "total_events": total_events,
        "events": [
            {
                "event_name": row.event_name,
                "count": row.count,
            }
            for row in results
        ],
    }

@router.get("/events/timeseries")
def get_event_timeseries(
    event_name: str = Query(...),
    since: str = Query(default="24h"),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    if since == "1h":
        delta = timedelta(hours=1)
    elif since == "24h":
        delta = timedelta(hours=24)
    elif since == "7d":
        delta = timedelta(days=7)
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid since value. Use 1h, 24h, or 7d.",
        )

    since_time = datetime.now(timezone.utc) - delta

    results = (
        db.query(
            EventAggregate.time_bucket,
            EventAggregate.count,
        )
        .filter(
            EventAggregate.tenant_id == tenant.id,
            EventAggregate.event_name == event_name,
            EventAggregate.time_bucket >= since_time,
        )
        .order_by(EventAggregate.time_bucket.asc())
        .all()
    )

    return {
        "event_name": event_name,
        "since": since,
        "data": [
            {
                "time": row.time_bucket,
                "count": row.count,
            }
            for row in results
        ],
    }