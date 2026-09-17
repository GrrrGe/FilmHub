"""Post-retrieval filtering + ranking shared by RAG and legacy ADK paths.

Score = semantic position prior + IMDb quality + MetaScore quality.
All pure-python, no LLM. Filters: exclude titles, min IMDb, min MetaScore.
"""
import logging
from typing import Iterable, List, Optional

logger = logging.getLogger(__name__)


def _f(x, default=0.0) -> float:
    try:
        v = float(str(x).strip())
        if v != v:  # NaN
            return default
        return v
    except Exception:
        return default


def _meta(d) -> dict:
    if hasattr(d, "metadata"):
        return d.metadata or {}
    if isinstance(d, dict):
        return d.get("metadata", d)
    return {}


def _title_of(d) -> str:
    m = _meta(d)
    return str(m.get("title", m.get("Title", "")))


def _imdb_of(d) -> float:
    m = _meta(d)
    return _f(m.get("rating", m.get("IMDb Rating", 0)))


def _meta_score_of(d) -> float:
    m = _meta(d)
    return _f(m.get("metascore", m.get("MetaScore", 0)))


def filter_and_rank(
    docs: Iterable,
    exclude: Optional[Iterable[str]] = None,
    min_imdb: float = 0.0,
    min_metascore: float = 0.0,
    top_k: int = 5,
    w_sem: float = 0.5,
    w_imdb: float = 0.35,
    w_meta: float = 0.15,
) -> List:
    """Exclude input/seen, apply quality floors, rerank by blended score."""
    excluded = set(exclude or [])
    scored = []
    docs = list(docs)
    n = max(len(docs), 1)
    for i, d in enumerate(docs):
        title = _title_of(d)
        if not title or title in excluded:
            continue
        imdb = _imdb_of(d)
        meta = _meta_score_of(d)
        if imdb < min_imdb or meta < min_metascore:
            continue
        sem = 1.0 - (i / n)  # retriever order as relevance prior
        score = w_sem * sem + w_imdb * (imdb / 10.0) + w_meta * (meta / 100.0)
        scored.append((score, d))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [d for _, d in scored[:top_k]]
