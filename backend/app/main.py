from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.services.lidar_manager import LidarManager
from app.services.ws_hub import WsHub
from app.storage.config_store import ConfigStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup state
    app.state.start_time = time.time()
    from app.services.calibration import CalibrationService
    from app.services.detection import DetectionService
    from app.services.zone_engine import ZoneEngine
    from app.services.fusion import FusionService
    from app.output.manager import OutputManager
    app.state.config_store = ConfigStore()
    app.state.config_store.load()
    app.state.ws_hub = WsHub()
    app.state.lidar_manager = LidarManager(app.state.config_store, app.state.ws_hub)
    app.state.detection = DetectionService(app.state.config_store, app.state.ws_hub, app.state.lidar_manager)
    app.state.calibration_service = CalibrationService(app.state.config_store, app.state.ws_hub)
    app.state.zone_engine = ZoneEngine(app.state.config_store, app.state.ws_hub)
    app.state.fusion_service = FusionService(app.state.config_store, app.state.ws_hub)
    app.state.output_manager = OutputManager(app.state.config_store)
    # Hook services
    app.state.detection.calibration_service = app.state.calibration_service
    app.state.detection.fusion_service = app.state.fusion_service
    app.state.fusion_service.zone_engine = app.state.zone_engine
    app.state.fusion_service.output_manager = app.state.output_manager
    app.state.zone_engine.output_manager = app.state.output_manager
    
    await app.state.lidar_manager.start_all()
    await app.state.detection.start()
    await app.state.fusion_service.start()
    await app.state.output_manager.start()
    
    yield
    
    # Teardown
    await app.state.output_manager.stop()
    await app.state.fusion_service.stop()
    await app.state.detection.stop()
    await app.state.lidar_manager.stop_all()

app = FastAPI(title="Lidar Interactive Wall", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

from app.api.endpoints import ws
app.include_router(ws.router)

import os
import time
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    os.makedirs("data/logs", exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers if any
    for h in logger.handlers[:]:
        logger.removeHandler(h)
        
    handler = RotatingFileHandler("data/logs/app.log", maxBytes=5*1024*1024, backupCount=5, encoding="utf-8")
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

setup_logging()

@app.get("/api/health")
async def health(request: Request):
    # Diagnostics info
    lm = request.app.state.lidar_manager
    det = request.app.state.detection
    
    lidars = {}
    for lidar_id, driver in lm.drivers.items():
        st = driver.get_status()
        lidars[lidar_id] = {
            "state": st.state,
            "fps": st.fps,
            "lastError": st.last_error
        }
        
    return {
        "status": "ok", 
        "version": "1.0.0", 
        "uptimeS": int(time.time() - getattr(request.app.state, 'start_time', time.time())),
        "lidars": lidars,
        "processingP95Ms": det.get_p95_processing_time_ms() if hasattr(det, 'get_p95_processing_time_ms') else 0
    }

@app.get("/api/logs/download")
async def download_logs():
    return FileResponse("data/logs/app.log", filename="app_diagnostics.log")

@app.get("/api/serial-ports")
async def get_serial_ports():
    import serial.tools.list_ports
    return [{"port": p.device, "desc": p.description} for p in serial.tools.list_ports.comports()]

# Serve frontend (SPA routing)
import sys
if getattr(sys, 'frozen', False):
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    frontend_dist = os.path.join(base_dir, "frontend", "dist")
else:
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    fonts_dir = os.path.join(frontend_dist, "fonts")
    if os.path.isdir(fonts_dir):
        app.mount("/fonts", StaticFiles(directory=fonts_dir), name="fonts")

    @app.get("/favicon.svg")
    async def favicon():
        favicon_path = os.path.join(frontend_dist, "favicon.svg")
        if os.path.isfile(favicon_path):
            return FileResponse(favicon_path, media_type="image/svg+xml")
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    @app.api_route("/api", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    @app.api_route("/api/{api_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    async def api_not_found():
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    @app.get("/{catchall:path}")
    async def serve_spa(request: Request):
        if request.url.path.startswith(("/api/", "/ws/", "/assets/", "/fonts/")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path, media_type="text/html")
        return JSONResponse({"detail": "Frontend not built"}, status_code=503)

