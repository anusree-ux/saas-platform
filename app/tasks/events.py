from datetime import datetime
import uuid

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Event, EventAggregate
from app.pubsub import publish_tenant_update


@celery_app.task(
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
)
def process_event(
    event_id: str,
    tenant_id: str,
    event_name: str,
    properties: dict,
    occurred_at: str,
):
    db = SessionLocal()

    try:
        tenant_uuid = uuid.UUID(tenant_id)
        event_uuid = uuid.UUID(event_id)
        occurred_at_dt = datetime.fromisoformat(occurred_at)

        # Check whether this event has already been processed.
        existing_event = (
            db.query(Event)
            .filter(Event.id == event_uuid)
            .first()
        )

        if existing_event:
            print(
                f"Event {event_id} already exists. "
                "Skipping duplicate processing."
            )
            return

        # Calculate the hourly bucket.
        time_bucket = occurred_at_dt.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        # Store the raw event.
        event = Event(
            id=event_uuid,
            tenant_id=tenant_uuid,
            event_name=event_name,
            properties=properties,
            occurred_at=occurred_at_dt,
        )

        db.add(event)

        # Find the existing hourly aggregate.
        aggregate = (
            db.query(EventAggregate)
            .filter(
                EventAggregate.tenant_id == tenant_uuid,
                EventAggregate.event_name == event_name,
                EventAggregate.time_bucket == time_bucket,
            )
            .first()
        )

        # Increment existing aggregate or create a new one.
        if aggregate:
            aggregate.count += 1
        else:
            aggregate = EventAggregate(
                tenant_id=tenant_uuid,
                event_name=event_name,
                time_bucket=time_bucket,
                count=1,
            )
            db.add(aggregate)

        # Commit event + aggregate together.
        db.commit()

        # Get the updated aggregate count.
        count = aggregate.count

        # Notify connected WebSocket clients.
        publish_tenant_update(
            tenant_id,
            event_name,
            count,
        )

        print(
            f"Event {event_id} stored and aggregate updated "
            f"for tenant {tenant_id}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()