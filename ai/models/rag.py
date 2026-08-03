"""Pydantic model for a Knowledge RAG chunk.

A ``RagChunk`` represents a single text fragment stored in Qdrant together with
its metadata.  The ``score`` field is populated only on retrieval; it is never
persisted in the Qdrant payload (see ``to_qdrant_payload``).

New fields added for the knowledge_base corpus:
  doc_type    — e.g. "master_circular", "faq", "riskometer", "act"
  priority    — 1 (highest) … 12 (lowest), matching the ingestion priority spec
  source_file — original filename (for traceability)
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class RagChunk(BaseModel):
    chunk_id:       str
    collection:     str
    document_title: str
    section_id:     str
    text:           str
    score:          float = 0.0   # populated on retrieval; not stored in Qdrant payload
    ingested_at:    str           # ISO datetime string

    # Extended metadata (optional — absent in legacy chunks ingested via MinIO)
    doc_type:    str | None = None
    priority:    int | None = None
    source_file: str | None = None

    def to_qdrant_payload(self) -> dict:
        """Serialise to Qdrant payload dict.
        ``score`` is excluded — it is a retrieval-time value, not stored.
        """
        payload: dict = {
            "chunk_id":       self.chunk_id,
            "collection":     self.collection,
            "document_title": self.document_title,
            "section_id":     self.section_id,
            "text":           self.text,
            "ingested_at":    self.ingested_at,
        }
        # Only include extended fields when they carry a value
        if self.doc_type    is not None:
            payload["doc_type"]    = self.doc_type
        if self.priority    is not None:
            payload["priority"]    = self.priority
        if self.source_file is not None:
            payload["source_file"] = self.source_file
        return payload

    @classmethod
    def from_qdrant_payload(cls, payload: dict, score: float = 0.0) -> "RagChunk":
        """Deserialise from a Qdrant payload dict.

        Unknown keys are silently ignored so older payloads (without doc_type
        etc.) continue to deserialise without errors.
        """
        return cls(
            chunk_id       = payload["chunk_id"],
            collection     = payload["collection"],
            document_title = payload["document_title"],
            section_id     = payload["section_id"],
            text           = payload["text"],
            score          = score,
            ingested_at    = payload["ingested_at"],
            doc_type       = payload.get("doc_type"),
            priority       = payload.get("priority"),
            source_file    = payload.get("source_file"),
        )
