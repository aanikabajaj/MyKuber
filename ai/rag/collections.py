"""Qdrant collection definitions — aligned with the local knowledge_base folder.

Collection → Source documents mapping
--------------------------------------
SEBI_Regulations      SEBI Master Circulars/ (all PDFs)
RBI_Guidelines        RBI Master Directions/ (all PDFs)
CBDT_Tax              Taxation (CBDT & Income Tax)/ (all PDFs)
AMFI_MutualFunds      AMFI Scheme/ (PDFs + XLSX riskometers)

Collections inherited from the original spec (no local docs yet, but kept for
future uploads via MinIO / Celery):
  NSDL_CDSL_Demat, NSE_BSE_Market, PFRDA_NPS, IRDAI_Insurance,
  AA_Framework, Financial_Literacy
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Collection → local knowledge_base subfolder mapping
# ---------------------------------------------------------------------------

# Maps each Qdrant collection name to the relative subfolder inside
# ai/rag/knowledge_base/ that contains its source documents.
COLLECTION_FOLDER_MAP: dict[str, str] = {
    "SEBI_Regulations":  "SEBI Master Circulars",
    "RBI_Guidelines":    "RBI Master Directions",
    "CBDT_Tax":          "Taxation (CBDT & Income Tax)",
    "AMFI_MutualFunds":  "AMFI Scheme",
}

# Priority weights used during personalised retrieval scoring.
# Higher weight → collection boosted when user context matches.
COLLECTION_PRIORITY: dict[str, float] = {
    "SEBI_Regulations":  1.35,   # Priority 1 — 30-35 % of RAG
    "RBI_Guidelines":    1.20,   # Priority 2
    "CBDT_Tax":          1.15,   # Priority 3
    "AMFI_MutualFunds":  1.10,   # Priority 4
    "NSDL_CDSL_Demat":   1.05,   # Priority 5-6
    "NSE_BSE_Market":    1.00,   # Priority 9-10
    "PFRDA_NPS":         1.00,   # Priority 7
    "IRDAI_Insurance":   1.00,   # Priority 8
    "AA_Framework":      1.05,   # Priority 11
    "Financial_Literacy": 1.00,  # Priority 12
}

COLLECTIONS: list[str] = list(COLLECTION_PRIORITY.keys())

VECTOR_SIZE = 384  # all-MiniLM-L6-v2 (see rag/embeddings.py)

# ---------------------------------------------------------------------------
# Document-level metadata: title, priority, doc_type
# ---------------------------------------------------------------------------

DOCUMENT_REGISTRY: list[dict] = [
    # ── SEBI ─────────────────────────────────────────────────────────────────
    {"file": "SEBI Master Circular for Mutual Funds (March 20, 2026).pdf",
     "collection": "SEBI_Regulations", "priority": 1, "doc_type": "master_circular",
     "title": "SEBI Master Circular for Mutual Funds 2026"},
    {"file": "SEBI (Mutual Funds) Regulations, 1996 (as amended).pdf",
     "collection": "SEBI_Regulations", "priority": 1, "doc_type": "regulation",
     "title": "SEBI Mutual Funds Regulations 1996"},
    {"file": "SEBI Master Circular for Investment Advisers (2026).pdf",
     "collection": "SEBI_Regulations", "priority": 1, "doc_type": "master_circular",
     "title": "SEBI Master Circular for Investment Advisers 2026"},
    {"file": "SEBI Investor Charter.pdf",
     "collection": "SEBI_Regulations", "priority": 1, "doc_type": "charter",
     "title": "SEBI Investor Charter"},
    {"file": "SEBI SCORES User Manual (FAQs).pdf",
     "collection": "SEBI_Regulations", "priority": 1, "doc_type": "faq",
     "title": "SEBI SCORES User Manual and FAQs"},
    {"file": "SEBI Master Circular for Research Analysts (2026).pdf",
     "collection": "SEBI_Regulations", "priority": 1, "doc_type": "master_circular",
     "title": "SEBI Master Circular for Research Analysts 2026"},
    # ── RBI ──────────────────────────────────────────────────────────────────
    {"file": "Master Direction – Know Your Customer (KYC) Direction, 2016 (updated).pdf",
     "collection": "RBI_Guidelines", "priority": 2, "doc_type": "master_direction",
     "title": "RBI KYC Master Direction 2016"},
    {"file": "Digital Lending Guidelines & Master Directions.pdf",
     "collection": "RBI_Guidelines", "priority": 2, "doc_type": "master_direction",
     "title": "RBI Digital Lending Guidelines"},
    {"file": "Master Directions on Prepaid Payment Instruments (PPIs).pdf",
     "collection": "RBI_Guidelines", "priority": 2, "doc_type": "master_direction",
     "title": "RBI Master Directions on PPIs"},
    {"file": "Integrated Ombudsman Scheme, 2021 (updated).pdf",
     "collection": "RBI_Guidelines", "priority": 2, "doc_type": "scheme",
     "title": "RBI Integrated Ombudsman Scheme 2021"},
    {"file": "Master Direction – Non-Banking Financial Company – Account Aggregator (Reserve Bank) Directions, 2016 (updated).pdf",
     "collection": "RBI_Guidelines", "priority": 2, "doc_type": "master_direction",
     "title": "RBI Account Aggregator Master Direction 2016"},
    # ── CBDT / Income Tax ────────────────────────────────────────────────────
    {"file": "Income-tax Act, 1961.pdf",
     "collection": "CBDT_Tax", "priority": 3, "doc_type": "act",
     "title": "Income Tax Act 1961"},
    {"file": "Finance Act (Current FY).pdf",
     "collection": "CBDT_Tax", "priority": 3, "doc_type": "act",
     "title": "Finance Act Current FY"},
    {"file": "CBDT Circulars on Capital Gains & Securities Taxation --1.pdf",
     "collection": "CBDT_Tax", "priority": 3, "doc_type": "circular",
     "title": "CBDT Circulars on Capital Gains and Securities Taxation"},
    {"file": "Income Tax Department FAQs --1.pdf",
     "collection": "CBDT_Tax", "priority": 3, "doc_type": "faq",
     "title": "Income Tax Department FAQs Part 1"},
    {"file": "Income Tax Department FAQs --2.pdf",
     "collection": "CBDT_Tax", "priority": 3, "doc_type": "faq",
     "title": "Income Tax Department FAQs Part 2"},
    # ── AMFI ─────────────────────────────────────────────────────────────────
    {"file": "AMFI Best Practices Guidelines.pdf",
     "collection": "AMFI_MutualFunds", "priority": 4, "doc_type": "guidelines",
     "title": "AMFI Best Practices Guidelines"},
    {"file": "AMFI Scheme Classification Documents.pdf",
     "collection": "AMFI_MutualFunds", "priority": 4, "doc_type": "classification",
     "title": "AMFI Scheme Classification Documents"},
    {"file": "Riskometer - 2024- 2025.xlsx",
     "collection": "AMFI_MutualFunds", "priority": 4, "doc_type": "riskometer",
     "title": "AMFI Riskometer 2024-2025"},
    {"file": "Riskometer - 2025- 2026.xlsx",
     "collection": "AMFI_MutualFunds", "priority": 4, "doc_type": "riskometer",
     "title": "AMFI Riskometer 2025-2026"},
    {"file": "Riskometer - 2026 - 2027.xlsx",
     "collection": "AMFI_MutualFunds", "priority": 4, "doc_type": "riskometer",
     "title": "AMFI Riskometer 2026-2027"},
    {"file": "Riskometer- 2023- 2024.xlsx",
     "collection": "AMFI_MutualFunds", "priority": 4, "doc_type": "riskometer",
     "title": "AMFI Riskometer 2023-2024"},
]

# Quick lookup: filename → registry entry
DOCUMENT_REGISTRY_BY_FILE: dict[str, dict] = {
    d["file"]: d for d in DOCUMENT_REGISTRY
}


def ensure_collections(client) -> None:
    """Create all RAG collections if they don't already exist."""
    from qdrant_client.models import Distance, VectorParams  # type: ignore
    existing = {c.name for c in client.get_collections().collections}
    for name in COLLECTIONS:
        if name not in existing:
            client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
            )
