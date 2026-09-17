"""FilmHub RAG service (LangChain hybrid). See rag/ module docstrings."""
from .service import search, recommend, ask
from .chains import classify_intent

__all__ = ["search", "recommend", "ask", "classify_intent"]
