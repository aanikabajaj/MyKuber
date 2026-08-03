"""Integration test for the RAG document ingestion Celery task.

All external I/O (MinIO, Qdrant, SQLAlchemy, FlagEmbedding) is mocked using
``sys.modules`` injection so the test runs offline without any of those
packages being installed.  The task is called via ``.apply()`` to execute
synchronously in-process.

**Validates: Requirements 10.6, 10.8 — Task 14.4**
"""
from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SAMPLE_TEXT = (
    "SEBI Investment Adviser Regulations 2013.\n"
    "No person shall act as an investment adviser unless registered.\n"
    "Registration requirements include educational qualifications.\n"
    "Advisory fees must be disclosed transparently to clients.\n"
)

_BUCKET = "rag-documents"
_OBJECT_KEY = "sebi_regulations_test.txt"
_COLLECTION = "SEBI_Regulations"


# ---------------------------------------------------------------------------
# sys.modules stubs for optional heavy dependencies
# ---------------------------------------------------------------------------

def _build_module_stubs() -> dict[str, types.ModuleType]:
    """Return a dict of fake modules to inject into sys.modules."""
    stubs: dict[str, types.ModuleType] = {}

    # ---- minio ----
    minio_mod = types.ModuleType("minio")
    stubs["minio"] = minio_mod

    # ---- qdrant_client ----
    qc_mod = types.ModuleType("qdrant_client")
    qc_models_mod = types.ModuleType("qdrant_client.models")
    # PointStruct: a simple container used in assertions
    class _PointStruct:
        def __init__(self, id, vector, payload):
            self.id = id
            self.vector = vector
            self.payload = payload
    qc_models_mod.PointStruct = _PointStruct  # type: ignore[attr-defined]
    qc_mod.models = qc_models_mod  # type: ignore[attr-defined]
    stubs["qdrant_client"] = qc_mod
    stubs["qdrant_client.models"] = qc_models_mod

    # ---- FlagEmbedding ----
    fe_mod = types.ModuleType("FlagEmbedding")
    stubs["FlagEmbedding"] = fe_mod

    return stubs


# ---------------------------------------------------------------------------
# Fixture: inject stubs and reload the ingestion module cleanly each test
# ---------------------------------------------------------------------------

@pytest.fixture()
def ingestion_task(tmp_path):
    """
    Yield the ``ingest_document`` Celery task with all heavy deps stubbed out.

    The fixture:
    1. Injects fake modules into sys.modules.
    2. Re-imports (or reloads) ``ai.rag.ingestion`` so it picks up the stubs.
    3. Yields the task callable.
    4. Restores sys.modules on teardown.
    """
    stubs = _build_module_stubs()
    originals: dict[str, object] = {}

    # Save originals and inject stubs
    for name, mod in stubs.items():
        originals[name] = sys.modules.get(name, None)
        sys.modules[name] = mod  # type: ignore[assignment]

    # Reload the ingestion module so it re-resolves the lazy imports against
    # our stubs at task execution time.
    if "ai.rag.ingestion" in sys.modules:
        del sys.modules["ai.rag.ingestion"]

    import ai.rag.ingestion as _ingestion_mod  # noqa: PLC0415
    importlib.reload(_ingestion_mod)

    yield _ingestion_mod.ingest_document

    # Teardown: restore originals
    for name, original in originals.items():
        if original is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = original  # type: ignore[assignment]

    # Re-remove the reloaded module to avoid leaking into other test files
    sys.modules.pop("ai.rag.ingestion", None)


# ---------------------------------------------------------------------------
# Helper: build mocks and wire them into the stub modules
# ---------------------------------------------------------------------------

def _wire_mocks(stubs: dict, text: str, upserted: list, added_rows: list) -> None:
    """Configure the stub modules with concrete mock objects."""
    import numpy as np

    # MinIO mock
    response_mock = MagicMock()
    response_mock.read.return_value = text.encode("utf-8")
    response_mock.close.return_value = None
    minio_instance = MagicMock()
    minio_instance.get_object.return_value = response_mock
    stubs["minio"].Minio = MagicMock(return_value=minio_instance)

    # Qdrant mock
    qdrant_instance = MagicMock()
    qdrant_instance.upsert.side_effect = lambda collection_name, points: upserted.extend(
        points
    )
    stubs["qdrant_client"].QdrantClient = MagicMock(return_value=qdrant_instance)

    # BGE-M3 mock
    def _fake_encode(texts, batch_size=8):
        return {"dense_vecs": [np.zeros(1024) for _ in texts]}
    bge_instance = MagicMock()
    bge_instance.encode.side_effect = _fake_encode
    stubs["FlagEmbedding"].BGEM3FlagModel = MagicMock(return_value=bge_instance)


