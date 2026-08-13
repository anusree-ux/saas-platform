import asyncio
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import APIKey, Tenant, Event
from app.pubsub import (
    subscribe_to_tenant,
    publish_tenant_update,
)
from app.schemas import EventCreate
from app.services.aggregation import update_event_aggregate

router = APIRouter()


def get_tenant_from_api_key(api_key: str) -> Tenant | None:
    db: Session = SessionLocal()

    try:
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        api_key_record = (
            db.query(APIKey)
            .filter(
                APIKey.key_hash == key_hash,
                APIKey.revoked_at.is_(None),
            )
            .first()
        )

        if not api_key_record:
            return None

        tenant = (
            db.query(Tenant)
            .filter(
                Tenant.id == api_key_record.tenant_id,
                Tenant.status == "active",
            )
            .first()
        )

        return tenant

    finally:
        db.close()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    api_key = websocket.query_params.get("api_key")

    if not api_key:
        await websocket.close(code=1008)
        return

    tenant = get_tenant_from_api_key(api_key)

    if not tenant:
        await websocket.close(code=1008)
        return

    tenant_id = str(tenant.id)

    await websocket.accept()

    pubsub = subscribe_to_tenant(tenant_id)

    print(f"WebSocket connected for tenant {tenant_id}")

    try:
        while True:

            # Receive event from client
            try:
                data = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=0.1,
                )

                event_data = EventCreate.model_validate(data)

                db: Session = SessionLocal()

                try:
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

                    aggregate = update_event_aggregate(
                        db=db,
                        tenant_id=tenant.id,
                        event_name=event.event_name,
                        occurred_at=event.occurred_at,
                    )
                    publish_tenant_update(
                        tenant_id=tenant_id,
                        event_name=aggregate.event_name,
                        count=aggregate.count,
                    )

                    print(
                        f"Event stored: {event.id} "
                        f"for tenant {tenant_id}"
                    )

                finally:
                    db.close()

                # Acknowledge event
                await websocket.send_json(
                    {
                        "status": "accepted",
                        "event_id": str(event.id),
                    }
                )

            except asyncio.TimeoutError:
                pass

            # Receive Redis messages
            message = pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=0,
            )

            if message:
                print("Redis message received:", message)

                await websocket.send_text(
                    message["data"]
                )

    except WebSocketDisconnect:
        print(
            f"WebSocket disconnected "
            f"for tenant {tenant_id}"
        )

    finally:
        pubsub.close()