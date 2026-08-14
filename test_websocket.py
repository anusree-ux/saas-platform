import asyncio
import json
import os

import websockets

API_KEY = os.environ["TEST_API_KEY"]


async def main():
    url = f"ws://127.0.0.1:8000/ws?api_key={API_KEY}"

    async with websockets.connect(url) as websocket:
        print("Connected!")

        event = {
            "event_name": "user.login",
            "idempotency_key": "login-test-001",
            "properties": {
                "user_id": "123",
                "source": "web",
            },
            "occurred_at": "2026-08-13T19:45:00Z",
        }

        await websocket.send(json.dumps(event))

        response = await websocket.recv()
        print("Server response:")
        print(response)

        update = await websocket.recv()
        print("Real-time update:")
        print(update)


asyncio.run(main())