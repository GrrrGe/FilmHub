"""SQLite-backed personal library: watched movies + 1-5 star ratings.

This is the NEW FilmHub layer (not in the original MARS repo).
Persists per-user so recommendations can use it even after restart,
unlike the original in-memory session profile.
"""
import sqlite3
import os
import time
from typing import List, Dict, Optional

DB_PATH = os.environ.get("FILMHUB_DB", "data/filmhub_library.db")


def _conn():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS watched (
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                rating REAL,
                liked INTEGER,
                updated_at REAL,
                PRIMARY KEY (user_id, title)
            )
            """
        )


init_db()


def rate_movie(user_id: str, title: str, rating: Optional[float] = None) -> dict:
    """Add/update a watched movie with a 1-5 star rating."""
    title = (title or "").strip()
    if not title:
        return {"status": "error", "message": "Empty title"}
    if rating is not None:
        rating = max(1.0, min(5.0, float(rating)))
    liked = None
    if rating is not None:
        liked = 1 if rating >= 3.5 else 0
    with _conn() as c:
        c.execute(
            """INSERT INTO watched (user_id, title, rating, liked, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id, title) DO UPDATE SET
                 rating=excluded.rating, liked=excluded.liked, updated_at=excluded.updated_at""",
            (user_id, title, rating, liked, time.time()),
        )
    return {"status": "success", "user_id": user_id, "title": title, "rating": rating}


def remove_movie(user_id: str, title: str) -> dict:
    with _conn() as c:
        c.execute("DELETE FROM watched WHERE user_id=? AND title=?", (user_id, title))
    return {"status": "success"}


def get_library(user_id: str) -> List[Dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT title, rating, liked, updated_at FROM watched WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_highly_rated(user_id: str, min_rating: float = 4.0) -> List[str]:
    with _conn() as c:
        rows = c.execute(
            "SELECT title FROM watched WHERE user_id=? AND rating>=? ORDER BY rating DESC",
            (user_id, min_rating),
        ).fetchall()
    return [r["title"] for r in rows]


def get_all_liked_titles(user_id: str) -> List[str]:
    with _conn() as c:
        rows = c.execute(
            "SELECT title FROM watched WHERE user_id=? AND (liked=1 OR rating>=3.5)",
            (user_id,),
        ).fetchall()
    return [r["title"] for r in rows]
