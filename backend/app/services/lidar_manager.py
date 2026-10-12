import asyncio
import os

from app.drivers.base import LidarDriver
from app.drivers.simulator import SimulatorDriver
from app.models.config import LidarConfig
from app.services.ws_hub import WsHub
from app.storage.config_store import ConfigStore


class LidarManager:
    def __init__(self, config_store: ConfigStore, ws_hub: WsHub):
        self.config_store = config_store
        self.ws_hub = ws_hub
        self.drivers: dict[str, LidarDriver] = {}
        self.force_sim = os.environ.get("LIDAR_FORCE_SIM") == "1"
        self._loop = None

    async def start_all(self):
        self._loop = asyncio.get_running_loop()
        config = self.config_store.get_config()
        for lidar_conf in config.lidars:
            if lidar_conf.enabled:
                await self.start_lidar(lidar_conf.id)
                
        # Start a loop to send lidar statuses
        self._status_task = asyncio.create_task(self._broadcast_status())

    async def stop_all(self):
        if hasattr(self, '_status_task'):
            self._status_task.cancel()
            
        for lidar_id in list(self.drivers.keys()):
            await self.stop_lidar(lidar_id)

    async def start_lidar(self, lidar_id: str) -> bool:
        config = self.config_store.get_config()
        lidar_conf = next((l for l in config.lidars if l.id == lidar_id), None)
        if not lidar_conf:
            return False

        if lidar_id in self.drivers:
            self.drivers[lidar_id].stop()
            
        driver = self._create_driver(lidar_conf)
        self.drivers[lidar_id] = driver
        driver.start()
        return True

    async def stop_lidar(self, lidar_id: str) -> bool:
        if lidar_id in self.drivers:
            self.drivers[lidar_id].stop()
            del self.drivers[lidar_id]
            return True
        return False

    def get_status(self, lidar_id: str) -> dict:
        if lidar_id in self.drivers:
            st = self.drivers[lidar_id].get_status()
            return {"state": st.state, "fps": st.fps, "scanCount": st.scan_count, "lastError": st.last_error}
        return {"state": "disconnected", "fps": 0, "scanCount": 0}

    def _create_driver(self, conf: LidarConfig) -> LidarDriver:
        if self.force_sim or conf.connection.kind == "simulator":
            hands = 1
            if hasattr(conf.connection, 'hands'):
                hands = conf.connection.hands
            return SimulatorDriver(hands=hands)
            
        from app.drivers.ydlidar_sdk import YdlidarSdkDriver
        if conf.connection.kind in ("serial", "tcp"):
            return YdlidarSdkDriver(conf.id, conf.connection) # type: ignore
            
        # Fallback
        return SimulatorDriver()

    async def _broadcast_status(self):
        while True:
            await asyncio.sleep(1.0)
            config = self.config_store.get_config()
            for lidar_conf in config.lidars:
                lidar_id = lidar_conf.id
                st = self.get_status(lidar_id) # This safely handles disconnected lidars
                msg = {
                    "v": 1,
                    "type": "lidarStatus",
                    "ts": int(asyncio.get_event_loop().time() * 1000),
                    "data": {
                        "id": lidar_id,
                        "state": st["state"],
                        "fps": st["fps"],
                        "scanCount": st["scanCount"],
                        "lastError": st.get("lastError")
                    }
                }
                await self.ws_hub.broadcast_events(msg)
