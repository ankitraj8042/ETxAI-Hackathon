"""
DCBrain WebSockets — Cascade Event Stream
Enables real-time push notifications of agent cascade activities to the frontend client.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.agents.cascade_bus import cascade_bus

router = APIRouter()


@router.websocket("/ws/cascade")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that registers with the global cascade bus."""
    await websocket.accept()
    # Register connection with cascade bus
    cascade_bus.register_websocket(websocket)
    
    try:
        while True:
            # Keep connection alive by listening for messages (pings/echoes)
            data = await websocket.receive_text()
            # Echo back for verification if needed
            await websocket.send_text(f"echo: {data}")
    except WebSocketDisconnect:
        # Client disconnected
        cascade_bus.unregister_websocket(websocket)
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")
        cascade_bus.unregister_websocket(websocket)
