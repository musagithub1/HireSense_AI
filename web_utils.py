"""Small helpers for safely embedding data in browser components."""

from __future__ import annotations

import json
from typing import Any


def json_for_script(value: Any) -> str:
    """Serialize JSON without allowing an HTML script element to be closed."""
    return (
        json.dumps(value, ensure_ascii=True)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )
