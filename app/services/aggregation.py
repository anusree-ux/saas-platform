from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import EventAggregate


def get_time_bucket(dt: datetime) -> datetime:
    """
    Convert an event timestamp into a one-minute bucket.
    """

    return dt.replace(
        second=0,
        microsecond=0,
    )


def update_event_aggregate(
    db: Session,
    tenant_id,
    event_name: str,
    occurred_at: datetime,
):
    """
    Increment the aggregate count for a tenant,
    event name, and one-minute time bucket.
    """

    time_bucket = get_time_bucket(occurred_at)

    aggregate = (
        db.query(EventAggregate)
        .filter(
            EventAggregate.tenant_id == tenant_id,
            EventAggregate.event_name == event_name,
            EventAggregate.time_bucket == time_bucket,
        )
        .first()
    )

    if aggregate:
        aggregate.count += 1

    else:
        aggregate = EventAggregate(
            tenant_id=tenant_id,
            event_name=event_name,
            time_bucket=time_bucket,
            count=1,
        )

        db.add(aggregate)

    db.commit()
    db.refresh(aggregate)

    return aggregate