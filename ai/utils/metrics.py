from prometheus_client import Counter, Histogram

ai_request_total = Counter(
    "ai_request_total",
    "Total AI requests",
    ["endpoint", "status"],
)

ai_request_duration = Histogram(
    "ai_request_duration_seconds",
    "Request duration",
    ["endpoint"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 15, 20, 30],
)

ai_llm_tokens_total = Counter(
    "ai_llm_tokens_total",
    "Total LLM tokens consumed",
)

ai_rag_retrieval_duration = Histogram(
    "ai_rag_retrieval_duration_seconds",
    "RAG retrieval latency",
    buckets=[0.1, 0.5, 1, 2, 5],
)

ai_cache_hit_total = Counter(
    "ai_cache_hit_total",
    "Redis cache hits",
    ["cache_type"],
)
