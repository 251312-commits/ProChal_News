"""Single-screen, asset-proportional Game 1 fractional prediction component.

The previous Streamlit grid/absolute-position CSS could be rewrapped on narrow
phones. This implementation uses the existing news-slot iframe architecture:
a single 100dvh document owns the full layout and native browser buttons.
Only 00-99 are submitted; Game 1's betting and scoring logic are unchanged.
"""
from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.ui_components import change_page, load_local_image_as_base64


_HERE = Path(__file__).resolve().parent
_ASSETS = _HERE.parent / "assets"
_SCREEN = components.declare_component(
    "game1_prediction_screen", path=str(_HERE / "prediction_screen")
)

_ART = {
    "background": "bet_background.jpg",
    "header": "game1_prediction/pred_header.avif",
    "news": "game1_prediction/pred_news.avif",
    "tag": "game1_prediction/pred_tag.avif",
    "frame": "game1_prediction/pred_frame.avif",
    "reel": "game1_prediction/pred_reel.avif",
    "podium": "bet_podium.png",
}


def _artwork() -> dict[str, str]:
    """Use the same cached local asset loader as the news selection screen."""
    return {
        key: load_local_image_as_base64(str(_ASSETS / filename))
        for key, filename in _ART.items()
    }


def _save_digits(values: object) -> bool:
    """Validate data from the iframe before updating the existing session keys."""
    if not isinstance(values, list) or len(values) != 2:
        return False
    if any(type(value) is not int or value < 0 or value > 9 for value in values):
        return False

    tens, ones = values
    st.session_state.game1_pred_tens = tens
    st.session_state.game1_pred_ones = ones
    st.session_state.tens_val = tens
    st.session_state.ones_val = ones
    return True


@st.fragment
def render_game1_prediction_picker(article_title: str) -> None:
    """Render the one-page UI. Confirm alone commits the prediction."""
    state = st.session_state
    if "game1_pred_tens" not in state:
        state.game1_pred_tens = int(state.get("tens_val", 0)) % 10
    if "game1_pred_ones" not in state:
        state.game1_pred_ones = int(state.get("ones_val", 4)) % 10
    if "game1_pred_round_id" not in state:
        state.game1_pred_round_id = uuid4().hex

    round_id = state.game1_pred_round_id
    user = state.get("current_user_data") or {}

    # Same full-viewport iframe shell already used in games/news_roulette.py.
    with st.container(key="game1-prediction-screen", gap=None):
        st.html("""
        <style>
        .st-key-game1-prediction-screen {
          position:fixed !important; inset:0 !important; z-index:1000 !important;
          width:100% !important; height:100vh !important; height:100dvh !important;
          overflow:hidden !important; background:#170824;
        }
        .st-key-game1-prediction-screen iframe {
          display:block !important; border:0 !important;
          width:100% !important; height:100vh !important; height:100dvh !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-game1-prediction-screen) [data-testid="stHeader"],
        [data-testid="stApp"]:has(.st-key-game1-prediction-screen) [data-testid="stHeader"] {
          display:none !important;
        }
        [data-testid="stMain"]:has(.st-key-game1-prediction-screen) {overflow:hidden !important;}
        </style>
        """)
        event = _SCREEN(
            key=f"game1-prediction-{round_id}",
            round_id=round_id,
            title=str(article_title or "선택된 뉴스가 없습니다"),
            coins=int(user.get("코인", 0) or 0),
            digits=[int(state.game1_pred_tens), int(state.game1_pred_ones)],
            art=_artwork(),
            default=None,
        )

    # Ignore stale or malformed messages (e.g. from an earlier round).
    if not isinstance(event, dict) or event.get("round_id") != round_id:
        return
    action = event.get("action")
    if action not in ("change", "confirm", "back", "bank"):
        return
    if not _save_digits(event.get("digits")):
        return

    if action == "confirm":
        state.game_1_predicted_digits = (
            int(state.game1_pred_tens) * 10 + int(state.game1_pred_ones)
        )
        state.pop("game1_pred_round_id", None)
        st.rerun()
    elif action == "back":
        change_page("main")
    elif action == "bank":
        change_page("bank")
    # 'change' is a lightweight synchronization event. Streamlit automatically
    # rerenders the fragment; the iframe keeps the local digits while doing so.
