# FilmHub deploy (free tier, honest version)

Architecture: `filmhub-api` (FastAPI, Docker) + `filmhub-ui` (Gradio, Python).
UI talks to API via `FILMHUB_API_BASE`. No secrets are committed.

## 1) Push (done by agent, or run yourself)
```bash
git add -A
git commit -m "FilmHub: RAG hybrid + Render deploy configs"
gh repo create FilmHub --public --source=. --remote=origin --push
```

## 2) Render: New -> Blueprint -> select repo (uses render.yaml)
Render creates `filmhub-api` + `filmhub-ui`.

## 3) MUST-ADD secrets (Render Dashboard -> Environment)
On `filmhub-api`:
- `GEMINI_API_KEY` = get at https://aistudio.google.com/apikey
- `GOOGLE_API_KEY` = same value (legacy ADK reads this name)

Optional (only for official verified plots):
- `TMDB_API_KEY` = free at themoviedb.org (preferred) and/or `OMDB_API_KEY` = omdbapi.com
- Without these the app uses LLM `Generated_Plot`s; run `make enrich LIMIT=200` locally once keys exist, then `make index`.

Quality/hybrid knobs (defaults fine on free tier):
`MIN_IMDB=0, MIN_METASCORE=0, HYBRID_CF=1, CF_ALPHA=0.7`
Per-request too: `/recommend/{id}?exclude=Inception&min_rating=7&min_metascore=60`

Kept defaults (no action needed):
`RAG_EMBEDDINGS=gemini, RAG_CHAT_MODEL=gemini-1.5-flash, RAG_LLM_EXPAND=0, RAG_FAISS_DIR=/tmp/filmhub_lc_faiss, FILMHUB_DB=/tmp/filmhub_library.db`

On `filmhub-ui`:
- `FILMHUB_API_BASE` = `https://filmhub-api-XXXX.onrender.com` (copy from api service URL after first deploy, then redeploy UI)

## 4) Verify
- `https://<api>/` -> mode message
- `https://<api>/search?q=matrix`
- UI: search -> click poster -> rate -> My Library -> Recommend for me

## Free-tier caveats (will bite you)
- Sleeps after ~15 min idle. First load 30-60s.
- `/tmp` is ephemeral: FAISS cache + SQLite library wipe on restart. Expected on free.
- Gemini free quota: 429s under load. Search/recommend still work in `keyword` mode without key.
