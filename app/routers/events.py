from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.dependencies import get_current_tenant, get_db
from app.models import Event, Tenant
from app.schemas import EventCreate, EventResponse


router = APIRouter(prefix="/events", tags=["Events"])


@router.post("/", response_model=EventResponse)
def create_event(
    event_data: EventCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    event = Event(
        tenant_id=tenant.id,
        event_name=event_data.event_name,
        properties=event_data.properties,
        occurred_at=event_data.occurred_at,
        received_at=datetime.now(timezone.utc),
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event

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