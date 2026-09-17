"""CSV -> LangChain Documents. No LLM here, pure mapping."""
import csv

from . import config


def _safe(row, col, default="N/A"):
    v = row.get(col, default)
    if v is None or (isinstance(v, str) and v.strip().lower() in ("", "nan", "none")):
        return default
    return str(v).strip()


def load_documents(limit=None):
    """Page content = plot + genre (same signal as old vector_db, but explicit).
    Metadata carries everything the UI needs so chains don't re-read CSV."""
    docs = []
    try:
        from langchain_core.documents import Document
    except Exception:
        # langchain not installed (deploy slim / tests) — return raw dicts
        Document = None

    with open(config.CSV_PATH, newline="", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if limit and i >= limit:
                break
            title = _safe(row, "Title", "Unknown")
            plot = row.get("Generated_Plot") or "No plot available."
            genre = _safe(row, "Genre", "N/A")
            page = f"{title} | {genre}\n{plot}"
            meta = {
                "title": title,
                "plot": plot,
                "poster": _safe(row, "Poster-src", ""),
                "cast": _safe(row, "Star Cast", ""),
                "director": _safe(row, "Director", "N/A"),
                "genre": genre,
                "year": _safe(row, "Year", "N/A"),
                "rating": _safe(row, "IMDb Rating", "N/A"),
                "metascore": _safe(row, "MetaScore", "N/A"),
                "duration": _safe(row, "Duration (minutes)", "N/A"),
            }
            if Document:
                docs.append(Document(page_content=page, metadata=meta))
            else:
                docs.append({"page_content": page, "metadata": meta})
    return docs
