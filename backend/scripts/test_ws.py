import asyncio

import websockets


async def test():
    uri = "ws://localhost:8000/ws/chat?token=fake_token"
    try:
        async with websockets.connect(uri, extra_headers={"Origin": "http://localhost:5173"}) as websocket:
            print("Connected!")
            msg = await websocket.recv()
            print("Received:", msg)
    except Exception as e:
        print("Error:", e)


asyncio.run(test())
