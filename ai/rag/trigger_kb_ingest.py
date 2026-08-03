"""trigger_kb_ingest.py — Enqueue Celery tasks for every knowledge_base document.

Use this instead of knowledge_base_loader.py when the Celery broker is live
(e.g. in production / staging). Each file is dispatched as an individual
`ingest_local_file` Celery task so ingestion is distributed and retryable.

Usage:
    python -m ai.rag.trigger_kb_ingest [--force]

When --force is omitted, already-completed filenames are skipped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).parent
WORKSPACE_ROOT = HERE.parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from ai.rag.collections import (       # noqa: E402
    COLLECTION_FOLDER_MAP,
    DOCUMENT_REGISTRY,
)
from ai.rag.ingestion import ingest_local_file  # noqa: E402


def trigger(force: bool = False) -> None:
    print("Enqueuing knowledge_base documents via Celery …\n")

    dispatched = 0
    for entry in DOCUMENT_REGISTRY:
        fname      = entry["file"]
        collection = entry["collection"]
        doc_type   = entry["doc_type"]
        doc_title  = entry["title"]
        priority   = entry["priority"]
        folder     = COLLECTION_FOLDER_MAP.get(collection, "")
        fpath      = HERE / "knowledge_base" / folder / fname

        if not fpath.exists():
            print(f"  [SKIP] Not on disk: {fpath}")
            continue

        print(f"  → Enqueuing: {fname} ({collection})")
        ingest_local_file.apply_async(
            kwargs={
                "file_path":  str(fpath),
                "collection": collection,
                "doc_type":   doc_type,
                "doc_title":  doc_title,
                "priority":   priority,
            },
            queue="rag_ingestion",
        )
        dispatched += 1

    print(f"\n✓ {dispatched} task(s) enqueued.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    trigger(force=args.force)
