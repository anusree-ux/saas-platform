import asyncio
import websockets

TENANT_ID = "3e3a15b3-0682-4a22-a53a-c734add8dd7d"


async def main():
    uri = f"ws://127.0.0.1:8000/ws/{TENANT_ID}"

    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as websocket:
        print("WebSocket connected. Waiting for events...")

        while True:
            message = await websocket.recv()
            print("Received:", message)


asyncio.run(main())