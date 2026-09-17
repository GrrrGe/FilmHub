"""FilmHub UI — cinematic dark theme + personal library + clickable details."""
import gradio as gr
import requests
import uuid
import os

API_BASE = os.getenv("FILMHUB_API_BASE", "http://127.0.0.1:8000").rstrip("/")
if API_BASE and "://" not in API_BASE:
    API_BASE = f"https://{API_BASE}"
CHAT_URL = f"{API_BASE}/chat"

theme = gr.themes.Base(
    primary_hue="amber",
    secondary_hue="zinc",
    neutral_hue="zinc",
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
).set(
    body_background_fill="#0a0a0f",
    body_background_fill_dark="#0a0a0f",
    body_text_color="#f4f4f5",
    body_text_color_dark="#f4f4f5",
    block_background_fill="#131318",
    block_background_fill_dark="#131318",
    block_border_color="#27272a",
    block_border_color_dark="#27272a",
    button_primary_background_fill="#f59e0b",
    button_primary_background_fill_dark="#f59e0b",
    button_primary_text_color="#09090b",
    button_primary_text_color_dark="#09090b",
)

CSS = """
body, .gradio-container { background: #0a0a0f !important; }
.hero { background: linear-gradient(135deg, #1c0a00 0%, #431407 40%, #0a0a0f 100%);
  border: 1px solid #292524; border-radius: 16px; padding: 28px 32px; margin-bottom: 16px; }
.hero h1 { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.02em; margin: 0; }
.hero h1 span { color: #f59e0b; }
.hero p { color: #a1a1aa; margin: 6px 0 0 0; }
.stat-pill { display: inline-block; background: #1c1917; border: 1px solid #44403c;
  border-radius: 999px; padding: 4px 14px; font-size: 0.8rem; color: #e7e5e4; margin-right: 8px; }
.movie-card { background: #131318; border: 1px solid #27272a; border-radius: 14px; padding: 20px; }
.movie-card h2 { margin: 0 0 4px 0; font-size: 1.6rem; }
.badge { display: inline-block; border-radius: 8px; padding: 2px 10px; font-size: 0.78rem;
  font-weight: 600; margin: 2px 4px 2px 0; }
.b-imdb { background: #f59e0b; color: #09090b; }
.b-genre { background: #27272a; color: #fafafa; border: 1px solid #3f3f46; }
.b-year { background: transparent; color: #a1a1aa; border: 1px solid #3f3f46; }
.plot { color: #d4d4d8; line-height: 1.6; margin-top: 10px; }
.meta { color: #a1a1aa; font-size: 0.9rem; }
.meta b { color: #e4e4e7; }
.gallery img { border-radius: 12px !important; }
button.primary { font-weight: 700 !important; }
footer { display: none !important; }
"""

session_state = {"user_id": str(uuid.uuid4()), "session_id": str(uuid.uuid4())}
SEARCH_CACHE = []


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


