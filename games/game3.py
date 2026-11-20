
import streamlit as st
import time
import math

from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread
from modules.ui_components import change_page
from games.shared.news_flow import get_game_news_selection
from games.shared.loading import similarity_analysis_loading
from games.shared.round_analysis import analyze_round_once
from games.shared.betting import render_betting_ui
from games.shared.result import show_summary_before_score
from games.shared.interest import apply_end_of_turn_interest
from modules.transactions import BalanceChanged, TransactionError, settle_game_round, update_session_balances


# ==========================================
# 공통 설정
# ==========================================

MIN_BET = 1000
GAME_3_WIN_MULTIPLIER = 2.0


# ==========================================
# 게임 상태 초기화
# ==========================================

def reset_game_3_state():

    old_round = st.session_state.get("game_3_round", 0)

    keys = [
        "game_3_choice",
        "game_3_choice_deadline",
        "game_3_choice_timeout",
        "game_3_bet",
        "game_3_round_id",
        "game_3_result",
        "game_3_summary_revealed",
        "game_3_analysis_checkpoint",
        "game_3_screen",
        "selected_news_game_3",
        "candidates_game_3",
        "read_done_game_3",
        "game_3_slot_round",
        "game_3_reader_round",
        "game_3_direct_url_error",
        "game_3_direct_url_request_id",
    ]

    for key in keys:
        st.session_state.pop(key, None)

    st.session_state.game_3_round = old_round + 1
    st.session_state.game_3_screen = "choice"


# ==========================================
# STEP 1. 홀짝 선택
# ==========================================

def show_choice_screen():

    st.markdown("### 🎯 STEP 1. 홀짝 선택")
    st.info("10초 안에 홀 또는 짝을 선택하세요!")

    if "game_3_choice_deadline" not in st.session_state:

        st.session_state.game_3_choice_deadline = time.time() + 10

    @st.fragment(run_every="1s")
    def choice_screen():

        remaining = max(
            0,
            math.ceil(
                st.session_state.game_3_choice_deadline - time.time()
            )
        )

        st.markdown(f"## ⏳ 남은 시간: {remaining}초")

        if remaining <= 0:

            st.session_state.game_3_choice_timeout = True
            st.rerun()
            return

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "🔴 홀 (ODD)",
                key="game_3_odd",
                use_container_width=True
            ):

                if time.time() <= st.session_state.game_3_choice_deadline:

                    st.session_state.game_3_choice = "홀"
                    st.session_state.game_3_screen = "bet"

                else:

                    st.session_state.game_3_choice_timeout = True

                st.rerun()

        with col2:

            if st.button(
                "🔵 짝 (EVEN)",
                key="game_3_even",
                use_container_width=True
            ):

                if time.time() <= st.session_state.game_3_choice_deadline:

                    st.session_state.game_3_choice = "짝"
                    st.session_state.game_3_screen = "bet"

                else:

                    st.session_state.game_3_choice_timeout = True

                st.rerun()

    choice_screen()


# ==========================================
# STEP 2. 베팅 화면
# ==========================================

def show_bet_screen():
    """Use the shared wager UI; Game 3 retains its half-stake loss rule."""
    ws = init_gspread()
    current_sid = str(st.session_state.current_user).strip().replace(".0", "")
    users_data = ws.get_all_records()
    user_info = next(
        (user for user in users_data
         if str(user.get("학번", "")).strip().replace(".0", "") == current_sid),
        None,
    )
    if user_info is None:
        st.error("사용자 정보를 찾을 수 없습니다.")
        return

    st.success(f"내 선택: {st.session_state.game_3_choice}")
    st.caption("정답 시 순이익 +베팅액의 2배, 오답 시 손실 −베팅액의 절반")
    round_number = st.session_state.get("game_3_round", 0)
    user = st.session_state.get("current_user_data") or {}
    confirmed_bet = render_betting_ui(
        current_coins=int(user_info.get("코인", 0)),
        users_data=users_data,
        current_sid=current_sid,
        current_nickname=str(user.get("아이디", user_info.get("아이디", ""))),
        min_bet=MIN_BET,
        payout_multiplier=GAME_3_WIN_MULTIPLIER,
        title="게임 3: 홀짝 예측",
        state_key=f"game_3_{round_number}",
        round_key="game_3",
    )
    if confirmed_bet is not None:
        st.session_state.game_3_bet = confirmed_bet
        st.session_state.game_3_screen = "news"
        st.rerun()

    if st.button("🔄 홀짝 다시 선택하기", use_container_width=True):
        reset_game_3_state()
        st.rerun()


# ==========================================
# STEP 3. 뉴스 선택
# ==========================================

def show_news_screen():
    # The shared reader has already saved the chosen article.
    title, article_text, url = get_game_news_selection(
        "game_3", win_multiplier=GAME_3_WIN_MULTIPLIER
    )
    if not title or not article_text or not url:
        return
    st.session_state.game_3_screen = "analysis"
    st.rerun()


