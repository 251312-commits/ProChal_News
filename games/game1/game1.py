from pathlib import Path
from uuid import uuid4

import streamlit.components.v1 as components

import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.ui_components import change_page, load_local_image_url
from views.ranking import fetch_ranking_data
from games.shared.news_flow import get_game_news_selection
from games.shared.betting import check_user_coins_or_pop_bank
from games.shared.betting import render_betting_ui
from games.shared.loading import similarity_analysis_loading
from games.shared.round_analysis import analyze_round_once
from games.shared.interest import apply_end_of_turn_interest
from modules.transactions import BalanceChanged, TransactionError, settle_game_round, update_session_balances

# 순이익(잔액 증가액) 배율. UI 예상 코인과 실제 승리 정산에 공통 적용.
GAME_1_WIN_MULTIPLIER = 100.0


def show_game_1():
    if "game_1_bet" not in st.session_state:
        # 코인 부족 검사 (부족 시 은행 팝업)
        if not check_user_coins_or_pop_bank():
            return

        user_data = st.session_state.get('current_user_data', {})
        current_coins = int(user_data.get('코인', 0))
        current_sid = str(st.session_state.get('current_user', ''))
        current_nickname = str(user_data.get('아이디', ''))
        # 베팅 예상 순위는 랭킹 화면과 같은 캐시를 사용한다.
        try:
            users_data = fetch_ranking_data()
        except Exception:
            users_data = None

        confirmed_bet = render_betting_ui(
            current_coins=current_coins,
            users_data=users_data,
            current_sid=current_sid,
            current_nickname=current_nickname,
            bg_image_path=str(Path(__file__).resolve().parents[2] / "assets" / "bet_background.jpg"),
            payout_multiplier=GAME_1_WIN_MULTIPLIER,
            title="게임 1 · 일치율 소수점 맞히기",
            state_key="game_1",
        )

        if confirmed_bet is not None:
            st.session_state.game_1_bet = confirmed_bet
            st.rerun()

        return

    # [2단계 & 3단계] 기사 선택 / 30초 읽기
    title, article_text, url = get_game_news_selection("game_1", win_multiplier=GAME_1_WIN_MULTIPLIER)
    if not title:
        return

    # [4단계] 실제 예측값은 소수점 아래 두 자리(00~99)만 저장한다.
    if "game_1_predicted_digits" not in st.session_state and "game_1_result" not in st.session_state:
        render_game1_prediction_picker(title)
        return

    if st.session_state.get("selected_news_game_1"):
        st.title("🎮 게임 1: 뉴스 유사도 예측 게임")

    # [5단계 & 6단계] AI 점수 측정 및 정산
    bet_coin = st.session_state.game_1_bet

    if "game_1_result" not in st.session_state:
        predicted_digits = st.session_state.game_1_predicted_digits
        with similarity_analysis_loading():
            try:
                summary_text, score_details = analyze_round_once(
                    st.session_state, "game_1", title=title, article_text=article_text,
                    summarize=summary, similarity=similarity_check,
                )
            except (RuntimeError, ValueError, TypeError, KeyError) as exc:
                st.error(f"뉴스 본문 분석에 실패해 유사도 점수를 계산할 수 없습니다: {exc}")
                return
            actual_score = score_details["score"]
            answer_digits = score_details["score_hundredths"] % 100

            if predicted_digits == answer_digits:
                reward = int(bet_coin * GAME_1_WIN_MULTIPLIER)
                is_win = True
                result_msg = f"🎉 적중! 소수점 뒤 두 자리는 {answer_digits:02d}"
            else:
                reward = -bet_coin
                is_win = False
                result_msg = f"💥 빗나갔습니다. 정답은 {answer_digits:02d}"

            try:
                settled = settle_game_round(
                    "game_1", int(bet_coin), is_win,
                    badge_evidence={
                        "predicted_digits": int(predicted_digits),
                        "answer_digits": int(answer_digits),
                    },
                )
            except BalanceChanged as changed:
                update_session_balances(changed.balances)
                st.error(str(changed))
                return
            except TransactionError as exc:
                st.error(str(exc))
                return
            reward = settled["reward"]
            new_coins = settled["new_coins"]
            new_streak = settled["new_streak"]

            st.session_state.game_1_result = {
                "title": title,
                "summary": summary_text,
                "actual_score": actual_score,
                "score_details": score_details,
                "predicted_digits": predicted_digits,
                "reward": reward,
                "is_win": is_win,
                "msg": result_msg,
                "new_coins": new_coins,
                "new_streak": new_streak
            }

    # Both settlement and interest finish before the cinematic reveal.
    res = st.session_state.game_1_result
    if not apply_end_of_turn_interest("game_1"):
        return
    from games.game1.result_reveal import render_game1_result_reveal
    render_game1_result_reveal(res)


# ===== Game 1-only prediction screen =====
_HERE = Path(__file__).resolve().parent
_ASSETS = _HERE.parents[1] / "assets"
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
    """Resolve image URLs for the prediction screen."""
    return {
        key: load_local_image_url(str(_ASSETS / filename))
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


# ===== Game 1-only tutorial screen =====
def show_game_1_tutorial():
    art = Path(__file__).resolve().parents[2] / "assets" / "game1_guide"
    steps = (
        ("bet", "코인 베팅", "금액을 정해 베팅한다.<br>최소 <b>1,000 C</b>"),
        ("news", "기사 선택", "레버를 내린 뒤<br>기사 한 편을 골라 읽는다."),
        ("digits", "두 자리 예측", "▲▼로 소수점 뒤 두 자리 선택<br>예시　87.04점 → <b>04</b>"),
        ("result", "결과 확인", "적중　+베팅액의 <b>100배</b><br>실패　−베팅액"),
    )
    cards = "".join(
        f'<li><h2><span>{number:02d}</span>{title}</h2>'
        f'<img src="{load_local_image_url(str(art / (name + ".webp")))}" alt="">'
        f'<p>{caption}</p></li>'
        for number, (name, title, caption) in enumerate(steps, 1)
    )
    with st.container(key="game1-guide", gap=None):
        st.html(Path(__file__).with_name("game1_tutorial.css"))
        with st.container(key="game1-guide-nav", horizontal=True, gap=None):
            if st.button("메인으로", key="game1-guide-back"):
                change_page("main")
            if st.button("건너뛰기", key="game1-guide-skip"):
                change_page("game_1")
        st.html(f"""
            <section class="game1-guide-sheet" aria-labelledby="game1-guide-title" lang="ko">
                <header class="game1-guide-heading">
                    <span>GAME 01</span><h1 id="game1-guide-title">뉴스 유사도 예측</h1>
                    <p>기사 제목과 AI 요약문은 얼마나 비슷할까?</p>
                </header>
                <ol aria-label="게임 진행 순서" role="list">{cards}</ol>
            </section>
        """)
        if st.button("베팅하러 가기", key="game1-guide-start", type="primary", width="stretch"):
            change_page("game_1")
