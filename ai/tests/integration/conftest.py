"""Integration test conftest — stubs heavy optional dependencies that are not
installed in the local dev/CI environment (e.g. qdrant_client).

These stubs are only injected into sys.modules so that the FastAPI app can be
imported without the real packages present.  All actual Qdrant calls in the
tests are mocked at a higher level via unittest.mock.patch.
"""
from __future__ import annotations
import sys
import types


def _stub_module(name: str) -> types.ModuleType:
    """Create and register a minimal stub module."""
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _ensure_qdrant_stubs() -> None:
    """Inject qdrant_client stubs if the real package is absent."""
    if "qdrant_client" in sys.modules:
        return  # already importable — nothing to do

    # qdrant_client top-level
    qc = _stub_module("qdrant_client")
    qc.AsyncQdrantClient = object  # type: ignore[attr-defined]
    qc.QdrantClient = object  # type: ignore[attr-defined]

    # qdrant_client.models
    qc_models = _stub_module("qdrant_client.models")
    qc_models.Distance = type("Distance", (), {"COSINE": "Cosine"})()
    qc_models.VectorParams = object

    # Make qdrant_client.models accessible as an attribute
    qc.models = qc_models  # type: ignore[attr-defined]


# Run stubs immediately at conftest import time so they are present
# before pytest collects and imports test modules.
_ensure_qdrant_stubs()
