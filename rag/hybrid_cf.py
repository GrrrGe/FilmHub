"""Hybrid CF-lite: item-item similarity from SQLite library ratings (BPR spirit).

No new deps. Falls back gracefully when data is thin (cold start -> content-only).
Blends: final = alpha * content_score + (1-alpha) * cf_score.
"""
import math
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def _all_ratings():
    """{user_id: {title: rating}} across every user in the library DB."""
    try:
        from storage import library_store

        with library_store._conn() as c:
            rows = c.execute("SELECT user_id, title, rating FROM watched WHERE rating IS NOT NULL").fetchall()
    except Exception as e:
        logger.warning(f"CF: cannot read ratings: {e}")
        return {}
    users = defaultdict(dict)
    for r in rows:
        try:
            users[r["user_id"]][r["title"]] = float(r["rating"])
        except Exception:
            continue
    return users


def item_similarities(target_items, users, min_overlap=1):
    """Cosine similarity between target items and all other items (mean-centered)."""
    means = {u: sum(r.values()) / len(r) for u, r in users.items() if r}
    # item -> {user: centered rating}
    centered = defaultdict(dict)
    for u, ratings in users.items():
        m = means[u]
        for t, v in ratings.items():
            centered[t][u] = v - m
    sims = defaultdict(float)
    for item in target_items:
        a = centered.get(item, {})
        if not a:
            continue
        na = math.sqrt(sum(v * v for v in a.values())) or 1.0
        for other, b in centered.items():
            if other == item or other in target_items:
                continue
            overlap = set(a) & set(b)
            if len(overlap) < min_overlap:
                continue
            num = sum(a[u] * b[u] for u in overlap)
            nb = math.sqrt(sum(b[u] ** 2 for u in overlap)) or 1.0
            sims[other] += num / (na * nb)
    return sims


def cf_scores_for_user(user_id, min_overlap=1):
    """{title: score} from users like you. Empty dict when too little data."""
    users = _all_ratings()
    mine = users.get(user_id, {})
    liked = [t for t, v in mine.items() if v >= 3.5]
    if not liked or len(users) < 2:
        return {}
    sims = item_similarities(liked, users, min_overlap=min_overlap)
    # weight by how much the neighbor item is liked globally
    return dict(sorted(sims.items(), key=lambda x: x[1], reverse=True)[:50])


def blend(content_titles_in_order, cf_scores, alpha=0.7):
    """Reorder content titles blending CF signal. Unknown CF titles appended by score."""
    if not cf_scores:
        return content_titles_in_order
    max_cf = max(abs(v) for v in cf_scores.values()) or 1.0
    ranked = []
    for i, t in enumerate(content_titles_in_order):
        content = 1.0 - (i / max(len(content_titles_in_order), 1))
        cf = cf_scores.get(t, 0.0) / max_cf
        ranked.append((alpha * content + (1 - alpha) * max(cf, 0.0), t))
    for t, v in cf_scores.items():
        if t not in content_titles_in_order and v > 0:
            ranked.append(((1 - alpha) * (v / max_cf), t))
    ranked.sort(reverse=True)
    return [t for _, t in ranked]
