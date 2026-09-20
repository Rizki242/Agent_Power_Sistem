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

# run_api.bat sets `chcp 65001` before launching this script, but other entry
# points (pple serve api, a plain PowerShell/VS Code terminal, launching this
# file directly) don't - on those, Windows' default cp1252 console encoding
# crashes on the emoji below with UnicodeEncodeError before uvicorn even
# starts. Force UTF-8 stdout/stderr so the banner never takes the server down.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
        except Exception:
            pass


def wait_until_port_free(port: int, host: str = "127.0.0.1", timeout: float = 5.0) -> bool:
    """Poll until `port` is free instead of blindly sleeping a fixed amount -
    taskkill returns before Windows has actually released the socket, so a
    fixed sleep(1) sometimes wasn't long enough and uvicorn still crashed
    with WinError 10048 (address already in use)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not is_port_in_use(port, host):
            return True
        time.sleep(0.3)
    return not is_port_in_use(port, host)


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
        if not wait_until_port_free(port):
            print(
                f"[!] Port {port} masih terpakai setelah dibersihkan. "
                "Uvicorn tetap akan mencoba start; jika gagal, tutup manual "
                f"proses yang memegang port {port} (lihat 'netstat -ano | findstr :{port}')."
            )

    import uvicorn

    def _start(bind_host: str):
        uvicorn.run("api_server:app", host=bind_host, port=port, reload=True)

    # Try the requested host, fall back to 127.0.0.1 on Windows-specific
    # binding failures instead of crashing the whole launcher.
    try:
        _start(host)
    except OSError as e:
        message = str(e)
        if "10013" in message or "access permissions" in message.lower():
            print(f"[!] Port {port} dibatasi pada 0.0.0.0, beralih ke 127.0.0.1...")
            _start("127.0.0.1")
        elif "10048" in message or "address already in use" in message.lower():
            # Stale listener survived the earlier cleanup (taskkill can return
            # before Windows actually releases the socket) - clean up once
            # more, wait for the OS to confirm the port is free, then retry.
            print(f"[!] Port {port} masih dipegang proses lain, mencoba membersihkan ulang...")
            kill_process_on_port(port)
            wait_until_port_free(port)
            _start(host)
        else:
            raise


if __name__ == "__main__":
    main()
