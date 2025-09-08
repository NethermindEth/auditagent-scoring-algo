from __future__ import annotations

from typing import Any, Callable

TELEMETRY_ENABLED: bool = True

try:
    from langfuse import get_client as _get_client
    from langfuse import observe as _observe
except Exception:
    _get_client = None
    _observe = None


def set_telemetry(enabled: bool) -> None:
    global TELEMETRY_ENABLED
    TELEMETRY_ENABLED = enabled


def observe(*args: Any, **kwargs: Any):  # decorator factory
    if TELEMETRY_ENABLED and _observe is not None:
        return _observe(*args, **kwargs)

    def noop_decorator(func: Callable):
        return func

    return noop_decorator


def update_generation(**payload: Any) -> None:
    if not TELEMETRY_ENABLED or _get_client is None:
        return
    try:  # best-effort
        client = _get_client()
        client.update_current_generation(**payload)
    except Exception:
        return
