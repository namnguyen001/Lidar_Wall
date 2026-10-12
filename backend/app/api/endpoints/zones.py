from fastapi import APIRouter, Request, HTTPException
from typing import List

from app.models.config import ZoneConfig

router = APIRouter()

@router.get("")
async def get_zones(request: Request):
    return request.app.state.config_store.get_config().zones

@router.put("")
async def import_zones(zones: List[ZoneConfig], request: Request):
    config_store = request.app.state.config_store
    config = config_store.get_config()
    config.zones = zones
    config_store.update_config(config)
    return config.zones

@router.post("")
async def create_zone(zone: ZoneConfig, request: Request):
    config_store = request.app.state.config_store
    config = config_store.get_config()
    # Check duplicate ID
    if any(z.id == zone.id for z in config.zones):
        raise HTTPException(status_code=400, detail="Zone ID already exists")
    config.zones.append(zone)
    config_store.update_config(config)
    return zone

@router.put("/{zone_id}")
async def update_zone(zone_id: str, zone: ZoneConfig, request: Request):
    config_store = request.app.state.config_store
    config = config_store.get_config()
    for i, z in enumerate(config.zones):
        if z.id == zone_id:
            config.zones[i] = zone
            config_store.update_config(config)
            return zone
    raise HTTPException(status_code=404, detail="Zone not found")

@router.delete("/{zone_id}")
async def delete_zone(zone_id: str, request: Request):
    config_store = request.app.state.config_store
    config = config_store.get_config()
    for i, z in enumerate(config.zones):
        if z.id == zone_id:
            del config.zones[i]
            config_store.update_config(config)
            return {"status": "ok"}
    raise HTTPException(status_code=404, detail="Zone not found")

@router.post("/{zone_id}/duplicate")
async def duplicate_zone(zone_id: str, request: Request):
    config_store = request.app.state.config_store
    config = config_store.get_config()
    for z in config.zones:
        if z.id == zone_id:
            new_zone = z.model_copy(deep=True)
            import uuid
            new_zone.id = f"{z.id}_copy_{uuid.uuid4().hex[:4]}"
            new_zone.name = f"{z.name} (Copy)"
            config.zones.append(new_zone)
            config_store.save(config)
            return new_zone
    raise HTTPException(status_code=404, detail="Zone not found")
