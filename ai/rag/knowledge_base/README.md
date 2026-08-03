# Knowledge Base — Regulatory Document Corpus

This folder contains the local regulatory documents that are ingested into
the Qdrant vector store to power the Wealth Intelligence AI's RAG pipeline.

## Folder → Qdrant Collection Mapping

| Folder | Qdrant Collection | Priority |
|--------|-------------------|----------|
| `SEBI Master Circulars/` | `SEBI_Regulations` | 1 (30–35 % of RAG) |
| `RBI Master Directions/` | `RBI_Guidelines` | 2 |
| `Taxation (CBDT & Income Tax)/` | `CBDT_Tax` | 3 |
| `AMFI Scheme/` | `AMFI_MutualFunds` | 4 |

## Chunking Strategy

| Document type | Chunk size | Overlap | Notes |
|---------------|-----------|---------|-------|
| FAQ / Charter | 256 tokens | 32 | Small docs, high retrieval precision |
| Short (< 20 pp) | 256 tokens | 32 | |
| Medium (20–80 pp) | 384 tokens | 48 | Most circulars / directions |
| Large (> 80 pp) | 512 tokens | 64 | Full Acts, Master Circulars |
| XLSX Riskometer | 1 row = 1 chunk | — | Row-by-row, each row is a point |

All chunking uses paragraph-aware splitting: paragraph boundaries are
preserved wherever possible, then a sliding window is applied.

## How to Ingest

**Option A — Direct (no Celery broker required):**
```bash
cd <workspace_root>
python -m ai.rag.knowledge_base_loader
# Add --force to re-ingest already-completed files
python -m ai.rag.knowledge_base_loader --force
```

**Option B — Via Celery (production/staging with broker running):**
```bash
python -m ai.rag.trigger_kb_ingest
```

Both options are idempotent by default: files already recorded as
`status='completed'` in `ai_document_metadata` are skipped.

## Adding New Documents

1. Place the PDF or XLSX in the appropriate subfolder.
2. Add an entry to `DOCUMENT_REGISTRY` in `ai/rag/collections.py`.
3. Re-run `knowledge_base_loader.py` (or `trigger_kb_ingest.py`).

## Personalised Retrieval

At query time, `ai/rag/retrieval.py` boosts collection scores based on
the authenticated user's profile fetched from the IAARE backend:

- **Balance bucket / investment goals** → boosts SEBI + AMFI scores
- **Face-ID / TOTP enabled** → boosts RBI KYC scores
- **NPS / pension holdings** → boosts PFRDA scores
- **Insurance holdings** → boosts IRDAI scores
- **High risk profile** → boosts NSE/BSE scores
- **UPI / payment goals** → boosts RBI UPI scores
