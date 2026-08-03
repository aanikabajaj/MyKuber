"""Financial Advisor — LangGraph node that calls Qwen3-8B via vLLM.

The LLM ONLY generates natural-language explanations. It NEVER computes
portfolio weights, tax amounts, or any numerical financial result.

Personalisation
---------------
build_system_prompt() now uses the full user_context assembled by the
Context Manager, which includes:
  - User account fields from the IAARE backend (city, state, risk_band,
    face_enabled, totp_enabled, txn_face_threshold, account_number_masked,
    balance_bucket, preferred_language, registration_stage)
  - AI financial profile (risk_profile, investment_goals, holdings,
    sip_details, investment_horizon_years, preferred_asset_classes)
  - Recent transaction summary
  - Conversation history summary
"""
from __future__ import annotations

import asyncio
from pydantic import BaseModel
from openai import AsyncOpenAI
from fastapi import HTTPException

from ai.core.config import settings
from ai.orchestrator.state import OrchestratorState


class LLMOutput(BaseModel):
    text: str
    tokens_used: int
    confidence: float


def _extract_confidence(response) -> float:
    """Extract confidence from logprobs if available, else default 0.7."""
    try:
        logprobs = response.choices[0].logprobs
        if logprobs and hasattr(logprobs, "content") and logprobs.content:
            import math
            avg_logprob = sum(t.logprob for t in logprobs.content) / len(logprobs.content)
            return max(0.0, min(1.0, math.exp(avg_logprob)))
    except Exception:
        pass
    return 0.7


# ---------------------------------------------------------------------------
# Rich personalised system prompt
# ---------------------------------------------------------------------------

def build_system_prompt(user_context: dict) -> str:
    """Build a fully personalised LLM system prompt from the assembled context.

    Uses every available field from the IAARE backend user record and the
    AI financial profile stored in AI_PostgreSQL.
    """
    user    = user_context.get("user", {})
    profile = user_context.get("financial_profile", {})
    txns    = user_context.get("transactions", [])

    # ── Identity ─────────────────────────────────────────────────────────────
    first_name  = user.get("first_name") or "Valued Customer"
    city        = user.get("city") or ""
    state_name  = user.get("state") or ""
    location    = f"{city}, {state_name}".strip(", ") if city or state_name else "India"

    # ── Account status ────────────────────────────────────────────────────────
    balance_bucket   = user.get("balance_bucket", "unknown")
    account_masked   = user.get("account_number_masked", "****0000")
    face_enabled     = user.get("face_enabled", False)
    totp_enabled     = user.get("totp_enabled", False)
    txn_threshold    = user.get("txn_face_threshold", 10000)
    preferred_lang   = user.get("preferred_language", "en")

    # ── Financial profile ─────────────────────────────────────────────────────
    risk_profile  = profile.get("risk_profile", "moderate")
    risk_band     = user.get("risk_band") or risk_profile
    horizon       = profile.get("investment_horizon_years", 5)
    goals         = profile.get("investment_goals") or []
    holdings      = profile.get("holdings") or []
    sip_details   = profile.get("sip_details") or []
    asset_classes = profile.get("preferred_asset_classes") or []

    # ── Build goal / holding summaries ────────────────────────────────────────
    goals_str    = ", ".join(str(g) for g in goals[:5]) if goals else "Not specified"
    holdings_str = ", ".join(str(h) for h in holdings[:5]) if holdings else "None on record"
    sip_str      = f"{len(sip_details)} active SIP(s)" if sip_details else "No SIPs"
    assets_str   = ", ".join(str(a) for a in asset_classes[:4]) if asset_classes else "Not specified"

    # ── Account security context (useful for KYC / security questions) ────────
    security_factors = []
    if face_enabled:
        security_factors.append("Face ID")
    if totp_enabled:
        security_factors.append("TOTP authenticator")
    security_str = " and ".join(security_factors) if security_factors else "standard password"

    # ── Transaction activity summary ──────────────────────────────────────────
    recent_count  = len(txns)
    credit_count  = sum(1 for t in txns if (t.get("amount") or 0) > 0)
    debit_count   = recent_count - credit_count
    txn_summary   = (
        f"{recent_count} recent transactions "
        f"({credit_count} credits, {debit_count} debits)"
        if recent_count > 0 else "No recent transaction history"
    )

    # ── Conversation history ──────────────────────────────────────────────────
    conv_summary = user_context.get("conversation_summary", "")

    # ── Language instruction ──────────────────────────────────────────────────
    lang_instruction = ""
    if preferred_lang and preferred_lang.lower() != "en":
        lang_instruction = (
            f"\nIMPORTANT: Respond in {preferred_lang}. "
            f"If you cannot produce a fluent response in that language, "
            f"respond in English and prepend: "
            f"'[Note: Response in English — {preferred_lang} not fully supported]'"
        )

    prompt = f"""You are a SEBI-compliant personal financial advisor for {first_name}, \
a Punjab & Sind Bank customer located in {location}.

── ACCOUNT PROFILE ──────────────────────────────────────────────────────────
Account (masked):     {account_masked}
Approximate balance:  {balance_bucket}
Security methods:     {security_str}
Face-ID txn limit:    ₹{txn_threshold:,} and above require biometric step-up
Preferred language:   {preferred_lang}
{lang_instruction}

── INVESTMENT PROFILE ───────────────────────────────────────────────────────
Risk band:            {risk_band}  (self-declared: {risk_profile})
Investment horizon:   {horizon} year(s)
Financial goals:      {goals_str}
Current holdings:     {holdings_str}
SIP activity:         {sip_str}
Preferred assets:     {assets_str}

── RECENT ACTIVITY ──────────────────────────────────────────────────────────
{txn_summary}

── CONVERSATION CONTEXT ─────────────────────────────────────────────────────
{conv_summary if conv_summary else "New conversation — no prior history."}

── CRITICAL RULES (non-negotiable) ──────────────────────────────────────────
1. You MUST NOT perform any mathematical calculations.
   Only interpret and explain pre-computed results provided to you.
2. You MUST cite SEBI / RBI / CBDT / AMFI / IRDAI / PFRDA regulatory sources
   whenever you mention a financial product, regulation, or tax rule.
3. NEVER invent returns, yields, or numerical projections.
4. ALWAYS tailor advice to this user's risk band, goals, and holdings above.
5. For any KYC / security query, reference the user's existing security setup.
6. When the user asks about complaints, reference SEBI SCORES or RBI Ombudsman.
7. Append the SEBI disclaimer if you discuss expected returns without a
   corresponding deterministic result from the Portfolio Service.
"""
    return prompt


