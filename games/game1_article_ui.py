from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.ui_components import load_local_image_as_base64


HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
_reader = components.declare_component("game1_article_reader", path=str(HERE / "article_reader"))

ART = {
    "background": "bet_background.jpg",
    "frame": "game1_article/reader-frame.webp",
    "news": "game1_guide/news.webp",
}
for folder, names in {
    "art": ("bet-header", "chip-left", "chip-right", "stage-ring", "sparkle-gold", "article-ai-copyright"),
    "chrome": ("article-divider", "guidance-panel", "predict-button", "read-button",
               "news-label", "balance-pill", "reward-pill", "progress-track", "progress-fill"),
    "icons": ("back", "coin", "add-balance", "die", "clipboard", "target", "book", "reward-crown"),
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


def render_game1_article(chosen, *, reward):
    """Render the current article and consume at most one navigation event."""
    state = st.session_state
    if "game1_reader_round" not in state:
        state.game1_reader_round = uuid4().hex
    round_id = state.game1_reader_round
    url, source = _article_source(chosen.get("url"))
    user = state.get("current_user_data") or {}

    with st.container(key="game1-article-reader", gap=None):
        st.html("""
        <style>
        .st-key-game1-article-reader {
          position:fixed; inset:0; z-index:1000; width:100%; height:100vh;
          height:100dvh; overflow:hidden; background:#170824;
        }
        .st-key-game1-article-reader iframe {
          display:block; border:0; width:100%; height:100vh !important; height:100dvh !important;
        }
        [data-testid="stApp"]:has(.st-key-game1-article-reader) [data-testid="stHeader"] {display:none;}
        [data-testid="stMain"]:has(.st-key-game1-article-reader) {overflow:hidden;}
        </style>
        """)
        event = _reader(
            key=f"game1-reader-{round_id}",
            round_id=round_id,
            title=chosen.get("title") or "제목 없는 기사",
            text=chosen.get("text") or "본문 내용을 가져올 수 없습니다.",
            url=url,
            source=source,
            coins=int(user.get("코인", 0) or 0),
            reward=reward,
            art={name: load_local_image_as_base64(str(ASSETS / path)) for name, path in ART.items()},
            default=None,
        )

    if isinstance(event, dict) and event.get("round_id") == round_id:
        action = event.get("action")
        if action in ("predict", "back", "bank"):
            del state["game1_reader_round"]
            return action
    return None