# ==========================================
# STEP 4. AI 분석 및 코인 정산
# ==========================================

def analyze_game_3():
    article = st.session_state.get("selected_news_game_3") or {}
    if not article or not st.session_state.get("read_done_game_3"):
        st.error("분석할 뉴스 기사가 없습니다.")
        return

    title = article["title"]
    article_text = article["text"]
    url = article["url"]
    bet_coin = st.session_state.game_3_bet

    st.markdown("### 🤖 STEP 4. AI 유사도 분석")
    st.info("AI가 뉴스 본문을 요약하고 뉴스 제목과 요약문의 유사도를 분석합니다.")
    st.markdown(f"**뉴스 제목: {title}**")
    with st.expander("뉴스 본문 확인하기"):
        st.write(article_text)
    st.markdown(f"[기사 원문 열기]({url})")

    if st.button("🤖 뉴스 유사도 분석 및 결과 확인", use_container_width=True):
        with similarity_analysis_loading():
            try:
                summary_text, similarity_result = analyze_round_once(
                    st.session_state, "game_3", title=title, article_text=article_text,
                    summarize=summary, similarity=similarity_check,
                )
                actual_score = float(similarity_result["score"])
                integer_score = int(actual_score)
                ai_result = "짝" if integer_score % 2 == 0 else "홀"
                user_choice = st.session_state.game_3_choice
                is_win = user_choice == ai_result

                settled = settle_game_round(
                    "game_3", int(bet_coin), is_win,
                    badge_evidence={"choice": user_choice},
                )
                st.session_state.game_3_result = {
                    "actual_score": actual_score,
                    "score_details": similarity_result,
                    "integer_score": integer_score,
                    "ai_result": ai_result,
                    "user_choice": user_choice,
                    "bet": bet_coin,
                    "reward": settled["reward"],
                    "is_win": is_win,
                    "new_coins": settled["new_coins"],
                    "new_streak": settled["new_streak"],
                    "title": title,
                    "url": url,
                    "summary": summary_text,
                }
                st.session_state.game_3_screen = "result"
                st.rerun()
            except BalanceChanged as changed:
                update_session_balances(changed.balances)
                st.error(str(changed))
            except TransactionError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"게임 진행 중 오류가 발생했습니다: {exc}")


# ==========================================
# STEP 5. 결과 화면
# ==========================================

def show_result_screen():

    res = st.session_state.game_3_result
    if not apply_end_of_turn_interest("game_3"):
        return

    show_summary_before_score(
        res["summary"], "game_3_summary_revealed",
        title=res["title"], score=res["actual_score"],
        details=res.get("score_details"), score_precision=2,
    )
    st.markdown("### 🏆 최종 게임 결과")

    if res["is_win"]:

        st.balloons()
        st.success("정답입니다! 베팅 성공!")

    else:

        st.error("아쉽습니다! 베팅 실패!")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("내 선택", res["user_choice"])

    with col2:
        st.metric("정수 부분의 홀짝", f"{res['integer_score']} · {res['ai_result']}")

    with st.expander("분석한 뉴스 기사 정보"):

        st.write(res["title"])
        st.markdown(f"[기사 원문 열기]({res['url']})")

    st.markdown(f"""
    <div style="
        background:#110022;
        border:2px solid #8A2BE2;
        padding:20px;
        border-radius:12px;
        text-align:center;
        color:white;
    ">

        <p>베팅 금액: {res['bet']:,} C</p>

        <h1 style="color:{'#00ffcc' if res['is_win'] else '#ff5555'};">
            {res['reward']:+,} C
        </h1>

        <p>현재 보유 코인</p>

        <h2 style="color:#ffd700;">
            {res['new_coins']:,} C
        </h2>

        <p>현재 연승 기록: {res['new_streak']} 연승</p>

    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:

        if st.button("🔄 다시 도전하기", use_container_width=True):

            reset_game_3_state()
            st.rerun()

    with col2:

        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):

            reset_game_3_state()
            change_page("main")


# ==========================================
# 게임 메인 함수
# ==========================================

def show_game_3():

    st.title("🎰 뉴스 유사도 홀짝 게임")

    if "game_3_screen" not in st.session_state:
        st.session_state.game_3_screen = "choice"

    # 시간 초과
    if st.session_state.get("game_3_choice_timeout", False):

        st.error("⏰ 선택 시간이 초과되었습니다!")

        if st.button("🔄 다시 도전하기"):

            reset_game_3_state()
            st.rerun()

        if st.button("⬅️ 메인으로 돌아가기"):

            reset_game_3_state()
            change_page("main")

        return

    screen = st.session_state.game_3_screen

    if screen == "choice":

        show_choice_screen()
        return

    elif screen == "bet":

        show_bet_screen()
        return

    elif screen == "news":

        show_news_screen()
        return

    elif screen == "analysis":

        analyze_game_3()
        return

    elif screen == "result":

        show_result_screen()
        return
