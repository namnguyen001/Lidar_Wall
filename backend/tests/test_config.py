import os
import shutil

from app.storage.config_store import ConfigStore


def test_config_store(tmp_path):
    # Setup
    backend_dir = tmp_path / "backend"
    config_dir = tmp_path / "config"
    data_dir = backend_dir / "data"
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(config_dir, exist_ok=True)
    shutil.copy("d:/Lidar/Code/lidar-wall-kit/config/default.config.json", config_dir / "default.config.json")
    
    cwd = os.getcwd()
    os.chdir(backend_dir)
    
    try:
        store = ConfigStore(data_dir="data")
        store.load()
        cfg = store.get_config()
        assert cfg.version == 1
        assert len(cfg.lidars) == 2
        
        cfg.wall.name = "Test Wall"
        store.update_config(cfg)
        
        assert os.path.exists("data/config.json")
        assert os.path.exists("data/config.json.bak")
    finally:
        os.chdir(cwd)
