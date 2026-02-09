from __future__ import annotations

from typing import Any


def get_by_path(payload: Any, path: str) -> Any:
    """Safely read nested data using dot notation and list indexes."""
    current = payload
    if not path:
        return None
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current
