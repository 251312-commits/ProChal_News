"""Game 1: music-synchronised, per-digit final score reveal.

All bets, model outputs and loan interest are settled before this view renders.
The browser component is presentation-only and never computes or changes payouts.
"""
from pathlib import Path
from random import randrange
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from modules.ui_components import change_page, load_local_image_url


RESULT_TRACKS = (
    ("result1.mp3", 9.7, 13.2, 48.5),
    ("result2.mp3", 13.2, 15.4, 31.6),
    ("result3.mp3", 8.7, 12.8, 43.1),
    ("result4.mp3", 8.9, 11.0, 24.6),
    ("result5.mp3", 9.7, 12.0, 27.9),
)
_SOUND_ROOT = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/sounds/"
_ASSETS = Path(__file__).resolve().parents[2] / "assets"
_COMPONENT = components.declare_component(
    "game1_result_reveal", path=str(Path(__file__).resolve().parent / "result_screen")
)

_ROUND_KEYS = (
    "game_1_bet", "selected_news_game_1", "candidates_game_1",
    "read_done_game_1", "game_1_round_id", "game_1_predicted_digits",
    "game_1_predicted_score", "game_1_result", "tens_val", "ones_val",
    "game1_pred_tens", "game1_pred_ones", "game1_pred_round_id",
    "game_1_summary_revealed", "game1_result_reveal_id",
    "game1_result_track_index",
)


def reveal_order(guess: int, answer: int) -> tuple[list[int], list[bool]]:
    """Reveal matching decimal positions first, without moving a digit's place."""
    predicted = f"{guess:02d}"
    actual = f"{answer % 100:02d}"
    matches = [predicted[i] == actual[i] for i in range(2)]
    ordered = [i for i in range(2) if matches[i]]
    ordered.extend(i for i in range(2) if not matches[i])
    return ordered, matches


def reset_game1_round() -> None:
    for key in _ROUND_KEYS:
        st.session_state.pop(key, None)


@st.fragment
def render_game1_result_reveal(res: dict) -> None:
    state = st.session_state
    if "game1_result_reveal_id" not in state:
        state.game1_result_reveal_id = uuid4().hex
    if "game1_result_track_index" not in state:
        state.game1_result_track_index = randrange(len(RESULT_TRACKS))
    reveal_id = state.game1_result_reveal_id
    filename, drop1, drop2, end = RESULT_TRACKS[state.game1_result_track_index]
    score_details = res.get("score_details") or {}
    units = score_details.get("score_hundredths")
    if units is None:
        units = round(float(res["actual_score"]) * 100)
    units = int(units)
    guess = int(res["predicted_digits"])
    order, matches = reveal_order(guess, units)
    # The stored per-round settlement remains authoritative; these are visual cues.
    # The credit balance is intentionally not shown until the result is revealed.
    user = state.get("current_user_data") or {}
    coins = int(user.get("코인", res.get("new_coins", 0)) or 0)
    art = {
        "background": load_local_image_url(str(_ASSETS / "bet_background.jpg")),
        "frame": load_local_image_url(str(_ASSETS / "game1_prediction/pred_frame.avif")),
        "news": load_local_image_url(str(_ASSETS / "game1_prediction/pred_news.avif")),
        "podium": load_local_image_url(str(_ASSETS / "bet_podium.png")),
    }
    model = {
        "name": str(score_details.get("model_name") or "BGE reranker"),
        "logit": score_details.get("logit"),
        "normalized": score_details.get("normalized"),
        "tokens": score_details.get("token_count"),
    }

    with st.container(key="game1-result-reveal-screen", gap=None):
        st.html("""
        <style>
        .st-key-game1-result-reveal-screen {
          position:fixed !important; inset:0 !important; z-index:1100 !important;
          width:100% !important; height:100vh !important; height:100dvh !important;
          overflow:hidden !important; background:#15071f;
        }
        .st-key-game1-result-reveal-screen iframe {
          display:block !important; border:0 !important;
          width:100% !important; height:100vh !important; height:100dvh !important;
        }
        [data-testid="stAppViewContainer"]:has(.st-key-game1-result-reveal-screen) [data-testid="stHeader"],
        [data-testid="stApp"]:has(.st-key-game1-result-reveal-screen) [data-testid="stHeader"] {
          display:none !important;
        }
        [data-testid="stMain"]:has(.st-key-game1-result-reveal-screen) { overflow:hidden !important; }
        </style>
        """)
        event = _COMPONENT(
            key="game1-result-reveal-" + reveal_id,
            round_id=reveal_id,
            title=str(res.get("title") or ""),
            summary=str(res.get("summary") or ""),
            guess=guess,
            units=units,
            reveal_order=order,
            matches=matches,
            win=bool(res.get("is_win")),
            reward=int(res.get("reward") or 0),
            coins=coins,
            streak=int(res.get("new_streak") or 0),
            track={"url": _SOUND_ROOT + filename, "name": filename,
                   "drop1": drop1, "drop2": drop2, "end": end},
            fail_url=_SOUND_ROOT + "fail.mp3",
            model=model,
            art=art,
            default=None,
        )
    if not isinstance(event, dict) or event.get("round_id") != reveal_id:
        return
    action = event.get("action")
    if action not in ("again", "home"):
        return
    reset_game1_round()
    if action == "home":
        change_page("main")
    else:
        st.rerun()
