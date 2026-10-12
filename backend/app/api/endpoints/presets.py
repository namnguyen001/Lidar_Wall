import os
import glob
import time
import json
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

router = APIRouter()
BACKUPS_DIR = "data/backups"

class PresetCreate(BaseModel):
    name: str
    includeCalibration: bool = True

def _ensure_backup_dir():
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    
def _rotate_backups():
    _ensure_backup_dir()
    files = sorted(glob.glob(os.path.join(BACKUPS_DIR, "*.json")), key=os.path.getmtime)
    while len(files) > 10:
        os.remove(files.pop(0))

@router.get("")
async def get_presets():
    _ensure_backup_dir()
    files = sorted(glob.glob(os.path.join(BACKUPS_DIR, "*.json")), key=os.path.getmtime, reverse=True)
    presets = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                data = json.load(file)
            name = os.path.basename(f).replace(".json", "")
            presets.append({
                "id": name,
                "name": name,
                "createdAt": os.path.getmtime(f) * 1000,
                "version": data.get("version", 1)
            })
        except Exception:
            pass
    return presets

@router.post("")
async def create_preset(request: Request, body: PresetCreate):
    _ensure_backup_dir()
    cfg = request.app.state.config_store.get_config()
    data = cfg.model_dump()
    
    if not body.includeCalibration:
        for lidar in data["lidars"]:
            lidar["calibration"] = {
                "homography": None,
                "rmsPx": None,
                "createdAt": None,
                "targetsUv": [],
                "capturedMm": []
            }
            
    timestamp = int(time.time())
    safe_name = "".join(c for c in body.name if c.isalnum() or c in (" ", "_", "-")).strip()
    if not safe_name:
        safe_name = f"backup_{timestamp}"
    filename = f"{safe_name}_{timestamp}.json"
    
    with open(os.path.join(BACKUPS_DIR, filename), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    _rotate_backups()
    return {"id": filename.replace(".json", ""), "name": filename.replace(".json", "")}

@router.post("/{preset_id}/apply")
async def apply_preset(request: Request, preset_id: str):
    file_path = os.path.join(BACKUPS_DIR, f"{preset_id}.json")
    if not os.path.exists(file_path):
        raise HTTPException(404, "Preset not found")
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise HTTPException(500, f"Error reading preset: {e}")
        
    from app.models.config import AppConfig
    try:
        new_config = AppConfig(**data)
        request.app.state.config_store.save(new_config)
    except Exception as e:
        raise HTTPException(400, f"Preset config invalid: {e}")
        
    return {"status": "ok"}

@router.delete("/{preset_id}")
async def delete_preset(preset_id: str):
    file_path = os.path.join(BACKUPS_DIR, f"{preset_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"status": "ok"}
    raise HTTPException(404, "Preset not found")
