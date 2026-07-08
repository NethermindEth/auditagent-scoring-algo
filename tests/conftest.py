"""Shared pytest configuration and fixtures for the scoring-algo test suite."""

from __future__ import annotations

import pytest

from scoring_algo.core import telemetry


@pytest.fixture(autouse=True)
def _no_telemetry():
    # Keep langfuse out of the test path entirely (no network, no client).
    telemetry.set_telemetry(False)
    yield
    telemetry.set_telemetry(True)
