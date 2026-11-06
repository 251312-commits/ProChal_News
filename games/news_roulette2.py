from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.ui_components import change_page, load_local_image_as_base64


HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
_news_slot = components.declare_component("game2_news_slot", path=str(HERE / "news_slot"))

ART = {
    "background": "bet_background.jpg",
    "crown": "bet_crown.png",
    "cushion": "bank/bank_cushion.avif",
    "frame": "news_slot/news_slot_frame.webp",
    "lever": "news_slot/news_slot_lever.webp",
    "paper": "news_slot/news_row_paper.webp",
}


def render_news_slot(candidates):
    """게임 2 전용 뉴스 슬롯 룰렛 화면 출력 및 선택 결과 반환"""
    state = st.session_state
    
    if "game_2_slot_round" not in state:
        state.game_2_slot_round = uuid4().hex
    round_id = state.game_2_slot_round

    titles_list = []
    for item in candidates:
        if isinstance(item, (list, tuple)):
            titles_list.append(item[0])
        elif isinstance(item, dict):
            titles_list.append(item.get("title", ""))
        else:
            titles_list.append(str(item))

    with st.container(key="game2-news-stage"):
        st.html("""
            <style>
            .st-key-game2-news-stage {
                position: fixed; inset: 0; z-index: 1000;
                width: 100%; height: 100vh; height: 100dvh;
                background: #170824; overflow: hidden;
            }
            .st-key-game2-news-stage iframe {
                display: block; border: 0; width: 100%;
                height: 100vh !important; height: 100dvh !important;
            }
            [data-testid="stAppViewContainer"]:has(.st-key-game2-news-stage) [data-testid="stHeader"],
            [data-testid="stApp"]:has(.st-key-game2-news-stage) [data-testid="stHeader"] {
                display: none;
            }
            [data-testid="stMain"]:has(.st-key-game2-news-stage) { overflow: hidden; }
            </style>
        """)
        event = _news_slot(
            key=f"game_2_slot_{round_id}",
            round_id=round_id,
            titles=titles_list,
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
            del state["game_2_slot_round"]
            return index
    elif action in ("back", "bank"):
        del state["game_2_slot_round"]
        if action == "back":
            state.pop("game_2_bet", None)
            st.rerun()
        else:
            change_page("bank")

    return None
