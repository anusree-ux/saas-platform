from datetime import datetime
import uuid

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Event


@celery_app.task
def process_event(
    event_id: str,
    tenant_id: str,
    event_name: str,
    properties: dict,
    occurred_at: str,
):
    db = SessionLocal()

    try:
        event = Event(
            id=uuid.UUID(event_id),
            tenant_id=uuid.UUID(tenant_id),
            event_name=event_name,
            properties=properties,
            occurred_at=datetime.fromisoformat(occurred_at),
        )

        db.add(event)
        db.commit()

        print(f"Event {event_id} stored for tenant {tenant_id}")

    finally:
        db.close()