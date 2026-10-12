from fastapi import APIRouter, WebSocket

router = APIRouter()

@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    ws_hub = websocket.app.state.ws_hub
    await ws_hub.connect_events(websocket)

@router.websocket("/ws/points")
async def ws_points(websocket: WebSocket):
    ws_hub = websocket.app.state.ws_hub
    await ws_hub.connect_points(websocket)