class TestIngestDocumentTask:
    """Unit-level integration tests for ``ingest_document``."""

    def _run(self, ingest_document, text: str = _SAMPLE_TEXT):
        """Wire mocks into the stubs and run the task synchronously."""
        import numpy as np  # always available

        upserted: list = []
        added_rows: list = []

        # Build fresh stubs for this run
        stubs = _build_module_stubs()
        _wire_mocks(stubs, text, upserted, added_rows)

        # Inject stubs
        for name, mod in stubs.items():
            sys.modules[name] = mod  # type: ignore[assignment]

        # Patch SQLAlchemy session (always available)
        from unittest.mock import patch, MagicMock as MM  # noqa: PLC0415

        session_mock = MM()
        session_mock.__enter__ = MM(return_value=session_mock)
        session_mock.__exit__ = MM(return_value=False)
        session_mock.add.side_effect = added_rows.append
        session_mock.commit.return_value = None
        session_maker_mock = MM(return_value=session_mock)

        with (
            patch("sqlalchemy.create_engine"),
            patch("sqlalchemy.orm.sessionmaker", return_value=session_maker_mock),
        ):
            result = ingest_document.apply(
                args=[_BUCKET, _OBJECT_KEY, _COLLECTION]
            ).get()

        return result, upserted, added_rows

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_returns_correct_collection(self, ingestion_task):
        result, _, _ = self._run(ingestion_task)
        assert result["collection"] == _COLLECTION

    def test_chunk_count_positive(self, ingestion_task):
        result, _, _ = self._run(ingestion_task)
        assert result["chunk_count"] > 0

    def test_upserted_point_count_matches_chunk_count(self, ingestion_task):
        result, upserted, _ = self._run(ingestion_task)
        assert len(upserted) == result["chunk_count"]

    def test_qdrant_points_have_correct_payload_fields(self, ingestion_task):
        _, upserted, _ = self._run(ingestion_task)
        required_fields = {
            "chunk_id",
            "collection",
            "document_title",
            "section_id",
            "text",
            "ingested_at",
        }
        for point in upserted:
            missing = required_fields - point.payload.keys()
            assert not missing, f"Missing fields in payload: {missing}"

    def test_qdrant_point_collection_field(self, ingestion_task):
        _, upserted, _ = self._run(ingestion_task)
        for point in upserted:
            assert point.payload["collection"] == _COLLECTION

    def test_db_metadata_row_added(self, ingestion_task):
        from ai.models.ai_tables import AIDocumentMetadata

        _, _, added_rows = self._run(ingestion_task)
        assert len(added_rows) == 1
        assert isinstance(added_rows[0], AIDocumentMetadata)

    def test_db_metadata_correct_fields(self, ingestion_task):
        from ai.models.ai_tables import AIDocumentMetadata

        result, _, added_rows = self._run(ingestion_task)
        meta: AIDocumentMetadata = added_rows[0]
        assert meta.filename == _OBJECT_KEY
        assert meta.collection == _COLLECTION
        assert meta.chunk_count == result["chunk_count"]
        assert meta.minio_key == f"{_BUCKET}/{_OBJECT_KEY}"
        assert meta.status == "completed"

    def test_short_document_produces_single_chunk(self, ingestion_task):
        short_text = "Hello world."
        result, upserted, _ = self._run(ingestion_task, text=short_text)
        assert result["chunk_count"] >= 1
        assert len(upserted) >= 1

    def test_large_document_produces_multiple_chunks(self, ingestion_task):
        # ~6000 chars >> 512 tokens * 4 chars/token = 2048 chars per chunk
        large_text = "A" * 6000
        result, upserted, _ = self._run(ingestion_task, text=large_text)
        assert result["chunk_count"] >= 2
        assert len(upserted) == result["chunk_count"]
