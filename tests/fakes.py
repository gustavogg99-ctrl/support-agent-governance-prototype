"""Test doubles shared by the test files. Nothing here calls the API."""

from __future__ import annotations

import json


def classification_json(
    category: object = "Technical Incident",
    priority: object = "Medium",
    sensitive_data: object = False,
    reason: object = "r",
    **extra: object,
) -> str:
    """A classifier reply as the model would send it. Valid unless a test passes a bad value or an extra key."""
    return json.dumps(
        {"category": category, "priority": priority, "sensitive_data": sensitive_data, "reason": reason, **extra}
    )
