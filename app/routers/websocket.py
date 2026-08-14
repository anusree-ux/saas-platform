import asyncio
import hashlib

from fastapi import APIRouter, WebSocket
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import APIKey, Tenant
from app.pubsub import subscribe_to_tenant

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

    print(
        f"WebSocket connected for tenant {tenant_id}"
    )

    try:
        while True:

            # Check Redis for new tenant events.
            message = pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=0,
            )

            if message:
                print(
                    "Redis message received:",
                    message,
                )

                await websocket.send_text(
                    message["data"]
                )

            # Give the event loop time to handle
            # WebSocket connections and other tasks.
            await asyncio.sleep(0.1)

    except Exception as error:
        print(
            f"WebSocket error for tenant "
            f"{tenant_id}: {error}"
        )

    finally:
        pubsub.close()

        print(
            f"WebSocket connection closed "
            f"for tenant {tenant_id}"
        )