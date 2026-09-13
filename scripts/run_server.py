"""
Robust FastAPI Launcher for Power Plant O&M Reliability Platform.
Checks for port availability, releases stale background processes if needed, and starts Uvicorn.
"""

import os
import sys
import socket
import subprocess
import time
from pathlib import Path

# This launcher lives in scripts/ (repo convention for helper scripts), but the
# app it serves ("api_server:app") lives at the repo root. Put the root on
# sys.path so `python scripts/run_server.py`, run_api.bat and `pple serve api`
# all resolve api_server the same way regardless of where they were invoked.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return False
        except OSError:
            return True


def kill_process_on_port(port: int):
    if sys.platform == "win32":
        try:
            # Find PID using netstat
            output = subprocess.check_output(f"netstat -ano | findstr :{port}", shell=True, text=True)
            killed_pids = set()
            for line in output.strip().split("\n"):
                parts = line.strip().split()
                if len(parts) >= 5 and f":{port}" in parts[1] and parts[3] == "LISTENING":
                    pid = parts[4]
                    if pid != str(os.getpid()) and pid not in killed_pids:
                        killed_pids.add(pid)
                        print(f"[*] Menutup proses lama (PID: {pid}) yang menahan Port {port}...")
                        subprocess.run(f"taskkill /F /T /PID {pid}", shell=True, capture_output=True)
            time.sleep(1)
        except Exception:
            pass


def main(host: str = None, port: int = None):
    """Start the FastAPI server. `host`/`port` default to the HOST/PORT env
    vars (0.0.0.0/8000) when not passed - this keeps `python scripts/run_server.py`
    and run_api.bat working unchanged while letting `pple serve api`
    (pple/cli/main.py, docs/final.md Phase 23) pass --host/--port through
    to the exact same launcher instead of reimplementing it."""
    port = port if port is not None else int(os.getenv("PORT", "8000"))
    host = host or os.getenv("HOST", "0.0.0.0")

    print(f"============================================================")
    print(f"🚀 Memulai Power Plant O&M Reliability API Server...")
    print(f"📍 Host: {host} | Port: {port}")
    print(f"============================================================")

    if is_port_in_use(port, "127.0.0.1"):
        print(f"[!] Port {port} sedang digunakan oleh proses lain. Membersihkan port...")
        kill_process_on_port(port)

    import uvicorn
    # Try 0.0.0.0, fallback to 127.0.0.1 if permission issues occur
    try:
        uvicorn.run("api_server:app", host=host, port=port, reload=True)
    except OSError as e:
        if "10013" in str(e) or "access permissions" in str(e).lower():
            print(f"[!] Port {port} dibatasi pada 0.0.0.0, beralih ke 127.0.0.1...")
            uvicorn.run("api_server:app", host="127.0.0.1", port=port, reload=True)
        else:
            raise e


if __name__ == "__main__":
    main()
