"""pytest configuration for the ai/tests suite."""
from __future__ import annotations


def pytest_configure(config):
    """Set asyncio_mode to 'auto' for pytest-asyncio 0.24."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async",
    )


# Configure pytest-asyncio in auto mode via ini-option injection.
# This is equivalent to asyncio_mode = "auto" in pytest.ini / pyproject.toml.
def pytest_collection_modifyitems(config, items):  # noqa: ARG001
    pass


# Inject asyncio_mode = "auto" programmatically for pytest-asyncio >= 0.21.
import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
