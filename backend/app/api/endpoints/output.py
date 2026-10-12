import asyncio
import math
import time
from fastapi import APIRouter, Request

from app.models.config import OutputConfig

router = APIRouter()

@router.get("")
async def get_output(request: Request):
    return request.app.state.config_store.get_config().output

@router.put("")
async def update_output(request: Request, output: OutputConfig):
    cfg = request.app.state.config_store.get_config()
    cfg.output = output
    request.app.state.config_store.save(cfg)
    return cfg.output

@router.post("/test")
async def test_output(request: Request):
    async def run_test():
        manager = getattr(request.app.state, 'output_manager', None)
        if not manager:
            return
            
        start_t = time.time()
        blob_id = 9999
        radius = 0.2
        cx, cy = 0.5, 0.5
        speed = 2 * math.pi / 2.0
        
        while time.time() - start_t < 3.0:
            t = time.time() - start_t
            u = cx + radius * math.cos(speed * t)
            v = cy + radius * math.sin(speed * t)
            vu = -radius * speed * math.sin(speed * t)
            vv = radius * speed * math.cos(speed * t)
            
            fake_blob = {
                "id": blob_id,
                "u": u,
                "v": v,
                "sizeMm": 150.0,
                "vu": vu,
                "vv": vv,
                "state": "active"
            }
            manager.process_blobs([fake_blob], time.time())
            await asyncio.sleep(1.0 / 30.0)
            
        fake_blob["state"] = "lost"
        manager.process_blobs([fake_blob], time.time())
        
    asyncio.create_task(run_test())
    return {"status": "ok"}
