"""knowledge_base_loader.py — One-shot ingestion of the local knowledge_base/ folder.

Run once (or on update) to populate Qdrant with all regulatory documents:

    python -m ai.rag.knowledge_base_loader

The script:
1. Iterates every file in ai/rag/knowledge_base/ using DOCUMENT_REGISTRY.
2. Extracts text:   PDF → pdfplumber    XLSX → openpyxl (row-by-row)
3. Chooses chunk config via select_config(doc_type, page_count).
4. Embeds chunks with BGE-M3 (batched, CPU-friendly fp32 fallback).
5. Upserts PointStruct records to Qdrant with rich payload metadata.
6. Records AIDocumentMetadata rows in AI_PostgreSQL (sync psycopg2).

Idempotent: already-ingested files are skipped unless --force is passed.
"""
from __future__ import annotations

import argparse
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ── paths ────────────────────────────────────────────────────────────────────
HERE          = Path(__file__).parent                              # ai/rag/
KB_ROOT       = HERE / "knowledge_base"
WORKSPACE_ROOT = HERE.parent.parent                               # project root
sys.path.insert(0, str(WORKSPACE_ROOT))                           # make `ai` importable

from ai.core.config import settings                                # noqa: E402
from ai.rag.collections import (                                   # noqa: E402
    COLLECTION_FOLDER_MAP,
    DOCUMENT_REGISTRY,
    DOCUMENT_REGISTRY_BY_FILE,
    ensure_collections,
)
from ai.rag.chunking import RISKOMETER, chunk_text, select_config  # noqa: E402


# ── helpers ───────────────────────────────────────────────────────────────────

def _extract_pdf(path: Path) -> tuple[str, int]:
    """Return (full_text, page_count). Requires pdfplumber."""
    import pdfplumber  # type: ignore
    pages: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text)
    return "\n\n".join(pages), len(pages)


def _extract_xlsx_rows(path: Path) -> list[str]:
    """Return one text chunk per data row. Requires openpyxl."""
    import openpyxl  # type: ignore
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows_text: list[str] = []
    for ws in wb.worksheets:
        headers: list[str] = []
        for row_idx, row in enumerate(ws.iter_rows(values_only=True)):
            if row_idx == 0:
                headers = [str(c).strip() if c is not None else f"Col{i}"
                           for i, c in enumerate(row)]
                continue
            if all(c is None for c in row):
                continue
            parts = [f"{headers[i] if i < len(headers) else f'Col{i}'}: {v}"
                     for i, v in enumerate(row) if v is not None]
            if parts:
                rows_text.append("  |  ".join(parts))
    wb.close()
    return rows_text


def _build_payload(
    chunk_id: str,
    collection: str,
    doc_title: str,
    doc_type: str,
    priority: int,
    section_id: str,
    text: str,
    source_file: str,
    now_iso: str,
) -> dict[str, Any]:
    return {
        "chunk_id":       chunk_id,
        "collection":     collection,
        "document_title": doc_title,
        "doc_type":       doc_type,
        "priority":       priority,
        "section_id":     section_id,
        "text":           text,
        "source_file":    source_file,
        "ingested_at":    now_iso,
    }


# ── main ingestion function ────────────────────────────────────────────────────

