"""Reusable full-screen article reader with a server-validated round event."""
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.ui_components import load_local_image_url


HERE = Path(__file__).resolve().parent
ASSETS = HERE.parents[1] / "assets"
_reader = components.declare_component("shared_article_reader", path=str(HERE / "article_reader"))

ART = {
    "background": "bet_background.jpg",
    "frame": "game1_article/reader-frame.webp",
}
for folder, names in {
    "art": ("bet-header", "chip-left", "chip-right", "sparkle-gold"),
    "chrome": ("article-divider", "guidance-panel", "predict-button",
               "news-label", "balance-pill", "reward-pill", "progress-track", "progress-fill"),
    "icons": ("coin", "add-balance", "die", "clipboard", "target", "reward-crown"),
}.items():
    ART.update({name: f"game1_article/{folder}/{name}.png" for name in names})


def _article_source(raw_url):
    url = str(raw_url or "").strip()
    try:
        parsed = urlsplit(url)
        if parsed.scheme in ("http", "https") and parsed.hostname:
            return url, parsed.hostname.removeprefix("www.")
    except ValueError:
        pass
    return "", ""


def render_article_reader(chosen, *, game_id="game_1", reward=None):
    """Render the current article and consume at most one navigation event."""
    state = st.session_state
    round_key = f"{game_id}_reader_round"
    if round_key not in state:
        state[round_key] = uuid4().hex
    round_id = state[round_key]
    url, source = _article_source(chosen.get("url"))
    user = state.get("current_user_data") or {}

    with st.container(key="shared-article-reader", gap=None):
        st.html("""
        <style>
        .st-key-shared-article-reader {
          position:fixed; inset:0; z-index:1000; width:100%; height:100vh;
          height:100dvh; overflow:hidden; background:#170824;
        }
        .st-key-shared-article-reader iframe {
          display:block; border:0; width:100%; height:100vh !important; height:100dvh !important;
        }
        [data-testid="stApp"]:has(.st-key-shared-article-reader) [data-testid="stHeader"] {display:none;}
        [data-testid="stMain"]:has(.st-key-shared-article-reader) {overflow:hidden;}
        </style>
        """)
        event = _reader(
            key=f"{game_id}-reader-{round_id}",
            round_id=round_id,
            title=chosen.get("title") or "제목 없는 기사",
            text=chosen.get("text") or "본문 내용을 가져올 수 없습니다.",
            image_url=chosen.get("image_url") or "",
            url=url,
            source=source,
            coins=int(user.get("코인", 0) or 0),
            reward=reward,
            art={name: load_local_image_url(str(ASSETS / path)) for name, path in ART.items()},
            default=None,
        )

    if isinstance(event, dict) and event.get("round_id") == round_id:
        action = event.get("action")
        if action in ("predict", "bank"):
            del state[round_key]
            return action
    return None


def render_game1_article(chosen, *, reward):
    """Legacy entrypoint retained for imports of games.game1_article_ui."""
    return render_article_reader(chosen, game_id="game_1", reward=reward)
