"""Casino-style fractional digit picker for Game 1.

The only submitted game value is the pair of fractional digits (00-99).
All art is loaded from local repository assets; the news headline is escaped.
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
    key = f"game1_pred_{name}"
    st.session_state[key] = (int(st.session_state.get(key, 0)) + delta) % 10


@st.fragment
def render_game1_prediction_picker(article_title: str) -> None:
    """Render and submit a mobile-first 2-digit similarity prediction.

    Navigation deliberately keeps the bet, chosen news, and current dial values.
    A prediction is committed only by the confirmation button.
    """
    # Preserve the previous round's selection keys so an interrupted visit resumes.
    if "game1_pred_tens" not in st.session_state:
        st.session_state.game1_pred_tens = int(st.session_state.get("tens_val", 0)) % 10
    if "game1_pred_ones" not in st.session_state:
        st.session_state.game1_pred_ones = int(st.session_state.get("ones_val", 4)) % 10

    # Legacy keys remain synchronized for the result/reset code and old sessions.
    tens = int(st.session_state.game1_pred_tens) % 10
    ones = int(st.session_state.game1_pred_ones) % 10
    st.session_state.tens_val = tens
    st.session_state.ones_val = ones

    user = st.session_state.get("current_user_data") or {}
    balance = int(user.get("코인", 0))
    headline = escape(str(article_title or "선택된 뉴스가 없습니다"), quote=True)

    banner = _asset("game1_prediction/pred_header.avif")
    tag = _asset("game1_prediction/pred_tag.avif")
    news_plate = _asset("game1_prediction/pred_news.avif")
    frame = _asset("game1_prediction/pred_frame.avif")
    reel = _asset("game1_prediction/pred_reel.avif")
    coins = _asset("bet_coin_stack.png")
    background = _asset("bet_background.jpg")

    # CSS backgrounds use trusted base64 data URLs. No remote images or scripts.
    asset_css = [
        ".stApp:has(.st-key-game1-prediction) {"
        f"background:#13051e url('{background}') center center/cover no-repeat !important;"
        "}" if background else "",
        f".st-key-game1-prediction-machine {{ background-image:url('{frame}') !important; border:0 !important; }}" if frame else "",
        f".game1-pred-news-wrap {{ background-image:url('{news_plate}') !important; background-size:100% 100% !important; border:0 !important; }}" if news_plate else "",
        f".st-key-game1-pred-reel-tens,.st-key-game1-pred-reel-ones {{ background-image:url('{reel}') !important; border:0 !important; }} .st-key-game1-pred-reel-tens button,.st-key-game1-pred-reel-ones button {{ color:transparent !important; text-shadow:none !important; }}" if reel else "",
    ]

    # The dedicated CSS turns ordinary vertical blocks into stable three-column grids.
    # Streamlit horizontal containers insert extra flex wrappers on narrow screens.
    with st.container(key="game1-prediction", gap=None):
        st.html(Path(__file__).with_suffix(".css"))
        st.html("<style>" + "\n".join(asset_css) + "</style>")

        with st.container(key="game1-prediction-nav", gap=None):
            if st.button("❮", key="game1-pred-back", help="메인으로 돌아가기"):
                change_page("main")
            st.html(
                '<div class="game1-pred-wallet" aria-label="보유 코인">'
                '<span class="game1-pred-wallet-coin" aria-hidden="true">₵</span>'
                f'<span>{balance:,} C</span></div>'
            )
            if st.button("+", key="game1-pred-bank", help="은행으로 이동"):
                change_page("bank")

        st.html(
            '<section class="game1-pred-heading" aria-label="유사도 예측">'
            + (f'<img class="game1-pred-banner" src="{banner}" alt="SIMILARITY PREDICT">' if banner else '<span class="game1-pred-banner-fallback">♛ SIMILARITY PREDICT</span>')
            + '<h1>유사도 예측</h1>'
            + '<p>선택한 기사 제목과 AI 요약문의<br>유사도 점수 소수 두 자리를 예측하세요.</p>'
            + '</section>'
        )

        st.html(
            '<section class="game1-pred-news-wrap" aria-label="선택한 뉴스">'
            + (f'<img class="game1-pred-news-tag" src="{tag}" alt="선택한 뉴스">' if tag else '<span class="game1-pred-news-tag-fallback">선택한 뉴스</span>')
            + f'<div class="game1-pred-news-title" title="{headline}">{headline}</div></section>'
        )

        with st.container(key="game1-prediction-machine", gap=None):
            st.html('<div class="game1-pred-machine-title">✦&nbsp; 예측하는 유사도 점수 &nbsp;✦</div>')
            with st.container(key="game1-prediction-reels", gap=None):
                st.html('<span class="game1-pred-zero" aria-hidden="true">0.</span>')
                for name, value, label in (("tens", tens, "첫째 자리"), ("ones", ones, "둘째 자리")):
                    with st.container(key=f"game1-pred-reel-{name}", gap=None):
                        if st.button("▲", key=f"game1-pred-{name}-up", help=f"소수 {label} 증가", width="stretch"):
                            _change_digit(name, 1)
                            st.rerun(scope="fragment")
                        st.html(f'<div class="game1-pred-digit" aria-label="소수 {label} {value}">{value}</div>')
                        if st.button("▼", key=f"game1-pred-{name}-down", help=f"소수 {label} 감소", width="stretch"):
                            _change_digit(name, -1)
                            st.rerun(scope="fragment")
            st.html('<p class="game1-pred-range">유사도 점수 범위　0.00 – 0.99 <span aria-hidden="true">ⓘ</span></p>')

        st.html(
            '<div class="game1-pred-coins" aria-hidden="true">'
            + (f'<img src="{coins}" alt="">' if coins else '<span>✦</span>')
            + '</div>'
        )
        if st.button("✓  예측 확정", key="game1-pred-submit", type="primary", width="stretch"):
            st.session_state.game_1_predicted_digits = (
                int(st.session_state.game1_pred_tens) * 10 + int(st.session_state.game1_pred_ones)
            )
            st.rerun()
