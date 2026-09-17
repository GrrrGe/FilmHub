"""Rebuild the LangChain FAISS index with the current embedding model.

Usage:
  python scripts/build_index.py
  RAG_EMBEDDINGS=local RAG_FAISS_DIR=vectorstore/filmhub_lc_local python scripts/build_index.py
  RAG_EMBEDDING_MODEL=models/text-embedding-004 RAG_FAISS_DIR=vectorstore/filmhub_lc_gemini python scripts/build_index.py

Tip: point RAG_FAISS_DIR at a model-specific dir when experimenting with
larger models (e.g. e5-large, bge-base) so indexes never mismatch dims.
"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag import config
from rag.documents import load_documents
from rag.vectorstore import _gemini_embeddings, _local_embeddings

try:
    from langchain_community.vectorstores import FAISS
except Exception as e:
    print(f"langchain-community not installed: {e}")
    raise SystemExit(2)


def main():
    backend = config.EMBEDDINGS_BACKEND if config.EMBEDDINGS_BACKEND in ("gemini", "local") else (
        "gemini" if config.GEMINI_API_KEY else "local")
    print(f"Building index: backend={backend} model={config.EMBEDDING_MODEL} docs={config.CSV_PATH}")
    emb = _gemini_embeddings() if backend == "gemini" else _local_embeddings()
    docs = load_documents()
    print(f"Loaded {len(docs)} documents (official plots preferred).")
    if os.path.exists(config.FAISS_DIR):
        shutil.rmtree(config.FAISS_DIR)
    vs = FAISS.from_documents(docs, emb)
    os.makedirs(config.FAISS_DIR, exist_ok=True)
    vs.save_local(config.FAISS_DIR)
    print(f"Saved to {config.FAISS_DIR}. Set RAG_FAISS_DIR to this path on deploy.")


if __name__ == "__main__":
    main()
