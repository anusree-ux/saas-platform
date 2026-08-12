import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.pubsub import subscribe_to_tenant

router = APIRouter()


@router.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    await websocket.accept()

    pubsub = subscribe_to_tenant(tenant_id)

    try:
        while True:
            message = pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1,
            )

            if message:
                print("Redis message received:", message)
                await websocket.send_text(message["data"])

            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pubsub.close()