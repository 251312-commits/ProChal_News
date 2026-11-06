from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.news_ai import bring_article
from modules.news_preprocessing import SUPPORTED_NEWS_SITES, supported_news_site
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

_DIRECT_ERROR_KEY = "game_1_direct_url_error"
_DIRECT_REQUEST_KEY = "game_1_direct_url_request_id"


def _reject_direct_url(message):
    st.session_state[_DIRECT_ERROR_KEY] = message
    st.rerun()
    return None


def _open_direct_url(raw_url):
    state = st.session_state
    url = str(raw_url or "").strip()
    newsroom = supported_news_site(url)
    if not newsroom:
        return _reject_direct_url(
            "올바르지 않은 URL입니다. 지원 언론사의 기사 URL을 입력해 주세요."
        )

    try:
        title, text, image_url = bring_article(url, include_image=True)
    except Exception:
        return _reject_direct_url(
            "기사 내용을 불러올 수 없습니다. 지원 언론사의 기사 상세 페이지 URL인지 확인해 주세요."
        )

    title = str(title or "").strip()
    text = str(text or "").strip()
    if not title or len("".join(text.split())) < 40:
        return _reject_direct_url(
            "기사 내용을 확인할 수 없습니다. 기사 상세 페이지 URL을 입력해 주세요."
        )

    state["selected_news_game_1"] = {
        "title": title,
        "text": text,
        "url": url,
        "image_url": str(image_url or "").strip(),
        "newsroom": newsroom,
    }
    state.pop("candidates_game_1", None)
    state.pop(_DIRECT_ERROR_KEY, None)
    state.pop(_DIRECT_REQUEST_KEY, None)
    state.pop("game_1_slot_round", None)
    st.rerun()
    return None


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
            supported_sources=list(SUPPORTED_NEWS_SITES),
            direct_url_error=str(state.get(_DIRECT_ERROR_KEY, "") or ""),
            direct_url_error_id=str(state.get(_DIRECT_REQUEST_KEY, "") or ""),
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
            state.pop(_DIRECT_ERROR_KEY, None)
            state.pop(_DIRECT_REQUEST_KEY, None)
            return index
    elif action == "direct_url":
        request_id = str(event.get("request_id") or "").strip()
        if not request_id or state.get(_DIRECT_REQUEST_KEY) == request_id:
            return None
        state[_DIRECT_REQUEST_KEY] = request_id
        return _open_direct_url(event.get("url"))
    elif action == "bank":
        del state["game_1_slot_round"]
        state.pop(_DIRECT_ERROR_KEY, None)
        state.pop(_DIRECT_REQUEST_KEY, None)
        change_page("bank")
    return None
