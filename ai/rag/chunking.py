"""Adaptive chunking strategies for the knowledge-base ingestion pipeline.

Strategy selection
------------------
Document type       | Strategy
--------------------|--------------------------------------------
riskometer (XLSX)   | row_by_row   — each row becomes one chunk
faq / charter       | small_chunks — 256 tok / 32 tok overlap
short docs < 20 pp  | small_chunks — 256 tok / 32 tok overlap
medium docs 20-80pp | medium_chunks— 384 tok / 48 tok overlap
large docs  > 80 pp | large_chunks — 512 tok / 64 tok overlap

All token estimates use the 1 token ≈ 4 chars heuristic to stay
dependency-free (no tiktoken needed at ingestion time).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# 1 token ≈ 4 characters (conservative for Indian regulatory English)
CHARS_PER_TOKEN = 4


@dataclass
class ChunkConfig:
    chunk_tokens: int
    overlap_tokens: int
    strategy: Literal["fixed_overlap", "paragraph", "row_by_row"]


# Pre-defined size presets
SMALL_CHUNK   = ChunkConfig(chunk_tokens=256,  overlap_tokens=32,  strategy="paragraph")
MEDIUM_CHUNK  = ChunkConfig(chunk_tokens=384,  overlap_tokens=48,  strategy="paragraph")
LARGE_CHUNK   = ChunkConfig(chunk_tokens=512,  overlap_tokens=64,  strategy="paragraph")
RISKOMETER    = ChunkConfig(chunk_tokens=0,    overlap_tokens=0,   strategy="row_by_row")

FAQ_TYPES   = {"faq", "charter"}
SHORT_LIMIT = 20   # pages
MEDIUM_LIMIT = 80  # pages


def select_config(doc_type: str, page_count: int) -> ChunkConfig:
    """Return the appropriate ChunkConfig for a document."""
    if doc_type == "riskometer":
        return RISKOMETER
    if doc_type in FAQ_TYPES or page_count < SHORT_LIMIT:
        return SMALL_CHUNK
    if page_count < MEDIUM_LIMIT:
        return MEDIUM_CHUNK
    return LARGE_CHUNK


# ---------------------------------------------------------------------------
# Paragraph-aware chunking
# ---------------------------------------------------------------------------

def _split_paragraphs(text: str) -> list[str]:
    """Split on blank lines; keep each paragraph intact."""
    raw = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in raw if p.strip()]


def chunk_by_paragraphs(
    text: str,
    chunk_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Merge paragraphs into chunks up to chunk_tokens, with overlap sliding window."""
    max_chars   = chunk_tokens   * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN

    paragraphs = _split_paragraphs(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para)
        if current_len + para_len + 1 > max_chars and current:
            chunks.append("\n\n".join(current))
            # Roll overlap: keep paragraphs from the tail that fit in overlap_chars
            tail: list[str] = []
            tail_len = 0
            for p in reversed(current):
                if tail_len + len(p) <= overlap_chars:
                    tail.insert(0, p)
                    tail_len += len(p)
                else:
                    break
            current = tail
            current_len = tail_len
        current.append(para)
        current_len += para_len + 1  # +1 for separator

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text]


def chunk_fixed(text: str, chunk_tokens: int, overlap_tokens: int) -> list[str]:
    """Simple character-window chunking (fallback for non-paragraph text)."""
    max_chars   = chunk_tokens   * CHARS_PER_TOKEN
    overlap_chars = overlap_tokens * CHARS_PER_TOKEN
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        start += max_chars - overlap_chars
        if start >= len(text):
            break
    return chunks if chunks else [text]


def chunk_text(text: str, config: ChunkConfig) -> list[str]:
    """Dispatch to the right chunking function based on config.strategy."""
    if config.strategy == "row_by_row":
        # Caller handles XLSX separately — this path is a no-op safety net
        return [text]
    if config.strategy == "paragraph":
        result = chunk_by_paragraphs(text, config.chunk_tokens, config.overlap_tokens)
        # Fall back to fixed if paragraphs produced nothing useful
        if not result or (len(result) == 1 and len(result[0]) < 20):
            result = chunk_fixed(text, config.chunk_tokens, config.overlap_tokens)
        return result
    return chunk_fixed(text, config.chunk_tokens, config.overlap_tokens)
