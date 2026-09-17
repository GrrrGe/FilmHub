"""FilmHub RAG config — deploy-friendly defaults."""
import os

# LLM: keep Gemini (existing key). Flash for QA, Pro only for optional taste expansion.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
CHAT_MODEL = os.getenv("RAG_CHAT_MODEL", "gemini-1.5-flash")
EXPAND_MODEL = os.getenv("RAG_EXPAND_MODEL", "gemini-1.5-flash")

# Embeddings for deploy: 'gemini' (default) = API-based, no torch download,
# small image + fast cold start on Render/HF free tier.
# 'local' = MiniLM-L12-v2, free/offline but ~400MB torch + slow cold start.
EMBEDDINGS_BACKEND = os.getenv("RAG_EMBEDDINGS", "gemini").lower()  # gemini|local|auto
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "models/text-embedding-004")

# 1 = allow an LLM call to expand taste into a search query (like old critic agent).
# 0 (default) = deterministic expansion from liked titles. Saves 1 LLM call per rec.
EXPAND_WITH_LLM = os.getenv("RAG_LLM_EXPAND", "0") == "1"

# Post-retrieval quality floors (0 = off). Also settable per-request.
MIN_IMDB = float(os.getenv("MIN_IMDB", "0") or 0)
MIN_METASCORE = float(os.getenv("MIN_METASCORE", "0") or 0)

# Hybrid CF blend: 1 = content-only, 0.7 default when CF data exists.
HYBRID_CF = os.getenv("HYBRID_CF", "1") == "1"
CF_ALPHA = float(os.getenv("CF_ALPHA", "0.7") or 0.7)
CF_MIN_OVERLAP = int(os.getenv("CF_MIN_OVERLAP", "1") or 1)

CSV_PATH = os.getenv("RAG_CSV", "data/imdb_cleaned.csv")
FAISS_DIR = os.getenv("RAG_FAISS_DIR", "vectorstore/filmhub_lc_faiss")
