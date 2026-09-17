import uuid
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()

from storage.session_service import PersistentSessionService
from storage import library_store
from storage.movie_data_access import search_movies_by_keywords, get_movie_details

# NEW: LangChain RAG service (deterministic paths). Never raises at import.
try:
    from rag import service as rag_service
except Exception as e:
    print(f"RAG service unavailable ({e}) — using keyword fallbacks.")
    rag_service = None

try:
    from tools.movie_tools import recommend_movies as recommend_movies_tool
except Exception as e:
    print(f"Vector recommender unavailable ({e}) — /recommend falls back to keyword search.")
    recommend_movies_tool = None

# --- ADK runner is optional so the API stays deployable without a Gemini key ---
runner = None
try:
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        from google.adk.runners import Runner
        from google.genai import types as genai_types
        from manager_agent.agent import root_agent

        session_service = PersistentSessionService()
        runner = Runner(
            agent=root_agent,
            app_name="MovieChatbot",
            session_service=session_service,
        )
    else:
        from storage.session_service import PersistentSessionService as PSS

        session_service = PSS()
        print("No GEMINI/GOOGLE API key found — /chat will use fallback retrieval mode.")
except Exception as e:
    print(f"ADK init failed ({e}) — /chat will use fallback retrieval mode.")
    from storage.session_service import PersistentSessionService as PSS

    session_service = PSS()

# --- Application Setup ---
app = FastAPI(title="FilmHub API (MARS + personal library)")


# --- API Data Models ---
class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    session_id: str


class RateRequest(BaseModel):
    user_id: str
    title: str
    rating: float  # 1-5


class AskRequest(BaseModel):
    question: str
    top_k: int = 4


def _fallback_chat(message: str, user_id: str) -> str:
    """Simple retrieval answer when no LLM key is configured (good for deploy demo)."""
    hits = search_movies_by_keywords(message, top_k=3)
    if not hits:
        return (
            "I couldn't find that in the local catalog. Try a title, genre, or actor "
            "(e.g. 'sci-fi', 'Tarantino', 'The Matrix')."
        )
    lines = []
    for h in hits:
        lines.append(f"**{h['title']}** ({h['year']}) [{h['genre']}] — IMDb {h['rating']}\n{h['plot']}")
    liked = library_store.get_highly_rated(user_id)
    extra = f"\n\nBased on your {len(liked)} highly-rated movies, ask me for 'recommend something like ...'." if liked else ""
    return "\n\n---\n\n".join(lines) + extra


# --- API Endpoints ---
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    await session_service.create_session("MovieChatbot", request.user_id, request.session_id)

    if runner is None:
        return ChatResponse(
            response=_fallback_chat(request.message, request.user_id),
            session_id=request.session_id,
        )

    from google.genai import types

    message = types.Content(role="user", parts=[types.Part(text=request.message)])
    final_response = ""

    for event in runner.run(user_id=request.user_id, session_id=request.session_id, new_message=message):
        if event.is_final_response() and event.content:
            final_response = event.content.parts[0].text
            break

    return ChatResponse(response=final_response, session_id=request.session_id)


@app.get("/search")
def search(q: str = Query(..., min_length=1), top_k: int = 8):
    """RAG search (0 LLM calls): LangChain retriever -> rerank -> UI cards."""
    if rag_service is not None:
        try:
            return rag_service.search(q, top_k=top_k)
        except Exception as e:
            print(f"RAG search error: {e}")
    return {"results": search_movies_by_keywords(q, top_k=top_k), "mode": "keyword"}


@app.post("/ask")
def ask_rag(req: AskRequest):
    """Pure RAG QA: retrieve + max 1 LLM call (vs 2-3 via ADK /chat)."""
    if rag_service is not None:
        try:
            return rag_service.ask(req.question, top_k=req.top_k)
        except Exception as e:
            print(f"RAG ask error: {e}")
    hits = search_movies_by_keywords(req.question, top_k=req.top_k)
    return {"intent": "factual", "answer": "RAG unavailable, keyword hits shown.", "sources": hits, "mode": "keyword"}