# ---------------------------------------------------------------------------
# vLLM client
# ---------------------------------------------------------------------------

_vllm_client: AsyncOpenAI | None = None


def get_vllm_client() -> AsyncOpenAI:
    global _vllm_client
    if _vllm_client is None:
        _vllm_client = AsyncOpenAI(base_url=settings.VLLM_BASE_URL, api_key=settings.VLLM_API_KEY)
    return _vllm_client


async def generate_response(system_prompt: str, user_prompt: str) -> LLMOutput:
    client = get_vllm_client()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=settings.VLLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                max_tokens=1024,
                temperature=0.2,
                timeout=15.0,
            ),
            timeout=15.0,
        )
        text         = response.choices[0].message.content or ""
        tokens_used  = response.usage.total_tokens if response.usage else 0
        confidence   = _extract_confidence(response)
        return LLMOutput(text=text, tokens_used=tokens_used, confidence=confidence)
    except Exception as e:
        import httpx
        if isinstance(e, (asyncio.TimeoutError, httpx.ConnectError)):
            raise HTTPException(
                status_code=503,
                detail={"error_code": "LLM_UNAVAILABLE", "message": str(e)},
            )
        raise HTTPException(
            status_code=503,
            detail={"error_code": "LLM_UNAVAILABLE", "message": str(e)},
        )


# ---------------------------------------------------------------------------
# LangGraph node
# ---------------------------------------------------------------------------

async def financial_advisor_node(state: OrchestratorState) -> dict:
    user_context = state.get("user_context", {})
    raw_query    = state.get("raw_query", "")

    system_prompt = build_system_prompt(user_context)

    # Build user prompt: query + pre-computed service results
    parts = [raw_query]
    if state.get("portfolio_result"):
        parts.append(f"\n[Portfolio analysis result]\n{state['portfolio_result']}")
    if state.get("analytics_result"):
        parts.append(f"\n[Transaction analytics result]\n{state['analytics_result']}")
    if state.get("rag_result"):
        rag_citations = state["rag_result"]
        if isinstance(rag_citations, list) and rag_citations:
            citation_text = "\n".join(
                f"• [{c.get('collection','?')}] {c.get('document_title','?')}: "
                f"{c.get('text','')[:300]}"
                for c in rag_citations[:3]
            )
            parts.append(f"\n[Regulatory context retrieved]\n{citation_text}")

    user_prompt = "\n".join(parts)

    # Retrieve personalised regulatory context if RAG result not already in state
    if not state.get("rag_result"):
        try:
            from ai.rag.retrieval import retrieve_for_user  # noqa: PLC0415
            chunks = await retrieve_for_user(raw_query, user_context, top_k=4)
            if chunks:
                state["rag_result"] = [c.model_dump() for c in chunks]
                citation_text = "\n".join(
                    f"• [{c.collection}] {c.document_title}: {c.text[:300]}"
                    for c in chunks[:3]
                )
                user_prompt += f"\n\n[Regulatory context retrieved]\n{citation_text}"
        except Exception:
            pass  # RAG failure is non-fatal

    preferred_lang = user_context.get("user", {}).get("preferred_language", "en")
    output = await generate_response(system_prompt, user_prompt)

    # Language fallback detection
    if preferred_lang and preferred_lang.lower() != "en":
        try:
            from langdetect import detect  # type: ignore
            detected = detect(output.text)
            if detected == "en":
                output = LLMOutput(
                    text=(
                        f"[Note: Response in English — "
                        f"'{preferred_lang}' not fully supported]\n\n{output.text}"
                    ),
                    tokens_used=output.tokens_used,
                    confidence=output.confidence,
                )
        except Exception:
            pass

    return {
        "llm_response":   output.text,
        "llm_confidence": output.confidence,
    }
