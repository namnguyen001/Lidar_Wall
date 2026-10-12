import argparse
import ctypes
import glob
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


if getattr(sys, 'frozen', False):
    ROOT = Path(sys.executable).parent
    BACKEND_ROOT = ROOT
else:
    ROOT = Path(__file__).resolve().parents[2]
    BACKEND_ROOT = ROOT / "backend"
    
WEBVIEW2_DOWNLOAD = "https://developer.microsoft.com/microsoft-edge/webview2/"


def show_message(title: str, message: str, error: bool = False) -> None:
    print(f"{title}: {message}", file=sys.stderr if error else sys.stdout, flush=True)
    if os.name == "nt":
        flags = 0x10 if error else 0x40
        ctypes.windll.user32.MessageBoxW(None, message, title, flags)


def has_webview2_runtime() -> bool:
    if os.name != "nt":
        return True

    try:
        import winreg

        clients_root = r"SOFTWARE\Microsoft\EdgeUpdate\Clients"
        registry_locations = (
            (winreg.HKEY_CURRENT_USER, clients_root),
            (winreg.HKEY_LOCAL_MACHINE, clients_root),
            (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\{clients_root}"),
        )
        for hive, path in registry_locations:
            try:
                with winreg.OpenKey(hive, path) as clients:
                    for index in range(winreg.QueryInfoKey(clients)[0]):
                        client_name = winreg.EnumKey(clients, index)
                        with winreg.OpenKey(clients, client_name) as client:
                            try:
                                name, _ = winreg.QueryValueEx(client, "name")
                                if name == "Microsoft Edge WebView2 Runtime":
                                    return True
                            except OSError:
                                continue
            except OSError:
                continue
    except ImportError:
        return False

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    runtime_exe_local = os.path.join(local_app_data, "Microsoft", "EdgeWebView", "Application", "*", "msedgewebview2.exe")
    
    program_files = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    runtime_exe_system = os.path.join(program_files, "Microsoft", "EdgeWebView", "Application", "*", "msedgewebview2.exe")
    
    return bool(glob.glob(runtime_exe_local) or glob.glob(runtime_exe_system))


def ensure_port_available(host: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.25)
        if probe.connect_ex((host, port)) == 0:
            raise OSError(f"Cổng {port} đang được sử dụng. Hãy đóng bản ứng dụng khác hoặc chọn --port khác.")


def wait_until_ready(thread: threading.Thread, health_url: str, timeout: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not thread.is_alive():
            return False
        try:
            with urllib.request.urlopen(health_url, timeout=0.5) as response:
                if response.status == 200:
                    return True
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(0.25)
    return False


class DesktopApi:
    def __init__(self, webview: Any, base_url: str):
        self._webview = webview
        self._base_url = base_url
        self._wall_window: Any | None = None

    def list_screens(self) -> list[dict[str, int | bool]]:
        return [
            {
                "index": index,
                "x": screen.x,
                "y": screen.y,
                "width": screen.width,
                "height": screen.height,
                "primary": index == 0,
            }
            for index, screen in enumerate(self._webview.screens)
        ]

    def open_wall(self, screen_index: int = 0) -> bool:
        screens = self._webview.screens
        if not screens:
            raise RuntimeError("Không tìm thấy màn hình hiển thị.")
        if screen_index < 0 or screen_index >= len(screens):
            raise ValueError(f"Màn hình {screen_index} không tồn tại.")
        self.close_wall()
        wall_window = self._webview.create_window(
            "Lidar Interactive Wall",
            f"{self._base_url}/wall",
            fullscreen=True,
            frameless=True,
            screen=screens[screen_index],
            js_api=self,
        )
        wall_window.events.closed += self._wall_closed
        self._wall_window = wall_window
        return True

    def _wall_closed(self) -> None:
        self._wall_window = None

    def close_wall(self) -> bool:
        if self._wall_window is None:
            return False
        wall_window = self._wall_window
        self._wall_window = None
        try:
            wall_window.destroy()
        except Exception:
            pass
        return True


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lidar Interactive Wall desktop application")
    parser.add_argument("--dev", action="store_true", help="Load the Vite development server at localhost:5173")
    parser.add_argument("--port", type=int, default=8080, help="Local FastAPI port (default: 8080)")
    parser.add_argument("--debug", action="store_true", help="Enable pywebview developer tools")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    host = "127.0.0.1"
    app_url = "http://localhost:5173" if args.dev else f"http://{host}:{args.port}"
    health_url = f"http://{host}:{args.port}/api/health"

    try:
        import webview
    except ImportError:
        show_message("Lidar Interactive Wall", "Chưa cài pywebview. Chạy: pip install -r backend/requirements.txt", True)
        return 1

    if not has_webview2_runtime():
        show_message(
            "Thiếu WebView2 Runtime",
            f"Cài Microsoft Edge WebView2 Runtime rồi mở lại ứng dụng:\n{WEBVIEW2_DOWNLOAD}",
            True,
        )
        return 1

    try:
        ensure_port_available(host, args.port)
    except OSError as error:
        show_message("Không thể khởi động Lidar Interactive Wall", str(error), True)
        return 1

    os.chdir(BACKEND_ROOT)
    sys.path.insert(0, str(BACKEND_ROOT))
    import uvicorn
    from app.main import app

    config = uvicorn.Config(app, host=host, port=args.port, log_level="info")
    server = uvicorn.Server(config)

    def _run_server() -> None:
        try:
            server.run()
        except Exception:
            pass

    server_thread = threading.Thread(target=_run_server, name="lidar-fastapi", daemon=True)
    print(f"Đang khởi động backend tại {health_url}...", flush=True)
    server_thread.start()

    if not wait_until_ready(server_thread, health_url):
        server.should_exit = True
        server_thread.join(timeout=10)
        show_message(
            "Backend không khởi động được",
            f"Không nhận được phản hồi từ {health_url} trong 15 giây. Kiểm tra log backend và cổng {args.port}.",
            True,
        )
        return 1

    api = DesktopApi(webview, app_url)
    main_window = webview.create_window(
        "Lidar Interactive Wall",
        f"{app_url}/control",
        width=1440,
        height=900,
        min_size=(1100, 700),
        js_api=api,
    )

    def close_application() -> None:
        server.should_exit = True
        try:
            api.close_wall()
        except Exception as error:
            print(f"Không đóng được cửa sổ Wall: {error}", file=sys.stderr, flush=True)

    main_window.events.closed += close_application
    try:
        webview.start(debug=args.debug)
    except Exception as error:
        server.should_exit = True
        show_message(
            "Không thể mở cửa sổ desktop",
            f"{error}\n\nĐảm bảo WebView2 Runtime đã được cài đặt: {WEBVIEW2_DOWNLOAD}",
            True,
        )
        return 1
    finally:
        server.should_exit = True
        server_thread.join(timeout=15)
        if server_thread.is_alive():
            print("Backend chưa dừng trong 15 giây; kiểm tra task và driver đang hoạt động.", file=sys.stderr, flush=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())