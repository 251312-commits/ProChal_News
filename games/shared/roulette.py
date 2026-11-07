"""Reusable news roulette screen for each game's article candidates.

Game 1 defaults to continuous spin and direct URL support; Game 2 retains its
return-to-bet behavior. Callers may override these presentation flags.
"""
from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.news_ai import bring_article
from modules.db_handler import (
    LAST_ARTICLE_HEADER,
    init_gspread,
    init_news_sheet,
    normalize_article_url,
    register_user_article,
    save_last_article_url,
)
from modules.news_preprocessing import SUPPORTED_NEWS_SITES, supported_news_site
from modules.ui_components import change_page, load_local_image_url


HERE = Path(__file__).resolve().parent
ASSETS = HERE.parents[1] / "assets"
_news_slot = components.declare_component("shared_news_slot", path=str(HERE / "news_slot"))

ART = {
    "background": "bet_background.jpg",
    "crown": "bet_crown.png",
    "cushion": "bank/bank_cushion.avif",
    "frame": "news_slot/news_slot_frame.webp",
    "lever": "news_slot/news_slot_lever.webp",
    "paper": "news_slot/news_row_paper.webp",
}


def _direct_keys(game_id):
    return f"{game_id}_direct_url_error", f"{game_id}_direct_url_request_id"


def _reject_direct_url(message, game_id="game_1"):
    error_key, _ = _direct_keys(game_id)
    st.session_state[error_key] = message
    st.rerun()
    return None


def _open_direct_url(raw_url, game_id="game_1"):
    state = st.session_state
    error_key, request_key = _direct_keys(game_id)
    url = str(raw_url or "").strip()
    newsroom = supported_news_site(url)
    if not newsroom:
        return _reject_direct_url(
            "올바르지 않은 URL입니다. 지원 언론사의 기사 URL을 입력해 주세요.", game_id
        )

    try:
        title, text, image_url = bring_article(url, include_image=True)
    except Exception:
        return _reject_direct_url(
            "기사 내용을 불러올 수 없습니다. 지원 언론사의 기사 상세 페이지 URL인지 확인해 주세요.", game_id
        )

    title = str(title or "").strip()
    text = str(text or "").strip()
    if not title or len("".join(text.split())) < 40:
        return _reject_direct_url(
            "기사 내용을 확인할 수 없습니다. 기사 상세 페이지 URL을 입력해 주세요.", game_id
        )

    canonical = normalize_article_url(url)
    user = state.get("current_user_data") or {}
    submitter_id = str(state.get("current_user") or user.get("학번") or "").strip().removesuffix(".0")
    submitter_name = str(user.get("아이디") or "").strip()
    try:
        register_user_article(
            init_news_sheet(),
            url=canonical,
            title=title,
            submitter_id=submitter_id,
            submitter_name=submitter_name,
        )
    except Exception:
        return _reject_direct_url(
            "기사는 읽었지만 뉴스풀에 저장하지 못했습니다. 잠시 후 다시 시도해 주세요.", game_id
        )

    if isinstance(user, dict):
        user[LAST_ARTICLE_HEADER] = canonical
    try:
        save_last_article_url(init_gspread(), submitter_id, canonical)
    except Exception:
        # The article can still be used this round; session history prevents
        # an immediate repeat even if the persistent metadata write is unavailable.
        pass

    state[f"selected_news_{game_id}"] = {
        "title": title, "text": text, "url": canonical,
        "image_url": str(image_url or "").strip(), "newsroom": newsroom,
    }
    state.pop(f"candidates_{game_id}", None)
    state.pop(error_key, None)
    state.pop(request_key, None)
    state.pop(f"{game_id}_slot_round", None)
    st.rerun()
    return None


def _titles(candidates):
    result = []
    for item in candidates:
        if isinstance(item, dict):
            result.append(str(item.get("title", "")))
        elif isinstance(item, (list, tuple)):
            result.append(str(item[0]) if item else "")
        else:
            result.append(str(item))
    return result


def render_news_slot(
    candidates, *, game_id="game_1", allow_back=None,
    continuous_reel=None, allow_direct_url=None,
):
    """Return a valid chosen index, otherwise await the next component event."""
    if allow_back is None:
        allow_back = game_id != "game_1"
    if continuous_reel is None:
        continuous_reel = game_id == "game_1"
    if allow_direct_url is None:
        allow_direct_url = game_id == "game_1"

    state = st.session_state
    round_key = f"{game_id}_slot_round"
    error_key, request_key = _direct_keys(game_id)
    if round_key not in state:
        state[round_key] = uuid4().hex
    round_id = state[round_key]

    with st.container(key="shared-news-stage"):
        st.html("""
        <style>
        .st-key-shared-news-stage {
            position:fixed; inset:0; z-index:1000;
            width:100%; height:100vh; height:100dvh;
            overflow:hidden; background:#170824;
        }
        .st-key-shared-news-stage iframe {
            display:block; border:0; width:100%;
            height:100vh !important; height:100dvh !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-shared-news-stage) [data-testid="stHeader"],
        [data-testid="stApp"]:has(.st-key-shared-news-stage) [data-testid="stHeader"] {display:none;}
        [data-testid="stMain"]:has(.st-key-shared-news-stage) {overflow:hidden;}
        </style>
        """)
        event = _news_slot(
            key=f"{game_id}-slot-{round_id}",
            round_id=round_id,
            titles=_titles(candidates),
            continuous_reel=bool(continuous_reel),
            allow_back=bool(allow_back),
            allow_direct_url=bool(allow_direct_url),
            coins=int((state.get("current_user_data") or {}).get("코인", 0)),
            supported_sources=list(SUPPORTED_NEWS_SITES) if allow_direct_url else [],
            direct_url_error=str(state.get(error_key, "") or "") if allow_direct_url else "",
            direct_url_error_id=str(state.get(request_key, "") or "") if allow_direct_url else "",
            art={name: load_local_image_url(str(ASSETS / path)) for name, path in ART.items()},
            default=None,
        )

    if not isinstance(event, dict) or event.get("round_id") != round_id:
        return None
    action = event.get("action")
    if action == "choose":
        index = event.get("index")
        if type(index) is int and 0 <= index < len(candidates):
            state.pop(round_key, None)
            state.pop(error_key, None)
            state.pop(request_key, None)
            return index
    elif action == "direct_url" and allow_direct_url:
        request_id = str(event.get("request_id") or "").strip()
        if not request_id or state.get(request_key) == request_id:
            return None
        state[request_key] = request_id
        return _open_direct_url(event.get("url"), game_id)
    elif action == "back" and allow_back:
        state.pop(round_key, None)
        state.pop(f"{game_id}_bet", None)
        st.rerun()
    elif action == "bank":
        state.pop(round_key, None)
        state.pop(error_key, None)
        state.pop(request_key, None)
        change_page("bank")
    return None
