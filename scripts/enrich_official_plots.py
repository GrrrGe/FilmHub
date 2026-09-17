"""Fetch verified plots from TMDb (preferred) or OMDb and merge into imdb_cleaned.csv.

Adds/updates columns: Official_Plot, Plot_Source (tmdb|omdb), Plot_Updated.
Never overwrites without --overwrite. Safe without keys (dry-run mode).

Usage:
  python scripts/enrich_official_plots.py --limit 50 --dry-run
  TMDB_API_KEY=xxx python scripts/enrich_official_plots.py --limit 200
  OMDB_API_KEY=xxx python scripts/enrich_official_plots.py --source omdb --limit 200
"""
import argparse
import csv
import os
import sys
import time
import urllib.parse
import urllib.request
import json

CSV_PATH = os.getenv("RAG_CSV", "data/imdb_cleaned.csv")


def tmdb_search(title, year, api_key):
    q = urllib.parse.urlencode({"api_key": api_key, "query": title, "year": year or ""})
    url = f"https://api.themoviedb.org/3/search/movie?{q}"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("overview") or None


def omdb_plot(title, year, api_key):
    q = urllib.parse.urlencode({"apikey": api_key, "t": title, "y": year or "", "plot": "short"})
    url = f"http://www.omdbapi.com/?{q}"
    with urllib.request.urlopen(url, timeout=20) as r:
        data = json.load(r)
    if data.get("Response") == "True" and data.get("Plot", "N/A") != "N/A":
        return data["Plot"]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--source", choices=["tmdb", "omdb", "auto"], default="auto")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--csv", default=CSV_PATH)
    args = ap.parse_args()

    tmdb_key = os.getenv("TMDB_API_KEY", "")
    omdb_key = os.getenv("OMDB_API_KEY", "")
    if args.dry_run:
        print(f"DRY-RUN: would enrich up to {args.limit} rows in {args.csv} (no API calls).")
        return 0
    if args.source in ("tmdb", "auto") and not tmdb_key and args.source != "omdb":
        if args.source == "tmdb" or (args.source == "auto" and not omdb_key):
            print("Missing TMDB_API_KEY (get one free at themoviedb.org). Try --source omdb with OMDB_API_KEY.", file=sys.stderr)
            return 2

    with open(args.csv, newline="", encoding="utf-8", errors="ignore") as f:
        rows = list(csv.DictReader(f))
        fieldnames = list(rows[0].keys()) if rows else []
    for col in ("Official_Plot", "Plot_Source", "Plot_Updated"):
        if col not in fieldnames:
            fieldnames.append(col)

    done = new = 0
    for row in rows:
        if done >= args.limit:
            break
        if row.get("Official_Plot") and not args.overwrite:
            continue
        title, year = (row.get("Title") or "").strip(), (row.get("Year") or "").strip()
        if not title:
            continue
        plot, src = None, None
        try:
            if args.source in ("tmdb", "auto") and tmdb_key:
                plot = tmdb_search(title, year, tmdb_key)
                src = "tmdb" if plot else None
            if not plot and omdb_key:
                plot = omdb_plot(title, year, omdb_key)
                src = "omdb" if plot else src
        except Exception as e:
            print(f"  ! {title}: {e}")
            continue
        time.sleep(0.25)  # free-tier rate limits
        done += 1
        if plot:
            row["Official_Plot"] = plot.strip()
            row["Plot_Source"] = src or args.source
            row["Plot_Updated"] = time.strftime("%Y-%m-%d")
            new += 1
            print(f"  + {title} ({src})")

    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Done: checked {done}, enriched {new}. Rebuild index: make index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
