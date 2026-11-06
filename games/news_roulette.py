from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.ui_components import change_page, load_local_image_as_base64


HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
_news_slot = components.declare_component("game1_news_slot", path=str(HERE / "news_slot"))

ART = {
    "background": "bet_background.jpg",
    "crown": "bet_crown.png",
    "cushion": "bank/bank_cushion.avif",
    "frame": "news_slot/news_slot_frame.webp",
    "lever": "news_slot/news_slot_lever.webp",
    "paper": "news_slot/news_row_paper.webp",
}


def render_news_slot(candidates):
    """Return a confirmed candidate index, or stay on the current selection screen."""
    state = st.session_state
    if "game_1_slot_round" not in state:
        state.game_1_slot_round = uuid4().hex
    round_id = state.game_1_slot_round

    with st.container(key="game1-news-stage"):
        st.html("""
            <style>
            .st-key-game1-news-stage {
                position: fixed; inset: 0; z-index: 1000;
                width: 100%; height: 100vh; height: 100dvh;
                background: #170824; overflow: hidden;
            }
            .st-key-game1-news-stage iframe {
                display: block; border: 0; width: 100%;
                height: 100vh !important; height: 100dvh !important;
            }
            [data-testid="stAppViewContainer"]:has(.st-key-game1-news-stage) [data-testid="stHeader"],
            [data-testid="stApp"]:has(.st-key-game1-news-stage) [data-testid="stHeader"] {
                display: none;
            }
            [data-testid="stMain"]:has(.st-key-game1-news-stage) { overflow: hidden; }
            </style>
        """)
        event = _news_slot(
            key=f"game_1_slot_{round_id}",
            round_id=round_id,
            continuous_reel=True,
            allow_back=False,
            titles=[item["title"] for item in candidates],
            coins=int((state.get("current_user_data") or {}).get("코인", 0)),
            art={name: load_local_image_as_base64(str(ASSETS / path)) for name, path in ART.items()},
            default=None,
        )

    if not isinstance(event, dict) or event.get("round_id") != round_id:
        return None
    action = event.get("action")
    if action == "choose":
        index = event.get("index")
        if type(index) is int and 0 <= index < len(candidates):
            del state["game_1_slot_round"]
            return index
    elif action == "bank":
        del state["game_1_slot_round"]
        change_page("bank")
    return None
