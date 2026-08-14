from datetime import datetime, timezone
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
    idempotency_key: str,
    properties: dict,
    occurred_at: str,
):
    db = SessionLocal()

    try:
        tenant_uuid = uuid.UUID(tenant_id)
        event_uuid = uuid.UUID(event_id)
        occurred_at_dt = datetime.fromisoformat(occurred_at)

        # Check idempotency for this tenant.
        existing_event = (
            db.query(Event)
            .filter(
                Event.tenant_id == tenant_uuid,
                Event.idempotency_key == idempotency_key,
            )
            .first()
        )

        if existing_event:
            print(
                f"Duplicate event received. "
                f"Idempotency key: {idempotency_key}"
            )
            return

        # Calculate hourly bucket.
        time_bucket = occurred_at_dt.replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        # Store raw event.
        event = Event(
            id=event_uuid,
            tenant_id=tenant_uuid,
            event_name=event_name,
            idempotency_key=idempotency_key,
            properties=properties,
            occurred_at=occurred_at_dt,
            received_at=datetime.now(timezone.utc),
        )

        db.add(event)

        # Find existing aggregate.
        aggregate = (
            db.query(EventAggregate)
            .filter(
                EventAggregate.tenant_id == tenant_uuid,
                EventAggregate.event_name == event_name,
                EventAggregate.time_bucket == time_bucket,
            )
            .first()
        )

        # Increment or create aggregate.
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

        # Refresh objects so generated/default values are available.
        db.refresh(event)
        db.refresh(aggregate)

        count = aggregate.count

        # Publish complete event to Redis.
        publish_tenant_update(
            tenant_id=tenant_id,
            event_id=str(event.id),
            event_name=event.event_name,
            properties=event.properties,
            occurred_at=event.occurred_at.isoformat(),
            received_at=event.received_at.isoformat(),
            count=count,
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