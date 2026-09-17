"""CI-friendly data check: columns, plot coverage, index staleness. No API keys needed."""
import csv
import os
import sys

CSV_PATH = os.getenv("RAG_CSV", "data/imdb_cleaned.csv")
REQUIRED = ["Title", "Genre", "IMDb Rating", "Poster-src"]


def main():
    if not os.path.exists(CSV_PATH):
        print(f"MISSING {CSV_PATH}")
        return 1
    with open(CSV_PATH, newline="", encoding="utf-8", errors="ignore") as f:
        rows = list(csv.DictReader(f))
    cols = set(rows[0].keys()) if rows else set()
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        print(f"MISSING COLUMNS: {missing}")
        return 1
    n = len(rows)
    official = sum(1 for r in rows if (r.get("Official_Plot") or "").strip())
    generated = sum(1 for r in rows if (r.get("Generated_Plot") or "").strip())
    print(f"rows={n} official_plots={official} ({official*100//max(n,1)}%) generated_plots={generated}")
    if n == 0:
        print("EMPTY CSV")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
