"""Test doubles shared by the test files. Nothing here calls the API."""

from __future__ import annotations

import contextlib
import json
from unittest import mock


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


@contextlib.contextmanager
def without_injection_detection():
    """The rules as they were before AGENT-V2-05, to reproduce the reference baseline of the published run."""
    import prototype

    with mock.patch.object(prototype, "detect_prompt_injection", return_value=[]):
        yield
