"""Lean chains: rule classifier + deterministic taste expansion + 1-LLM-call QA.

This is the tradeoff fix:
- OLD: every rec = manager LLM + critic LLM + recommender LLM (3 calls).
- NEW: search/rec = 0 LLM calls (retriever + rerank). ask = 1 LLM call.
  ADK chain stays only for free-form /chat.
"""
import re
import logging

from . import config

logger = logging.getLogger(__name__)

_INTENT_PATTERNS = {
    "rate": re.compile(r"\b(rate|rating|stars?|/5)\b", re.I),
    "recommend": re.compile(r"\b(recommend|suggest|like|similar|watch|for me)\b", re.I),
    "plot": re.compile(r"\b(plot|story|about|summary)\b", re.I),
    "cast": re.compile(r"\b(cast|actor|actress|director|stars? in)\b", re.I),
}


def classify_intent(message: str) -> str:
    m = message or ""
    if _INTENT_PATTERNS["rate"].search(m):
        return "rate"
    if _INTENT_PATTERNS["recommend"].search(m):
        return "recommend"
    if _INTENT_PATTERNS["plot"].search(m) or _INTENT_PATTERNS["cast"].search(m):
        return "factual"
    return "chat"  # ambiguous -> legacy ADK /chat path


def expand_query(base: str, liked_titles, plots_by_title=None) -> str:
    """Deterministic taste expansion. No LLM by default (RAG_LLM_EXPAND=0).

    Concatenates base + up to 3 liked titles (+ their plots if available)
    so the embedding query carries user taste without a critic call."""
    parts = [(base or "").strip()]
    for t in (liked_titles or [])[:3]:
        parts.append(t)
        if plots_by_title and plots_by_title.get(t):
            parts.append(str(plots_by_title[t])[:300])
    q = " ".join(p for p in parts if p).strip()
    if config.EXPAND_WITH_LLM and config.GEMINI_API_KEY and liked_titles:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=config.EXPAND_MODEL, google_api_key=config.GEMINI_API_KEY
            )
            resp = llm.invoke(
                "Summarize this user's movie taste in one sentence for vector search. "
                f"Base: {base}. Liked: {', '.join(liked_titles[:5])}"
            )
            return resp.content.strip() + " " + q
        except Exception as e:
            logger.warning(f"LLM expansion failed, using deterministic: {e}")
    return q or base


def _to_float(x, default=0.0):
    try:
        return float(str(x).strip())
    except Exception:
        return default


def rerank(docs, liked=None, disliked=None, top_k=5, exclude=None,
           min_imdb=0.0, min_metascore=0.0):
    """Filter seen/disliked + quality floors, rerank by semantic+IMDb+MetaScore.

    Backward-compatible: old callers pass liked/disliked only.
    `exclude` additionally filters the input movie (so recs never echo the query).
    """
    from . import ranking
    try:
        cfg_min_imdb = float(getattr(config, "MIN_IMDB", 0.0) or 0.0)
        cfg_min_meta = float(getattr(config, "MIN_METASCORE", 0.0) or 0.0)
    except Exception:
        cfg_min_imdb, cfg_min_meta = 0.0, 0.0
    return ranking.filter_and_rank(
        docs,
        exclude=set(liked or []) | set(disliked or []) | set(exclude or []),
        min_imdb=max(min_imdb, cfg_min_imdb),
        min_metascore=max(min_metascore, cfg_min_meta),
        top_k=top_k,
    )


def answer_question(question: str, docs) -> str:
    """Single-LLM-call RAG answer with citations. Fallback = extractive."""
    ctx = "\n\n".join(
        f"[{d.metadata.get('title')}] ({d.metadata.get('year')}, {d.metadata.get('genre')}) — {d.metadata.get('plot','')[:400]}"
        for d in docs[:5]
        if hasattr(d, "metadata")
    )
    if not config.GEMINI_API_KEY or not ctx.strip():
        # Extractive fallback (0 LLM calls, deploy-safe)
        lines = [
            f"**{d.metadata.get('title')}** ({d.metadata.get('year')}) — {d.metadata.get('plot','')[:220]}..."
            for d in docs[:3]
            if hasattr(d, "metadata")
        ]
        return "\n\n".join(lines) or "No matches in the local catalog."
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model=config.CHAT_MODEL, google_api_key=config.GEMINI_API_KEY
        )
        resp = llm.invoke(
            "Answer ONLY from the context. Cite movie titles. If unsure, say so.\n"
            f"Question: {question}\nContext:\n{ctx}"
        )
        return resp.content
    except Exception as e:
        logger.warning(f"RAG answer LLM failed: {e}")
        return ctx[:1500]
