import asyncio
import websockets

API_KEY = "sk_lofsHzUwV_raFiCJftTwuyHPTA2JxfRIzGgycTP02wE"

async def main():
    url = f"ws://127.0.0.1:8000/ws?api_key={API_KEY}"

    async with websockets.connect(url) as websocket:
        print("Connected. Waiting for real-time updates...")

        while True:
            message = await websocket.recv()
            print("Received:")
            print(message)


asyncio.run(main())