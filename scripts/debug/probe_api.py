import urllib.request
import time

endpoints = [
    "/docs",
    "/api/health",
    "/api/summary",
    "/api/equipment",
    "/api/settings/overview",
    "/api/settings/ai",
    "/api/automations/workflows",
    "/api/automations/runs",
    "/api/materi",
    "/api/vibration/equipment",
    "/api/vibration/summary",
    "/api/vibration/classes",
    "/api/vibration/tests",
    "/api/dga/summary",
    "/api/dga/transformers",
    "/api/pd/summary",
    "/api/pd/samples",
    "/api/tribology/summary",
    "/api/tribology/samples",
    "/api/thermal/summary",
    "/api/thermal/inspections",
    "/api/workorders",
    "/api/agents/specialists",
    "/api/skills/learned-patterns",
    "/api/v2/modules",
    "/api/v2/module-load-report",
    "/api/v2/assets/tree",
    "/api/v2/assets",
    "/api/v2/agents",
    "/api/v2/audit",
    "/api/v2/domain/domains",
    "/api/v2/domain/vibrasi/summary",
]

for path in endpoints:
    url = f"http://127.0.0.1:8000{path}"
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Probe/1.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            dt = time.time() - t0
            print(f"[OK] {resp.status} ({dt:.2f}s) {path}", flush=True)
    except Exception as e:
        dt = time.time() - t0
        print(f"[FAIL] ({dt:.2f}s) {path} -> {e}", flush=True)