def chat_fn(message, history):
    payload = {"user_id": session_state["user_id"], "session_id": session_state["session_id"], "message": message}
    try:
        r = requests.post(CHAT_URL, json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get("response", "Sorry, I encountered an error.")
    except Exception as e:
        return f"⚠️ Backend not reachable. Is the API running at {API_BASE}? ({e})"


def search_movies(query, min_rating):
    global SEARCH_CACHE
    query = (query or "").strip()
    if not query:
        return [], "Type a title, genre, actor or director above — or try a quick pick.", gr.update(choices=[], value=None)
    data = api_get("/search", {"q": query, "top_k": 12})
    if "error" in data:
        return [], f"⚠️ API error: {data['error']}", gr.update(choices=[], value=None)
    results = [m for m in data.get("results", []) if _num(m.get("rating")) >= (min_rating or 0)]
    SEARCH_CACHE = results
    if not results:
        return [], "No matches at that quality bar. Lower the IMDb filter or try another search.", gr.update(choices=[], value=None)
    gallery = [(m.get("poster") or None, f"{m['title']} ({m.get('year','')})") for m in results]
    choices = [m["title"] for m in results]
    return gallery, f"**{len(results)}** results for *{query}* — click a poster or pick below.", gr.update(choices=choices, value=choices[0])


def _num(x):
    try:
        return float(str(x).strip())
    except Exception:
        return 0.0


def _stars_badge(imdb):
    try:
        v = float(imdb)
        full = int(round(v / 2))
        return "★" * full + "☆" * (5 - full) + f" {v:.1f}"
    except Exception:
        return "N/A"


def show_details(title):
    m = next((x for x in SEARCH_CACHE if x["title"] == title), None)
    if not m:
        data = api_get("/movie", {"title": title or ""})
        m = data.get("movie") if isinstance(data, dict) else None
    if not m:
        return None, "<div class='movie-card'>Movie not found.</div>", ""
    html = f"""
    <div class="movie-card">
      <h2>{m.get('title','')}</h2>
      <div><span class="badge b-imdb">IMDb {m.get('rating','N/A')} {_stars_badge(m.get('rating'))}</span>
      <span class="badge b-genre">{m.get('genre','')}</span>
      <span class="badge b-year">{m.get('year','')} · {m.get('duration','?')} min</span></div>
      <p class="meta"><b>Director:</b> {m.get('director','N/A')}<br>
      <b>Cast:</b> {m.get('cast','N/A')}<br>
      <b>Plot source:</b> {m.get('plot_source','generated')}</p>
      <p class="plot">{m.get('plot','')}</p>
    </div>
    """
    return m.get("poster") or None, html, m.get("title", "")


def on_gallery_select(evt: gr.SelectData):
    idx = evt.index if isinstance(evt.index, int) else evt.index[0] if isinstance(evt.index, (list, tuple)) else 0
    try:
        m = SEARCH_CACHE[idx]
    except Exception:
        return None, "<div class='movie-card'>Select a movie again.</div>", ""
    return show_details(m["title"])


def save_rating(title, stars):
    if not title:
        return "Pick a movie first."
    res = api_post("/rate", {"user_id": session_state["user_id"], "title": title, "rating": float(stars)})
    if "error" in res:
        return f"⚠️ Error: {res['error']}"
    return f"✅ Saved **{title}** with **{stars}★** — it now steers your recommendations."


def load_library():
    data = api_get(f"/library/{session_state['user_id']}")
    if "error" in data:
        return f"⚠️ API error: {data['error']}", [], []
    movies = data.get("movies", [])
    if not movies:
        return "Your shelf is empty. Go to **Browse & Rate** and save a few films first.", [], []
    rows = [[m.get("title"), m.get("user_rating"), m.get("rating"), m.get("genre")] for m in movies]
    gallery = [(m.get("poster") or None, f"{m.get('title')} — {m.get('user_rating')}★") for m in movies]
    avg = sum(m.get("user_rating") or 0 for m in movies) / len(movies)
    return f"**{len(movies)}** watched · your avg **{avg:.1f}★**", rows, gallery


def recommend_for_me(min_rating):
    data = api_get(f"/recommend/{session_state['user_id']}", {"top_k": 8, "min_rating": min_rating})
    if "error" in data:
        return f"⚠️ API error: {data['error']}", []
    recs = data.get("recommendations", [])
    based = ", ".join(data.get("based_on", [])[:5]) or "nothing yet — rate 4-5★ movies first"
    if not recs:
        return f"Based on: {based}. No recs yet.", []
    gallery = [(m.get("poster") or None, f"{m['title']}") for m in recs]
    detail = f"**Based on:** {based}\n\n" + "\n\n".join(
        f"**{m['title']}** ({m.get('year')}) [{m.get('genre')}] · IMDb {m.get('rating')} — {m.get('plot','')[:220]}..." for m in recs
    )
    return detail, gallery


def chat_submit(message, history):
    try:
        if not (message or "").strip():
            return "", history
        return "", (history or []) + [[message, chat_fn(message, history)]]
    except Exception as e:
        return "", (history or []) + [[message or "", f"UI error: {e}"]]


with gr.Blocks(theme=theme, css=CSS, title="FilmHub — Personal Movie Recommender") as demo:
    gr.HTML(f"""<div class="hero"><h1>🎬 Film<span>Hub</span></h1>
    <p>Cinematic RAG recommender — search 3,173 films, rate what you've watched, get taste-aware picks.</p>
    <div style="margin-top:10px"><span class="stat-pill">📚 3,173 films</span>
    <span class="stat-pill">🤖 RAG + agents</span>
    <span class="stat-pill">👤 You: <code>{session_state['user_id'][:8]}</code></span></div></div>""")

    with gr.Tabs():
        with gr.Tab("💬 Chat"):
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(label="MovieBot", height=480)
                    msg = gr.Textbox(placeholder="Try: 'a dark comedy like Parasite' or 'plot of Dune'…", show_label=False)
                    msg.submit(chat_submit, [msg, chatbot], [msg, chatbot])
                with gr.Column(scale=1):
                    gr.Markdown("### ✨ Try")
                    for ex in ["Recommend a sci-fi like Inception", "Plot of The Matrix", "Best crime dramas above 8"]:
                        gr.Button(ex, size="sm").click(lambda x=ex: x, None, msg)

        with gr.Tab("🔎 Browse & Rate"):
            with gr.Row():
                q = gr.Textbox(placeholder="🔍 Title, genre, actor, director… e.g. Tarantino, sci-fi, The Matrix", scale=4, show_label=False)
                min_r = gr.Slider(0, 9, step=0.5, value=0, label="Min IMDb", scale=1)
                btn = gr.Button("Search", variant="primary", scale=1)
            gr.Markdown("**Quick picks:**")
            with gr.Row():
                for qp in ["comedy", "sci-fi", "crime", "Tarantino", "Nolan"]:
                    gr.Button(qp, size="sm").click(lambda x=qp: (x, 0), None, [q, min_r])
            status = gr.Markdown("")
            gallery = gr.Gallery(label="Results — click any poster", columns=4, height="auto", object_fit="cover")
            with gr.Row():
                with gr.Column(scale=1):
                    poster = gr.Image(label="Poster", height=420)
                with gr.Column(scale=2):
                    picker = gr.Dropdown(label="Or pick a title", choices=[])
                    details = gr.HTML()
                    with gr.Row():
                        stars = gr.Slider(1, 5, step=0.5, value=4.0, label="Your rating (★)")
                        save_btn = gr.Button("⭐ Save to my shelf", variant="primary")
                    save_msg = gr.Markdown("")
                    hidden_title = gr.Textbox(visible=False)
            btn.click(search_movies, [q, min_r], [gallery, status, picker])
            q.submit(search_movies, [q, min_r], [gallery, status, picker])
            picker.change(show_details, [picker], [poster, details, hidden_title])
            gallery.select(on_gallery_select, None, [poster, details, hidden_title])
            save_btn.click(save_rating, [hidden_title, stars], [save_msg])

        with gr.Tab("📚 My Shelf + For You"):
            gr.Markdown("Your ratings persist per session and re-rank every recommendation.")
            with gr.Row():
                lib_btn = gr.Button("↻ Load my shelf", variant="primary")
                rec_min = gr.Slider(0, 9, step=0.5, value=0, label="Min IMDb for recs")
                rec_btn = gr.Button("✨ Recommend for me")
            lib_md = gr.Markdown("")
            lib_table = gr.Dataframe(headers=["Title", "Your ★", "IMDb", "Genre"], label="Watched", wrap=True)
            lib_gallery = gr.Gallery(label="Your shelf", columns=5, object_fit="cover")
            rec_md = gr.Markdown("")
            rec_gallery = gr.Gallery(label="Recommended for you", columns=4, object_fit="cover")
            lib_btn.click(load_library, None, [lib_md, lib_table, lib_gallery])
            rec_btn.click(recommend_for_me, [rec_min], [rec_md, rec_gallery])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
