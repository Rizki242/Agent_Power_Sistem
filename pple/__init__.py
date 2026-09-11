"""
PPLE V2 core package (docs/final.md).

This package hosts the UI-independent domain layer that api_server.py,
app.py, and (eventually) a CLI will share. It must never import
React/Streamlit/FastAPI-specific request objects.

Migration status: Phase 1 skeleton. Only pple.engineering has real
content so far (EngineeringModule interface + registry + a Vibration
adapter over src.agents.specialist_agents.VibrationAgent). All other
subpackages are placeholders for later phases - see
docs/pple_v2_baseline.md for the phase-by-phase plan.
"""

import sys
from pathlib import Path

# Ensure the repository root (containing `src`) is on sys.path so that
# console scripts (like `pple.exe`) can resolve `src.*` modules reliably.
_repo_root = str(Path(__file__).resolve().parent.parent)
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

