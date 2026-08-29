"""Shared utility functions for MCSA project.

Centralises helpers that were previously duplicated across multiple modules
(rotorbar, standards, analytics, data_loader, app).
"""

import re


def safe_float(value):
    """Convert *value* to float, returning ``None`` on failure.

    Handles ``None``, empty strings, strings with stray non-numeric
    characters (e.g. units), and comma-separated thousands.
    """
    try:
        if value is None:
            return None
        if isinstance(value, str):
            s = value.strip().replace(',', '')
            s = re.sub(r'[^0-9eE+\-\.]', '', s)
            if s in {'', '+', '-', '.', '+.', '-.'}:
                return None
            value = s
        return float(value)
    except Exception:
        return None
