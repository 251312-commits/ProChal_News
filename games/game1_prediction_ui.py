"""Mobile-first two-digit similarity prediction for Game 1.

Buttons are ordinary Streamlit widgets so they work with touch, mouse and
keyboard. Only the 00-99 fractional digits are submitted to the game logic.
"""
from html import escape
from pathlib import Path

import streamlit as st

from modules.ui_components import change_page, load_local_image_as_base64


_ASSETS = Path(__file__).resolve().parents[1] / "assets"


def _asset(relative_name: str) -> str:
    path = _ASSETS / relative_name
    if not path.is_file():
        return ""
    return load_local_image_as_base64(str(path))


def _change_digit(name: str, delta: int) -> None:
    """Cycle exactly one fractional digit without submitting the prediction."""
    if name not in ("tens", "ones"):
        raise ValueError("Unknown Game 1 digit")
    key = f"game1_pred_{name}"
    next_value = (int(st.session_state.get(key, 0)) + delta) % 10
    st.session_state[key] = next_value
    # Keep the legacy keys synchronized for resumed rounds and the result flow.
    st.session_state[f"{name}_val"] = next_value


@st.fragment
def render_game1_prediction_picker(article_title: str) -> None:
    """Show the accessible two-reel selector; only confirmation commits a score."""
    if "game1_pred_tens" not in st.session_state:
        st.session_state.game1_pred_tens = int(st.session_state.get("tens_val", 0)) % 10
    if "game1_pred_ones" not in st.session_state:
        st.session_state.game1_pred_ones = int(st.session_state.get("ones_val", 4)) % 10

    tens = int(st.session_state.game1_pred_tens) % 10
    ones = int(st.session_state.game1_pred_ones) % 10
    st.session_state.tens_val = tens
    st.session_state.ones_val = ones

    user = st.session_state.get("current_user_data") or {}
    balance = int(user.get("코인", 0) or 0)
    headline = escape(str(article_title or "선택된 뉴스가 없습니다"), quote=True)

    banner = _asset("game1_prediction/pred_header.avif")
    tag = _asset("game1_prediction/pred_tag.avif")
    news_plate = _asset("game1_prediction/pred_news.avif")
    frame = _asset("game1_prediction/pred_frame.avif")
    reel = _asset("game1_prediction/pred_reel.avif")
    podium = _asset("bet_podium.png")
    background = _asset("bet_background.jpg")

    # Only decorative art goes in backgrounds. NEVER hide arrow button text:
    # these are real clickable buttons, not part of the reel illustration.
    asset_css = [
        (".stApp:has(.st-key-game1-prediction) {"
         f"background:#13051e url('{background}') center center/cover no-repeat !important;"
         "}") if background else "",
        f".st-key-game1-prediction-machine {{ background-image:url('{frame}') !important; }}" if frame else "",
        f".game1-pred-news-wrap {{ background-image:url('{news_plate}') !important; }}" if news_plate else "",
        (".st-key-game1-pred-reel-tens,.st-key-game1-pred-reel-ones {"
         f"background-image:url('{reel}') !important;"
         "}") if reel else "",
    ]

    with st.container(key="game1-prediction", gap=None):
        st.html(Path(__file__).with_suffix(".css"))
        st.html("<style>" + "\n".join(asset_css) + "</style>")

        # Native Streamlit columns provide three real, stable hit targets.
        # CSS keeps them side by side even on narrow mobile viewports.
        with st.container(key="game1-prediction-nav", gap=None):
            back_col, wallet_col, bank_col = st.columns([1, 5, 1], gap=None, vertical_alignment="center")
            with back_col:
                if st.button("❮", key="game1-pred-back", help="메인으로 돌아가기"):
                    change_page("main")
            with wallet_col:
                st.html(
                    '<div class="game1-pred-wallet" aria-label="보유 코인 '
                    f'{balance:,} C">'
                    '<span class="game1-pred-wallet-coin" aria-hidden="true">₵</span>'
                    f'<span class="game1-pred-wallet-amount">{balance:,} C</span></div>'
                )
            with bank_col:
                if st.button("+", key="game1-pred-bank", help="은행으로 이동"):
                    change_page("bank")

        st.html(
            '<section class="game1-pred-heading" aria-label="유사도 예측">'
            + (f'<img class="game1-pred-banner" src="{banner}" alt="SIMILARITY PREDICT">'
               if banner else '<span class="game1-pred-banner-fallback">♛ SIMILARITY PREDICT</span>')
            + '<h1>유사도 예측</h1>'
            + '<p>선택한 기사 제목과 AI 요약문의<br>유사도 점수 소수 두 자리를 예측하세요.</p>'
            + '</section>'
        )

        st.html(
            '<section class="game1-pred-news-wrap" aria-label="선택한 뉴스">'
            + (f'<img class="game1-pred-news-tag" src="{tag}" alt="선택한 뉴스">'
               if tag else '<span class="game1-pred-news-tag-fallback">선택한 뉴스</span>')
            + f'<div class="game1-pred-news-title" title="{headline}">{headline}</div>'
            + '</section>'
        )

        with st.container(key="game1-prediction-machine", gap=None):
            st.html('<div class="game1-pred-machine-title">✦ 예측하는 유사도 점수 ✦</div>')
            with st.container(key="game1-prediction-reels", gap=None):
                zero_col, tens_col, ones_col = st.columns([0.7, 1, 1], gap=None, vertical_alignment="center")
                with zero_col:
                    st.html('<span class="game1-pred-zero" aria-hidden="true">0.</span>')
                for name, value, label, column in (
                    ("tens", tens, "첫째 자리", tens_col),
                    ("ones", ones, "둘째 자리", ones_col),
                ):
                    with column:
                        with st.container(key=f"game1-pred-reel-{name}", gap=None):
                            st.button(
                                "▲", key=f"game1-pred-{name}-up", help=f"소수 {label} 증가",
                                width="stretch", on_click=_change_digit, args=(name, 1),
                            )
                            st.html(
                                f'<div class="game1-pred-digit" aria-label="소수 {label} {value}">'
                                f'{value}</div>'
                            )
                            st.button(
                                "▼", key=f"game1-pred-{name}-down", help=f"소수 {label} 감소",
                                width="stretch", on_click=_change_digit, args=(name, -1),
                            )
            st.html(
                '<p class="game1-pred-range">'
                '유사도 점수 범위&nbsp; 0.00 – 0.99 '
                '<span aria-hidden="true">ⓘ</span></p>'
            )

        st.html(
            '<div class="game1-pred-podium" aria-hidden="true">'
            + (f'<img src="{podium}" alt="">' if podium else '<span>♛</span>')
            + '</div>'
        )

        if st.button("✓  예측 확정", key="game1-pred-submit", type="primary", width="stretch"):
            st.session_state.game_1_predicted_digits = (
                int(st.session_state.game1_pred_tens) * 10 + int(st.session_state.game1_pred_ones)
            )
            st.rerun()
