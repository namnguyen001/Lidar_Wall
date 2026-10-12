
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

class StartRequest(BaseModel):
    lidarId: str
    targetsUv: list[list[float]] | None = None
    samplesPerPoint: int = 40

@router.post("/start")
async def start_calibration(req: StartRequest, request: Request):
    service = request.app.state.calibration_service
    try:
        await service.start(req.lidarId, req.targetsUv, req.samplesPerPoint)
        return service.state
    except ValueError as e:
        raise HTTPException(status_code=409 if "BUSY" in str(e) else 404, detail=str(e))

@router.get("/state")
async def get_state(request: Request):
    return request.app.state.calibration_service.state

@router.post("/capture")
async def manual_capture(request: Request):
    await request.app.state.calibration_service.manual_capture()
    return request.app.state.calibration_service.state

class RedoRequest(BaseModel):
    pointIndex: int

@router.post("/redo")
async def redo_point(req: RedoRequest, request: Request):
    await request.app.state.calibration_service.redo(req.pointIndex)
    return request.app.state.calibration_service.state

@router.post("/cancel")
async def cancel_calibration(request: Request):
    await request.app.state.calibration_service.cancel()
    return request.app.state.calibration_service.state

@router.post("/commit")
async def commit_calibration(request: Request):
    await request.app.state.calibration_service.commit()
    return request.app.state.calibration_service.state
