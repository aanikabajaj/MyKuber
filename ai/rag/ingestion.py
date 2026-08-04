"""Celery worker for asynchronous RAG document ingestion.

Two ingestion paths
-------------------
1. MinIO path (existing):  ingest_document(bucket, object_key, collection)
   Triggered by MinIO event notifications for user-uploaded documents.

2. Local knowledge_base path:  ingest_local_file(file_path, collection, doc_type, doc_title, priority)
   Used by knowledge_base_loader.py and for ad-hoc refreshes of the
   regulatory document corpus.

Chunking is adaptive: see ai/rag/chunking.py for the strategy selection logic.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from celery import Celery

from ai.core.config import settings

celery_app = Celery(
    "ai_rag_ingestion",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _get_db_session():
    """Return a sync SQLAlchemy Session for AI_PostgreSQL (Celery context)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.AI_DATABASE_URL.replace(
        "postgresql+asyncpg", "postgresql+psycopg2"
    )
    engine = create_engine(sync_url)
    return sessionmaker(bind=engine)()


def _get_qdrant():
    from qdrant_client import QdrantClient  # type: ignore
    return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)


def _get_embedding_model():
    from sentence_transformers import SentenceTransformer  # type: ignore
    return SentenceTransformer("all-MiniLM-L6-v2")


def _upsert_chunks(
    qdrant,
    model,
    chunks_text: list[str],
    collection: str,
    doc_title: str,
    doc_type: str,
    priority: int,
    source_file: str,
    batch_size: int = 32,
) -> int:
    """Embed and upsert chunks. Returns number of upserted points."""
    from qdrant_client.models import PointStruct  # type: ignore

    now_iso = datetime.now(timezone.utc).isoformat()
    points = []

    for batch_start in range(0, len(chunks_text), batch_size):
        batch = chunks_text[batch_start: batch_start + batch_size]
        embeddings = model.encode(batch, convert_to_numpy=True)

        for local_i, (chunk_str, emb) in enumerate(zip(batch, embeddings)):
            global_i = batch_start + local_i
            chunk_id = f"{source_file}-chunk-{global_i}"
            payload = {
                "chunk_id":       chunk_id,
                "collection":     collection,
                "document_title": doc_title,
                "doc_type":       doc_type,
                "priority":       priority,
                "section_id":     f"chunk-{global_i}",
                "text":           chunk_str,
                "source_file":    source_file,
                "ingested_at":    now_iso,
            }
            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=emb.tolist(),
                    payload=payload,
                )
            )

    qdrant.upsert(collection_name=collection, points=points, wait=True)
    return len(points)


def _record_metadata(db, filename: str, collection: str, chunk_count: int, minio_key: str):
    from ai.models.ai_tables import AIDocumentMetadata  # noqa: PLC0415
    meta = AIDocumentMetadata(
        filename=filename,
        collection=collection,
        chunk_count=chunk_count,
        ingested_at=datetime.now(timezone.utc),
        minio_key=minio_key,
        status="completed",
    )
    db.add(meta)
    db.commit()


# ---------------------------------------------------------------------------
# Task 1: MinIO-triggered ingestion (existing path, now with adaptive chunking)
# ---------------------------------------------------------------------------

@celery_app.task(name="ai.rag.ingestion.ingest_document", bind=True, max_retries=3)
def ingest_document(self, bucket: str, object_key: str, collection: str) -> dict:
    """Download document from MinIO, chunk adaptively, embed, upsert to Qdrant."""
    from minio import Minio  # type: ignore
    from ai.rag.chunking import chunk_text, select_config, SMALL_CHUNK

    # Download
    minio_client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    response = minio_client.get_object(bucket, object_key)
    raw_bytes = response.read()
    response.close()
    text = raw_bytes.decode("utf-8", errors="replace")

    # Adaptive chunking — treat MinIO uploads as medium docs by default
    cfg = SMALL_CHUNK if len(text) < 20_000 else select_config("circular", 40)
    chunks = chunk_text(text, cfg)

    model  = _get_embedding_model()
    qdrant = _get_qdrant()
    db     = _get_db_session()

    n = _upsert_chunks(
        qdrant, model, chunks, collection,
        doc_title=object_key, doc_type="upload", priority=5,
        source_file=object_key,
    )
    _record_metadata(db, object_key, collection, len(chunks), f"{bucket}/{object_key}")
    db.close()

    return {"chunk_count": n, "collection": collection, "source": "minio"}


# ---------------------------------------------------------------------------
# Task 2: Local-file ingestion (knowledge_base/ corpus)
# ---------------------------------------------------------------------------

@celery_app.task(name="ai.rag.ingestion.ingest_local_file", bind=True, max_retries=3)
def ingest_local_file(
    self,
    file_path: str,
    collection: str,
    doc_type: str,
    doc_title: str,
    priority: int = 5,
) -> dict:
    """Ingest a local PDF or XLSX file into Qdrant (used by knowledge_base_loader)."""
    from ai.rag.chunking import chunk_text, select_config, RISKOMETER

    fpath  = Path(file_path)
    suffix = fpath.suffix.lower()
    fname  = fpath.name

    if suffix == ".pdf":
        import pdfplumber  # type: ignore
        pages: list[str] = []
        with pdfplumber.open(fpath) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                pages.append(t)
        full_text  = "\n\n".join(pages)
        page_count = len(pages)
        cfg        = select_config(doc_type, page_count)
        chunks     = chunk_text(full_text, cfg)

    elif suffix in (".xlsx", ".xls"):
        import openpyxl  # type: ignore
        wb     = openpyxl.load_workbook(fpath, read_only=True, data_only=True)
        chunks = []
        for ws in wb.worksheets:
            headers: list[str] = []
            for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
                if row_idx == 0:
                    headers = [str(c).strip() if c else f"Col{i}" for i, c in enumerate(row)]
                    continue
                if all(c is None for c in row):
                    continue
                parts = [f"{headers[i] if i < len(headers) else f'Col{i}'}: {v}"
                         for i, v in enumerate(row) if v is not None]
                if parts:
                    chunks.append("  |  ".join(parts))
        wb.close()
    else:
        return {"error": f"Unsupported format: {suffix}"}

    if not chunks:
        return {"error": "No text extracted", "file": fname}

    model  = _get_embedding_model()
    qdrant = _get_qdrant()
    db     = _get_db_session()

    n = _upsert_chunks(
        qdrant, model, chunks, collection,
        doc_title=doc_title, doc_type=doc_type,
        priority=priority, source_file=fname,
    )
    _record_metadata(db, fname, collection, len(chunks), f"local/{fname}")
    db.close()

    return {"chunk_count": n, "collection": collection, "source": "local", "file": fname}
