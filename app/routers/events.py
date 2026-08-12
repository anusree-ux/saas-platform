from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from app.rate_limiter import check_and_consume
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_current_tenant, get_db
from app.models import Event, Tenant
from app.schemas import EventCreate, EventResponse
from app.tasks.events import process_event


router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", status_code=202)
def create_event(
    event_data: EventCreate,
    tenant: Tenant = Depends(get_current_tenant),
):
    if not check_and_consume(str(tenant.id)):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Try again later.",
        )

    event_id = uuid.uuid4()

    process_event.delay(
        event_id=str(event_id),
        tenant_id=str(tenant.id),
        event_name=event_data.event_name,
        properties=event_data.properties,
        occurred_at=event_data.occurred_at.isoformat(),
    )

    return {
        "id": event_id,
        "status": "queued",
    }

@router.get("/", response_model=list[EventResponse])
def get_events(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    events = (
        db.query(Event)
        .filter(Event.tenant_id == tenant.id)
        .order_by(Event.occurred_at.desc())
        .all()
    )

    return events

@router.get("/count")
def count_events(
    since: str = Query(default="1h"),
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

    count = (
        db.query(func.count(Event.id))
        .filter(
            Event.tenant_id == tenant.id,
            Event.occurred_at >= since_time,
        )
        .scalar()
    )

    return {
        "count": count,
        "since": since,
    }