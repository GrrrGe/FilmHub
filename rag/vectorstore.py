"""Retriever factory — deploy-first.

Order:
1. Gemini embeddings + LangChain FAISS (light container, no torch). Needs GEMINI key.
2. Local MiniLM-L12-v2 via langchain-huggingface (offline dev, heavy).
3. Legacy storage.vector_db.MovieRetriever (existing index, no langchain).
4. None -> callers fall back to keyword search.
"""
import os
import logging

from . import config

logger = logging.getLogger(__name__)
_RETRIEVER = None


def _gemini_embeddings():
    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=config.EMBEDDING_MODEL, google_api_key=config.GEMINI_API_KEY
    )


def _local_embeddings():
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L12-v2")


def _build_lc_faiss(embeddings, docs):
    from langchain_community.vectorstores import FAISS

    if os.path.exists(os.path.join(config.FAISS_DIR, "index.faiss")):
        return FAISS.load_local(
            config.FAISS_DIR, embeddings, allow_dangerous_deserialization=True
        )
    vs = FAISS.from_documents(docs, embeddings)
    os.makedirs(config.FAISS_DIR, exist_ok=True)
    vs.save_local(config.FAISS_DIR)
    return vs


def get_retriever(k=8):
    """Returns (retriever, mode). Mode tells API what to report."""
    global _RETRIEVER
    if _RETRIEVER is not None:
        return _RETRIEVER.as_retriever(search_kwargs={"k": k}), "langchain-cached"

    from .documents import load_documents

    backend = config.EMBEDDINGS_BACKEND
    if backend == "auto":
        backend = "gemini" if config.GEMINI_API_KEY else "local"

    # 1/2: LangChain FAISS paths
    for attempt in ([backend] if backend in ("gemini", "local") else ["gemini", "local"]):
        try:
            if attempt == "gemini" and not config.GEMINI_API_KEY:
                continue
            emb = _gemini_embeddings() if attempt == "gemini" else _local_embeddings()
            docs = load_documents()
            if not docs:
                continue
            _RETRIEVER = _build_lc_faiss(emb, docs)
            logger.info(f"RAG retriever ready via {attempt} embeddings ({len(docs)} docs)")
            return _RETRIEVER.as_retriever(search_kwargs={"k": k}), f"langchain-{attempt}"
        except Exception as e:
            logger.warning(f"LangChain {attempt} retriever failed: {e}")

    # 3: legacy retriever (works without langchain / without API key if index exists)
    try:
        from storage.vector_db import movie_retriever_instance

        class _LegacyWrap:
            def __init__(self, inner):
                self.inner = inner

            def get_relevant_documents(self, q):
                from langchain_core.documents import Document

                out = []
                for r in self.inner.search(q, top_k=k):
                    out.append(
                        Document(
                            page_content=f"{r.get('Title','')} | {r.get('Genre','')}\n{r.get('Generated_Plot','')}",
                            metadata={
                                "title": r.get("Title", "Unknown"),
                                "plot": r.get("Generated_Plot", ""),
                                "poster": r.get("Poster-src", ""),
                                "cast": r.get("Star Cast", ""),
                                "director": r.get("Director", "N/A"),
                                "genre": r.get("Genre", "N/A"),
                                "year": r.get("Year", "N/A"),
                                "rating": r.get("IMDb Rating", "N/A"),
                            },
                        )
                    )
                return out

            def invoke(self, q):
                return self.get_relevant_documents(q)

        logger.info("RAG retriever: legacy MovieRetriever")
        return _LegacyWrap(movie_retriever_instance), "legacy"
    except Exception as e:
        logger.warning(f"Legacy retriever unavailable: {e}")

    return None, "keyword-only"
