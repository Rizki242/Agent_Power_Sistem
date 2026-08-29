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
