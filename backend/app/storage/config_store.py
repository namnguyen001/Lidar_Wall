import json
import os
import shutil
from pathlib import Path

from app.models.config import LidarWallConfig


class ConfigStore:
    def __init__(self, data_dir: str = "../data", config_file: str = "config.json"):
        self.data_dir = Path(data_dir)
        self.config_path = self.data_dir / config_file
        self.config: LidarWallConfig | None = None

    def load(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            default_cfg = Path("../config/default.config.json")
            if default_cfg.exists():
                shutil.copy(default_cfg, self.config_path)
            else:
                raise FileNotFoundError("Default config not found")
        
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.config = LidarWallConfig(**data)

    def get_config(self) -> LidarWallConfig:
        if self.config is None:
            self.load()
        assert self.config is not None
        return self.config

    def update_config(self, new_config: LidarWallConfig):
        # debounce logic would go here in a real app or handled at API layer
        
        backup_path = self.config_path.with_suffix('.json.bak')
        tmp_path = self.config_path.with_suffix('.tmp')
        
        if self.config_path.exists():
            shutil.copy(self.config_path, backup_path)
            
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(new_config.model_dump_json(indent=2))
            
        os.replace(tmp_path, self.config_path)
        self.config = new_config

    def save(self, new_config: LidarWallConfig | None = None):
        if new_config is not None:
            self.update_config(new_config)
        elif self.config is not None:
            self.update_config(self.config)
