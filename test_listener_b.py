import asyncio
import websockets

API_KEY = "sk_kc6SFr_tJrxU2gIWTThfbOyIVVOGQURky8aRzKRJcgY"


async def main():
    url = f"ws://127.0.0.1:8000/ws?api_key={API_KEY}"

    async with websockets.connect(url) as websocket:
        print("Tenant B connected. Waiting for updates...")

        while True:
            message = await websocket.recv()
            print("Tenant B received:")
            print(message)


asyncio.run(main())