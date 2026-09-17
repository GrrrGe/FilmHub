"""FilmHub UI — MARS chatbot + personal watched/rated library + clickable movie details."""
import gradio as gr
import requests
import uuid
import os

API_BASE = os.getenv("FILMHUB_API_BASE", "http://127.0.0.1:8000").rstrip("/")
if API_BASE and "://" not in API_BASE:
    API_BASE = f"https://{API_BASE}"
CHAT_URL = f"{API_BASE}/chat"

theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="sky",
    neutral_hue="slate",
    font=[gr.themes.GoogleFont("Readex Pro"), "ui-sans-serif", "system-ui", "sans-serif"],
)

session_state = {"user_id": str(uuid.uuid4()), "session_id": str(uuid.uuid4())}
SEARCH_CACHE = []  # last search results for detail lookup


def api_get(path, params=None, timeout=20):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def api_post(path, payload, timeout=20):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ---------- Chat ----------
def chat_fn(message, history):
    payload = {
        "user_id": session_state["user_id"],
        "session_id": session_state["session_id"],
        "message": message,
    }
    try:
        r = requests.post(CHAT_URL, json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get("response", "Sorry, I encountered an error.")
    except Exception as e:
        return f"Backend not reachable ({e}). Start it with: uvicorn main:app --reload"


# ---------- Browse / details ----------
def search_movies(query):
    global SEARCH_CACHE
    if not query.strip():
        return [], "Type a title, genre, actor or director to search.", gr.update(choices=[], value=None)
    data = api_get("/search", {"q": query, "top_k": 12})
    if "error" in data:
        return [], f"API error: {data['error']}", gr.update(choices=[], value=None)
    results = data.get("results", [])
    SEARCH_CACHE = results
    if not results:
        return [], "No matches. Try another title/genre.", gr.update(choices=[], value=None)
    gallery = [(m.get("poster") or None, f"{m['title']} ({m.get('year','')})") for m in results]
    choices = [m["title"] for m in results]
    return gallery, f"Found {len(results)} movies. Click a poster, or pick from the dropdown to see details.", gr.update(
        choices=choices, value=choices[0]
    )


def show_details(title):
    m = next((x for x in SEARCH_CACHE if x["title"] == title), None)
    if not m:
        data = api_get("/movie", {"title": title or ""})
        m = data.get("movie") if isinstance(data, dict) else None
    if not m:
        return None, "Movie not found.", ""
    html = f"""
    <h2>{m.get('title','')}</h2>
    <p><b>{m.get('year','')} · {m.get('genre','')} · IMDb {m.get('rating','N/A')} · {m.get('duration','')} min</b><br>
    <b>Director:</b> {m.get('director','N/A')}<br>
    <b>Cast:</b> {m.get('cast','N/A')}<br>
    <b>Certificate:</b> {m.get('certificates','N/A')}</p>
    <p>{m.get('plot','')}</p>
    """
    return m.get("poster") or None, html, m.get("title", "")


def on_gallery_select(evt: gr.SelectData):
    idx = evt.index if isinstance(evt.index, int) else evt.index[0] if isinstance(evt.index, (list, tuple)) else 0
    try:
        m = SEARCH_CACHE[idx]
    except Exception:
        return None, "Select a movie again.", ""
    return show_details(m["title"])


def save_rating(title, stars):
    if not title:
        return "Pick a movie first."
    res = api_post("/rate", {"user_id": session_state["user_id"], "title": title, "rating": float(stars)})
    if "error" in res:
        return f"Error: {res['error']}"
    return f"Saved '{title}' with {stars}★. It will now steer your recommendations."


# ---------- Library / personalized ----------
def load_library():
    data = api_get(f"/library/{session_state['user_id']}")
    if "error" in data:
        return f"API error: {data['error']}", [], []
    movies = data.get("movies", [])
    if not movies:
        return "No watched movies yet. Rate something in Browse & Rate.", [], []
    rows = [[m.get("title"), m.get("user_rating"), m.get("rating"), m.get("genre")] for m in movies]
    gallery = [(m.get("poster") or None, f"{m.get('title')} — {m.get('user_rating')}★") for m in movies]
    md = f"**{len(movies)} watched** · avg your-rating: {sum(m.get('user_rating') or 0 for m in movies)/len(movies):.1f}★"
    return md, rows, gallery


def recommend_for_me():
    data = api_get(f"/recommend/{session_state['user_id']}", {"top_k": 8})
    if "error" in data:
        return f"API error: {data['error']}", []
    recs = data.get("recommendations", [])
    based = ", ".join(data.get("based_on", [])[:5]) or "nothing yet — rate 4-5★ movies first"
    if not recs:
        return f"Based on: {based}. No recs yet.", []
    gallery = [(m.get("poster") or None, f"{m['title']}") for m in recs]
    detail = f"**Based on:** {based}\n\n" + "\n\n".join(
        f"**{m['title']}** ({m.get('year')}) [{m.get('genre')}] — {m.get('plot','')[:220]}..." for m in recs
    )
    return detail, gallery


def chat_submit(message, history):
    """Tuple-format chat (pinned gradio 4.x). Never raises into Gradio 'Error'."""
    try:
        if not (message or "").strip():
            return "", history
        reply = chat_fn(message, history)
        history = (history or []) + [[message, reply]]
        return "", history
    except Exception as e:
        history = (history or []) + [[message or "", f"UI error: {e}"]]
        return "", history


with gr.Blocks(theme=theme, title="FilmHub — Personal Movie Recommender") as demo:
    gr.Markdown(
        f"# 🎬 FilmHub\nYour multi-agent assistant + personal library. Your ID: `{session_state['user_id'][:8]}...`"
    )

    with gr.Tabs():
        with gr.Tab("💬 Chat"):
            chatbot = gr.Chatbot(label="MovieBot", height=450)
            msg = gr.Textbox(placeholder="Ask for a plot, rating, or 'recommend like Inception'...")
            msg.submit(chat_submit, [msg, chatbot], [msg, chatbot])

        with gr.Tab("🔎 Browse & Rate"):
            gr.Markdown("Search the catalog, **click a movie to see poster / summary / cast**, then give it your own 1–5★ rating.")
            with gr.Row():
                q = gr.Textbox(placeholder="e.g. The Matrix, sci-fi, Tarantino...", scale=4)
                btn = gr.Button("Search", variant="primary", scale=1)
            status = gr.Markdown("")
            gallery = gr.Gallery(label="Results (click a poster)", columns=4, height="auto")
            with gr.Row():
                with gr.Column(scale=1):
                    poster = gr.Image(label="Poster", height=380)
                with gr.Column(scale=2):
                    picker = gr.Dropdown(label="Pick movie for details", choices=[])
                    details = gr.HTML()
                    with gr.Row():
                        stars = gr.Slider(1, 5, step=0.5, value=4.0, label="Your rating (★)")
                        save_btn = gr.Button("⭐ Save watched + rating", variant="primary")
                    save_msg = gr.Markdown("")
                    hidden_title = gr.Textbox(visible=False)
            btn.click(search_movies, [q], [gallery, status, picker])
            q.submit(search_movies, [q], [gallery, status, picker])
            picker.change(show_details, [picker], [poster, details, hidden_title])
            gallery.select(on_gallery_select, None, [poster, details, hidden_title])
            save_btn.click(save_rating, [hidden_title, stars], [save_msg])

        with gr.Tab("📚 My Library + For You"):
            gr.Markdown("Movies **you watched + rated** steer all future recommendations (persisted in SQLite).")
            with gr.Row():
                lib_btn = gr.Button("↻ Load my library", variant="primary")
                rec_btn = gr.Button("✨ Recommend for me")
            lib_md = gr.Markdown("")
            lib_table = gr.Dataframe(headers=["Title", "Your ★", "IMDb", "Genre"], label="Watched")
            lib_gallery = gr.Gallery(label="Your shelf", columns=5)
            rec_md = gr.Markdown("")
            rec_gallery = gr.Gallery(label="Recommended for you", columns=4)
            lib_btn.click(load_library, None, [lib_md, lib_table, lib_gallery])
            rec_btn.click(recommend_for_me, None, [rec_md, rec_gallery])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