def ingest_knowledge_base(force: bool = False, batch_size: int = 32) -> None:
    """Ingest all knowledge_base documents into Qdrant."""
    from FlagEmbedding import BGEM3FlagModel  # type: ignore
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    print("── Loading BGE-M3 model …")
    try:
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
    except Exception:
        print("  fp16 unavailable, falling back to fp32")
        model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=False)

    print("── Connecting to Qdrant …")
    qdrant = QdrantClient(url=settings.QDRANT_URL)
    ensure_collections(qdrant)

    print("── Connecting to AI_PostgreSQL …")
    sync_url = settings.AI_DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    engine = create_engine(sync_url)
    Session = sessionmaker(bind=engine)

    # Collect already-ingested filenames to support idempotent re-runs
    ingested_files: set[str] = set()
    if not force:
        with Session() as db:
            try:
                rows = db.execute(
                    text("SELECT filename FROM ai_document_metadata WHERE status='completed'")
                ).fetchall()
                ingested_files = {r[0] for r in rows}
            except Exception:
                pass  # table may not exist yet on first run

    total_chunks = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for entry in DOCUMENT_REGISTRY:
        fname      = entry["file"]
        collection = entry["collection"]
        doc_title  = entry["title"]
        doc_type   = entry["doc_type"]
        priority   = entry["priority"]

        # Locate the file on disk
        folder = COLLECTION_FOLDER_MAP.get(collection, "")
        fpath  = KB_ROOT / folder / fname
        if not fpath.exists():
            print(f"  [SKIP] Not found on disk: {fpath}")
            continue

        if fname in ingested_files:
            print(f"  [SKIP] Already ingested: {fname}")
            continue

        print(f"  [INGEST] {fname}")

        # ── Extract text / rows ─────────────────────────────────────────────
        suffix = fpath.suffix.lower()
        chunks_text: list[str] = []
        page_count = 0

        if suffix == ".pdf":
            try:
                full_text, page_count = _extract_pdf(fpath)
            except Exception as exc:
                print(f"    ERROR extracting PDF: {exc}")
                continue
            cfg = select_config(doc_type, page_count)
            chunks_text = chunk_text(full_text, cfg)

        elif suffix in (".xlsx", ".xls"):
            try:
                rows = _extract_xlsx_rows(fpath)
            except Exception as exc:
                print(f"    ERROR extracting XLSX: {exc}")
                continue
            chunks_text = rows  # each row is its own chunk
            page_count = 1       # XLSX has no "pages"

        else:
            print(f"    [SKIP] Unsupported format: {suffix}")
            continue

        if not chunks_text:
            print(f"    [WARN] No text extracted from {fname}")
            continue

        print(f"    → {len(chunks_text)} chunks (doc_type={doc_type}, pages≈{page_count})")

        # ── Embed in batches ────────────────────────────────────────────────
        points: list[PointStruct] = []
        for batch_start in range(0, len(chunks_text), batch_size):
            batch = chunks_text[batch_start: batch_start + batch_size]
            try:
                embeddings = model.encode(batch, batch_size=len(batch))["dense_vecs"]
            except Exception as exc:
                print(f"    ERROR embedding batch {batch_start}: {exc}")
                continue

            for local_i, (chunk_str, emb) in enumerate(zip(batch, embeddings)):
                global_i  = batch_start + local_i
                chunk_id  = f"{fname}-chunk-{global_i}"
                section_id = f"chunk-{global_i}"
                payload = _build_payload(
                    chunk_id, collection, doc_title, doc_type,
                    priority, section_id, chunk_str, fname, now_iso,
                )
                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=emb.tolist(),
                        payload=payload,
                    )
                )

        # ── Upsert to Qdrant ────────────────────────────────────────────────
        try:
            qdrant.upsert(collection_name=collection, points=points, wait=True)
        except Exception as exc:
            print(f"    ERROR upserting to Qdrant: {exc}")
            continue

        total_chunks += len(points)

        # ── Record metadata in AI_PostgreSQL ────────────────────────────────
        from ai.models.ai_tables import AIDocumentMetadata  # noqa: PLC0415
        with Session() as db:
            try:
                meta = AIDocumentMetadata(
                    filename=fname,
                    collection=collection,
                    chunk_count=len(chunks_text),
                    ingested_at=datetime.now(timezone.utc),
                    minio_key=f"local/{folder}/{fname}",
                    status="completed",
                )
                db.add(meta)
                db.commit()
            except Exception as exc:
                db.rollback()
                print(f"    [WARN] Could not record metadata: {exc}")

    print(f"\n✓ Ingestion complete. Total chunks upserted: {total_chunks}")


# ── CLI entry-point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest knowledge_base/ documents into Qdrant"
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-ingest even if already marked completed"
    )
    parser.add_argument(
        "--batch-size", type=int, default=32,
        help="BGE-M3 embedding batch size (default: 32)"
    )
    args = parser.parse_args()
    ingest_knowledge_base(force=args.force, batch_size=args.batch_size)
