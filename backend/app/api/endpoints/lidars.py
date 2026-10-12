
from fastapi import APIRouter, HTTPException, Request

router = APIRouter(prefix="/lidars")

@router.get("")
async def get_lidars(request: Request):
    manager = request.app.state.lidar_manager
    config = request.app.state.config_store.get_config()
    res = []
    for lidar_conf in config.lidars:
        status = manager.get_status(lidar_conf.id)
        res.append({"config": lidar_conf.model_dump(), "status": status})
    return res

@router.post("/{lidar_id}/connect")
async def connect_lidar(lidar_id: str, request: Request):
    manager = request.app.state.lidar_manager
    if not await manager.start_lidar(lidar_id):
        raise HTTPException(status_code=404, detail="Lidar not found")
    return {"status": manager.get_status(lidar_id)}

@router.post("/{lidar_id}/disconnect")
async def disconnect_lidar(lidar_id: str, request: Request):
    manager = request.app.state.lidar_manager
    if not await manager.stop_lidar(lidar_id):
        raise HTTPException(status_code=404, detail="Lidar not found")
    return {"status": manager.get_status(lidar_id)}

@router.post("/{lidar_id}/background/learn")
async def learn_background(lidar_id: str, request: Request):
    detection_service = request.app.state.detection
    try:
        detection_service.start_learning_bg(lidar_id)
        return {"status": "learning"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Lidar not found in detection service")

from pydantic import BaseModel


class ScanAreaUpdate(BaseModel):
    quadMm: list[tuple[float, float]]

@router.put("/{lidar_id}/scan-area")
async def update_scan_area(lidar_id: str, area: ScanAreaUpdate, request: Request):
    config_store = request.app.state.config_store
    config = config_store.get_config()
    lidar_conf = next((l for l in config.lidars if l.id == lidar_id), None)
    if not lidar_conf:
        raise HTTPException(status_code=404, detail="Lidar not found")
        
    from app.core.scan_area import is_convex_quad
    if not is_convex_quad(area.quadMm):
        raise HTTPException(status_code=422, detail="VALIDATION_ERROR: Quad is not strictly convex")
        
    lidar_conf.scanArea.quadMm = area.quadMm
    config_store.save(config)
    return lidar_conf.scanArea

@router.delete("/{lidar_id}/calibration")
async def delete_calibration(lidar_id: str, request: Request):
    config_store = request.app.state.config_store
    config = config_store.get_config()
    lidar_conf = next((l for l in config.lidars if l.id == lidar_id), None)
    if not lidar_conf:
        raise HTTPException(status_code=404, detail="Lidar not found")
        
    lidar_conf.calibration = None # Or empty object if it's not optional
    # Actually, lidar_conf.calibration might not be Optional. Let's see config schema.
    # In config_store.py or models/config.py, Calibration is likely a sub-model.
    # I can just clear its fields.
    from app.models.config import CalibrationConfig
    lidar_conf.calibration = CalibrationConfig()
    config_store.save(config)
    return {"status": "ok"}

@router.get("/probe")
async def probe_lidar(kind: str = "serial", port: str = "", host: str = "", tcp_port: int = 8090):
    return {"status": "ok", "message": "Probe endpoint"}
