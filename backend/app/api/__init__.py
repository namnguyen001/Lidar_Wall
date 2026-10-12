from fastapi import APIRouter
from app.api.endpoints import calibration, config, lidars, zones, output, presets

api_router = APIRouter()
api_router.include_router(config.router, tags=["config"])
api_router.include_router(lidars.router, tags=["lidars"])
api_router.include_router(calibration.router, prefix="/calibration", tags=["calibration"])
api_router.include_router(zones.router, prefix="/zones", tags=["zones"])
api_router.include_router(output.router, prefix="/output", tags=["output"])
api_router.include_router(presets.router, prefix="/presets", tags=["presets"])
