from __future__ import annotations

import asyncio
import functools
from collections.abc import Callable
from typing import Any

TELEMETRY_ENABLED: bool = True

# Cache for langfuse-wrapped versions of decorated functions.
_wrapped_cache: dict[Callable, Callable] = {}


def set_telemetry(enabled: bool) -> None:
    global TELEMETRY_ENABLED
    TELEMETRY_ENABLED = enabled


def observe(*args: Any, **kwargs: Any) -> Callable:
    """Drop-in replacement for ``langfuse.observe``.

    Returns a decorator that checks ``TELEMETRY_ENABLED`` **at call time**:
    * ``False`` → original function called directly (langfuse never imported).
    * ``True``  → lazily imports langfuse, wraps the function once, caches it.
    """

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*a: Any, **kw: Any) -> Any:
                if not TELEMETRY_ENABLED:
                    return await func(*a, **kw)
                wrapped = _get_or_create_wrapped(func, args, kwargs)
                return await wrapped(*a, **kw)

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*a: Any, **kw: Any) -> Any:
            if not TELEMETRY_ENABLED:
                return func(*a, **kw)
            wrapped = _get_or_create_wrapped(func, args, kwargs)
            return wrapped(*a, **kw)

        return sync_wrapper

    return decorator


def _get_or_create_wrapped(func: Callable, dec_args: tuple, dec_kwargs: dict) -> Callable:
    """Return a langfuse-wrapped version of *func*, creating it on first call."""
    if func not in _wrapped_cache:
        try:
            from langfuse import observe as _real_observe

            _wrapped_cache[func] = _real_observe(*dec_args, **dec_kwargs)(func)
        except Exception:
            # langfuse unavailable – fall back to bare function.
            _wrapped_cache[func] = func
    return _wrapped_cache[func]


def update_generation(**payload: Any) -> None:
    if not TELEMETRY_ENABLED:
        return
    try:
        from langfuse import get_client

        client = get_client()
        client.update_current_generation(**payload)
    except Exception:
        return
