"""FilmHub RAG service (LangChain hybrid). Lazy exports so submodules
(like rag.ranking) import without pulling pandas/faiss."""
__all__ = ["search", "recommend", "ask", "classify_intent"]


def __getattr__(name):
    if name in ("search", "recommend", "ask"):
        from . import service as _service

        return getattr(_service, name)
    if name == "classify_intent":
        from . import chains as _chains

        return _chains.classify_intent
    raise AttributeError(name)
