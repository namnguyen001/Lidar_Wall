from fastapi import APIRouter, Request

from app.models.config import LidarWallConfig

router = APIRouter(prefix="/config")

@router.get("", response_model=LidarWallConfig)
async def get_config(request: Request):
    return request.app.state.config_store.get_config()

@router.put("", response_model=LidarWallConfig)
async def update_config(config: LidarWallConfig, request: Request):
    request.app.state.config_store.update_config(config)
    return config
