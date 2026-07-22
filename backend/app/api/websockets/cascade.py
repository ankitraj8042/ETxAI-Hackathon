import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.agents.cascade_bus import cascade_bus

router = APIRouter()


@router.websocket("/ws/cascade")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that registers with the global cascade bus with heartbeat ping/pong."""
    await websocket.accept()
    cascade_bus.register_websocket(websocket)

    heartbeat_task = None
    try:
        async def heartbeat():
            while True:
                await asyncio.sleep(25)
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

        heartbeat_task = asyncio.create_task(heartbeat())

        while True:
            data = await websocket.receive_text()
            if data == "pong" or data == '{"type":"pong"}':
                continue
            await websocket.send_json({"type": "ack", "message": f"received: {data}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")
    finally:
        if heartbeat_task:
            heartbeat_task.cancel()
        cascade_bus.unregister_websocket(websocket)

