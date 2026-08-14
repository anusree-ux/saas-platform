import asyncio
import hashlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
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


async def _watch_for_disconnect(websocket: WebSocket):
    """
    The Redis-poll loop only ever sends to the client, so it never
    naturally discovers that the client disconnected. This coroutine
    runs alongside it, blocked on receive(), purely to detect a
    client-initiated close (browser tab closed/refreshed, etc.).
    """
    while True:
        # We don't expect the client to send anything, but awaiting
        # receive() is how Starlette surfaces WebSocketDisconnect.
        await websocket.receive_text()


async def _forward_redis_messages(websocket: WebSocket, pubsub, tenant_id: str):
    while True:
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

    disconnect_task = asyncio.ensure_future(
        _watch_for_disconnect(websocket)
    )
    forward_task = asyncio.ensure_future(
        _forward_redis_messages(websocket, pubsub, tenant_id)
    )

    try:
        # Run both concurrently; stop as soon as either finishes.
        # In practice that's _watch_for_disconnect raising
        # WebSocketDisconnect once the client closes the connection.
        done, pending = await asyncio.wait(
            {disconnect_task, forward_task},
            return_when=asyncio.FIRST_EXCEPTION,
        )

        for task in done:
            task.result()

    except WebSocketDisconnect:
        print(
            f"WebSocket disconnected for tenant {tenant_id}"
        )

    except Exception as error:
        print(
            f"WebSocket error for tenant "
            f"{tenant_id}: {error}"
        )

    finally:
        disconnect_task.cancel()
        forward_task.cancel()

        pubsub.close()

        print(
            f"WebSocket connection closed "
            f"for tenant {tenant_id}"
        )