@app.get("/movie")
def movie_details(title: str = Query(..., min_length=1)):
    """Single-movie details for the click-to-view modal."""
    details = get_movie_details(title)
    if not details:
        raise HTTPException(status_code=404, detail=f"No movie found for '{title}'")
    return {"movie": details}


@app.post("/rate")
def rate_movie(req: RateRequest):
    if not req.title.strip():
        raise HTTPException(status_code=400, detail="Empty title")
    if not (1.0 <= req.rating <= 5.0):
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    return library_store.rate_movie(req.user_id, req.title.strip(), rating=req.rating)


@app.get("/library/{user_id}")
def get_library(user_id: str):
    items = library_store.get_library(user_id)
    # Enrich with posters/plots so the UI can render directly
    enriched = []
    for it in items:
        d = get_movie_details(it["title"]) or {"title": it["title"]}
        enriched.append({**d, "user_rating": it.get("rating")})
    return {"user_id": user_id, "count": len(enriched), "movies": enriched}


@app.delete("/library/{user_id}")
def remove_from_library(user_id: str, title: str):
    return library_store.remove_movie(user_id, title)


@app.get("/recommend/{user_id}")
def recommend_personalized(user_id: str, base: str = "movies similar to my top rated films", top_k: int = 5,
                           exclude: str = "", min_rating: float = 0.0, min_metascore: float = 0.0):
    """RAG recs (0 LLM calls by default): taste expansion + retrieve + IMDb rerank.

    Filters: `exclude` (comma-separated, input movie auto-excluded), `min_rating`
    (IMDb floor), `min_metascore`. Hybrid CF blends in when 2+ users rated.
    Legacy ADK critic->recommender chain kept only inside /chat for conversation.
    Set RAG_LLM_EXPAND=1 to re-enable 1 LLM expansion call here."""
    if rag_service is not None:
        try:
            return rag_service.recommend(user_id, base=base, top_k=top_k,
                                         exclude=[e.strip() for e in exclude.split(",") if e.strip()],
                                         min_imdb=min_rating, min_metascore=min_metascore)
        except Exception as e:
            print(f"RAG recommend error: {e}")
    liked = library_store.get_highly_rated(user_id)
    if not liked:
        liked_all = library_store.get_all_liked_titles(user_id)
        liked = liked_all
    if recommend_movies_tool is None:
        # Fallback: keyword search on liked titles
        seen, out = set(), []
        for t in (liked[:3] or [base]):
            for m in search_movies_by_keywords(t, top_k=3):
                if m["title"] not in seen and m["title"] not in liked:
                    seen.add(m["title"])
                    out.append(m)
                if len(out) >= top_k:
                    break
        return {"user_id": user_id, "based_on": liked[:5], "recommendations": out, "mode": "fallback"}
    result = recommend_movies_tool(base_query=base, liked_movies=liked or None, user_id=user_id)
    recs = result.get("recommendations", [])[:top_k]
    # Normalize to UI-friendly details
    out = []
    for r in recs:
        out.append(
            {
                "title": r.get("Title", "Unknown"),
                "plot": r.get("Generated_Plot", "No plot available."),
                "poster": r.get("Poster-src", ""),
                "genre": r.get("Genre", "N/A"),
                "year": r.get("Year", "N/A"),
                "rating": r.get("IMDb Rating", "N/A"),
                "cast": r.get("Star Cast", ""),
                "director": r.get("Director", "N/A"),
            }
        )
    return {"user_id": user_id, "based_on": liked[:5], "recommendations": out}


@app.get("/")
def read_root():
    return {
        "message": "FilmHub API: /search (RAG, 0 LLM) | POST /ask (RAG, <=1 LLM) | /recommend/{id} (RAG, 0 LLM) | POST /chat (legacy ADK agents, 2-3 LLMs)."
    }
