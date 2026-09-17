import pandas as pd
import logging
from typing import Optional, Dict, List

try:
    # Make sure the CSV file is located at 'data/imdb_cleaned.csv'
    MOVIE_DATA = pd.read_csv("data/imdb_cleaned.csv")
    logging.info("✅ IMDb data loaded successfully for data access.")
except Exception as e:
    logging.error(f"❌ Failed to load IMDb data: {e}")
    MOVIE_DATA = pd.DataFrame()


def _row_to_details(row) -> dict:
    """Full movie details for UI cards / modals. Poster comes from dataset."""
    def safe(col, default="N/A"):
        try:
            v = row.get(col, default)
            if v is None or (isinstance(v, float) and str(v) == "nan"):
                return default
            if isinstance(v, float) and col in ("Year", "Duration (minutes)"):
                return str(int(v))
            return v
        except Exception:
            return default

    raw_cast = safe("Star Cast", "")
    return {
        "title": safe("Title", "Unknown"),
        "plot": safe("Generated_Plot", "No plot available."),
        "poster": safe("Poster-src", ""),
        "cast": str(raw_cast),
        "director": safe("Director", "N/A"),
        "genre": safe("Genre", "N/A"),
        "year": safe("Year", "N/A"),
        "rating": safe("IMDb Rating", "N/A"),
        "metascore": safe("MetaScore", "N/A"),
        "duration": safe("Duration (minutes)", "N/A"),
        "certificates": safe("Certificates", "N/A"),
    }


def get_movie_details(title: str) -> Optional[Dict]:
    """Exact-then-fuzzy lookup returning full details for the UI modal."""
    if MOVIE_DATA.empty or not title:
        return None
    t = title.strip().lower()
    exact = MOVIE_DATA[MOVIE_DATA['Title'].str.strip().str.lower() == t]
    match = exact if not exact.empty else MOVIE_DATA[
        MOVIE_DATA['Title'].str.strip().str.lower().str.contains(t, na=False)
    ]
    if match.empty:
        return None
    return _row_to_details(match.iloc[0])


def search_movies_by_keywords(query: str, top_k: int = 5) -> list:
    """
    Keyword-based search across Title, Genre, Star Cast, and Director.
    Now returns FULL details (poster, plot, cast...) so the UI can
    render clickable cards without a second lookup.
    """
    if MOVIE_DATA.empty:
        logging.warning("⚠️ No movie data available for search.")
        return []

    query_lower = query.lower()
    
    # --- FIX 1: Using column names from your dataset sample ---
    matches = MOVIE_DATA[
        MOVIE_DATA['Title'].str.strip().str.lower().str.contains(query_lower, na=False) |
        MOVIE_DATA['Genre'].str.strip().str.lower().str.contains(query_lower, na=False) |
        MOVIE_DATA['Star Cast'].str.strip().str.lower().str.contains(query_lower, na=False) |
        MOVIE_DATA['Director'].str.strip().str.lower().str.contains(query_lower, na=False)
    ]

    results = []
    for _, row in matches.head(top_k).iterrows():
        results.append(_row_to_details(row))
    return results


def get_rating_by_title(title: str) -> dict:
    """
    Retrieve rating and votes for a movie title using a flexible search.
    """
    if MOVIE_DATA.empty:
        return None

    title_lower = title.lower()
    
    match = MOVIE_DATA[MOVIE_DATA['Title'].str.strip().str.lower().str.contains(title_lower, na=False)]

    if match.empty:
        return None

    row = match.iloc[0]

    rating = row.get("IMDb Rating", "N/A")
    votes = "N/A" # Your sample did not include a votes column

    return {
        "rating": rating,
        "votes": votes
    }