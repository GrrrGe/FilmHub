"""Single entry point used by FastAPI. Never raises (falls back to keyword)."""
import logging

from . import vectorstore, chains
from storage.movie_data_access import search_movies_by_keywords, get_movie_details
from storage import library_store

logger = logging.getLogger(__name__)


def _meta_to_ui(meta: dict) -> dict:
    return {
        "title": meta.get("title", "Unknown"),
        "plot": meta.get("plot", "No plot available."),
        "poster": meta.get("poster", ""),
        "genre": meta.get("genre", "N/A"),
        "year": meta.get("year", "N/A"),
        "rating": meta.get("rating", "N/A"),
        "cast": meta.get("cast", ""),
        "director": meta.get("director", "N/A"),
    }


def search(query: str, top_k=8):
    try:
        retriever, mode = vectorstore.get_retriever(k=top_k)
        if retriever is not None:
            docs = retriever.invoke(query) if hasattr(retriever, "invoke") else retriever.get_relevant_documents(query)
            results = [_meta_to_ui(d.metadata) for d in docs if hasattr(d, "metadata")]
            if results:
                return {"results": results, "mode": mode}
    except Exception as e:
        logger.warning(f"RAG search failed, keyword fallback: {e}")
    return {"results": search_movies_by_keywords(query, top_k=top_k), "mode": "keyword"}


def recommend(user_id: str, base="movies similar to my top rated films", top_k=5):
    liked = library_store.get_highly_rated(user_id) or library_store.get_all_liked_titles(user_id)
    disliked_rows = [m["title"] for m in library_store.get_library(user_id) if (m.get("rating") or 5) < 3.0]
    plots = {t: (get_movie_details(t) or {}).get("plot", "") for t in liked[:3]}
    q = chains.expand_query(base, liked, plots)
    try:
        retriever, mode = vectorstore.get_retriever(k=12)
        if retriever is not None:
            docs = retriever.invoke(q) if hasattr(retriever, "invoke") else retriever.get_relevant_documents(q)
            ranked = chains.rerank(docs, liked=liked, disliked=disliked_rows, top_k=top_k)
            return {
                "user_id": user_id,
                "based_on": liked[:5],
                "recommendations": [_meta_to_ui(d.metadata) for d in ranked],
                "mode": mode,
                "query": q[:200],
            }
    except Exception as e:
        logger.warning(f"RAG recommend failed, keyword fallback: {e}")
    # keyword fallback
    seen, out = set(), []
    for t in (liked[:3] or [base]):
        for m in search_movies_by_keywords(t, top_k=3):
            if m["title"] not in seen and m["title"] not in set(liked):
                seen.add(m["title"])
                out.append(m)
            if len(out) >= top_k:
                break
    return {"user_id": user_id, "based_on": liked[:5], "recommendations": out, "mode": "keyword"}


def ask(question: str, top_k=4):
    """Pure RAG QA: retrieve + 1 LLM call (or 0 if no key)."""
    from types import SimpleNamespace

    intent = chains.classify_intent(question)
    data = search(question, top_k=top_k)
    docs_ns = [
        SimpleNamespace(
            metadata={
                "title": m.get("title"), "plot": m.get("plot"),
                "year": m.get("year"), "genre": m.get("genre"),
            }
        )
        for m in data["results"]
    ]
    return {"intent": intent, "answer": chains.answer_question(question, docs_ns),
            "sources": data["results"], "mode": data.get("mode")}
