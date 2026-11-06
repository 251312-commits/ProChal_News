import asyncio
from pathlib import Path
from uuid import uuid4

import streamlit.components.v1 as components

import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread, init_news_sheet
from modules.ui_components import change_page, load_local_image_as_base64
from views.ranking import fetch_ranking_data
from games.shared.result import show_summary_before_score
from games.shared.news_flow import get_game_news_selection
from games.shared.betting import check_user_coins_or_pop_bank
from games.shared.betting import render_betting_ui
from games.shared.loading import similarity_analysis_loading

ws = init_gspread()
ws_news = init_news_sheet()

# 순이익(잔액 증가액) 배율. UI 예상 코인과 실제 승리 정산에 공통 적용.
GAME_1_WIN_MULTIPLIER = 100.0

# 정의된 함수: show_game_1

def show_game_1():
    if "game_1_bet" not in st.session_state:
        # 코인 부족 검사 (부족 시 은행 팝업)
        if not check_user_coins_or_pop_bank():
            return

        user_data = st.session_state.get('current_user_data', {})
        current_coins = int(user_data.get('코인', 0))
        current_sid = str(st.session_state.get('current_user', ''))
        current_nickname = str(user_data.get('아이디', ''))
        # 랭킹 화면과 같은, 최대 10초 캐시된 사용자 코인 목록을 이용한다.
        # 이전에는 캐시가 없는 경우 빈 목록으로 처리돼 1위로 잘못 표시됐다.
        try:
            users_data = fetch_ranking_data()
        except Exception:
            users_data = None

        # Use the checked-in betting background from the assets directory.
        confirmed_bet = render_betting_ui(
            current_coins=current_coins,
            users_data=users_data,
            current_sid=current_sid,
            current_nickname=current_nickname,
            bg_image_path=str(Path(__file__).resolve().parents[2] / "assets" / "bet_background.jpg"),
            payout_multiplier=GAME_1_WIN_MULTIPLIER,
            title="title",  # 나중에 실제 게임 제목으로 교체
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
            summary_text = asyncio.run(summary(article_text))
            if not summary_text:
                st.error("뉴스 본문 요약에 실패해 유사도 점수를 계산할 수 없습니다.")
                return
            score_details = similarity_check(summary_text, title)
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

            current_sid = st.session_state.current_user
            users_data = ws.get_all_records()
            user_row_idx = None
            user_info = None

            for idx, u in enumerate(users_data):
                sid = str(u.get('학번', '')).strip().replace('.0', '')
                if sid == current_sid:
                    user_row_idx = idx + 2
                    user_info = u
                    break

            current_coins = int(user_info.get('코인', 0)) if user_info else 0
            current_streak = int(user_info.get('연승', 0)) if user_info else 0

            if is_win:
                new_coins = current_coins + reward
                new_streak = current_streak + 1
            else:
                new_coins = max(0, current_coins + reward)
                new_streak = 0

            if user_row_idx:
                ws.update_cell(user_row_idx, 3, new_coins)
                ws.update_cell(user_row_idx, 4, new_streak)
                st.session_state.current_user_data['코인'] = new_coins
                st.session_state.current_user_data['연승'] = new_streak

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

    # 최종 결과 출력
    res = st.session_state.game_1_result
    show_summary_before_score(
        res.get("summary", ""), "game_1_summary_revealed",
        title=res.get("title", title), score=res["actual_score"],
        details=res.get("score_details"),
        prediction=res.get("predicted_digits"),
    )
    st.markdown("---")
    st.markdown("### 🏆 6단계: 최종 결과")

    if res["is_win"]:
        st.balloons()
        st.success(f"{res['msg']} | 획득 코인: +{res['reward']:,} C")
    else:
        st.error(f"{res['msg']} | 차감 코인: {res['reward']:,} C")

    if "predicted_digits" not in res:
        # An already settled round from the whole-score game keeps its original result.
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1: st.metric("내 예측 점수", f"{st.session_state.game_1_predicted_score:02d}점")
        with col_r2: st.metric("AI 측정 점수", f"{res['actual_score']:02d}점")
        with col_r3: st.metric("점수 오차", f"{res['diff']}점")

    st.markdown(
        f"""
        <div style="background:#110022; border:2px solid #8A2BE2; padding:15px; border-radius:10px; text-align:center; margin:15px 0;">
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 보유 코인: <span style="color:#00ffcc;">{res['new_coins']:,} C</span></p>
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 연승 기록: <span style="color:#ff00ff;">{res['new_streak']} 연승</span></p>
        </div>
        """,
        unsafe_allow_html=True
    )

    def reset_game_1_state():
        keys_to_clear = [
            "game_1_bet", "selected_news_game_1", "candidates_game_1", 
            "read_done_game_1", "game_1_predicted_digits", "game_1_predicted_score", "game_1_result",
            "tens_val", "ones_val", "game1_pred_tens", "game1_pred_ones", "game1_pred_round_id", "game_1_summary_revealed"
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            reset_game_1_state()
            st.rerun()

    with col_btn2:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            reset_game_1_state()
            change_page('main')


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
        f'<img src="{load_local_image_as_base64(str(art / (name + ".webp")))}" alt="">'
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
