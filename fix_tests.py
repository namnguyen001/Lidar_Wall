import os

# fix config_store.py
p = 'backend/app/storage/config_store.py'
with open(p, 'r') as f: c = f.read()
c = c.replace('return self.config', 'assert self.config is not None\n        return self.config')
with open(p, 'w') as f: f.write(c)

# fix simulator.py
p = 'backend/app/drivers/simulator.py'
with open(p, 'r') as f: c = f.read()
c = c.replace('self._thread = None', 'self._thread: threading.Thread | None = None')
c = c.replace('self._latest_frame = None', 'self._latest_frame: ScanFrame | None = None')
with open(p, 'w') as f: f.write(c)

# fix lidar_manager.py
p = 'backend/app/services/lidar_manager.py'
with open(p, 'r') as f: c = f.read()
target = """        if self.force_sim or conf.connection.kind == "simulator":
            hands = 1
            if getattr(conf.connection, 'hands', None) is not None:
                hands = conf.connection.hands
            return SimulatorDriver(hands=hands)"""
replacement = """        if self.force_sim or conf.connection.kind == "simulator":
            hands = 1
            if hasattr(conf.connection, 'hands'):
                hands = getattr(conf.connection, 'hands')
            return SimulatorDriver(hands=hands)"""
c = c.replace(target, replacement)
with open(p, 'w') as f: f.write(c)

# fix package.json
p = 'frontend/package.json'
with open(p, 'r') as f: c = f.read()
target = '"build": "tsc -b && vite build",'
replacement = '"typecheck": "tsc --noEmit",\n    "build": "tsc -b && vite build",'
c = c.replace(target, replacement)
with open(p, 'w') as f: f.write(c)
