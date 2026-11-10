
import streamlit as st
import time
import math
import asyncio
from collections.abc import Mapping

from modules.news_ai import summary, similarity_check, bring_article
from modules.db_handler import init_gspread
from modules.ui_components import change_page
from games.shared.news_flow import get_game_news_selection
from games.shared.loading import similarity_analysis_loading
from games.shared.betting import render_betting_ui
from games.shared.result import show_summary_before_score
from games.shared.interest import apply_end_of_turn_interest
from modules.transactions import BalanceChanged, TransactionError, settle_game_round, update_session_balances


# ==========================================
# 공통 설정
# ==========================================

MIN_BET = 1000


# ==========================================
# 유사도 점수 추출
# ==========================================

def extract_similarity_score(result):
    """Extract a 0~100 percentage from current or legacy AI responses."""
    if isinstance(result, bool):
        raise ValueError(f"유사도 결과가 숫자가 아닙니다: {result}")

    if isinstance(result, (int, float, str)):
        try:
            value = float(result)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"유사도 결과가 숫자가 아닙니다: {result}") from exc
        return value * 100 if 0 <= value <= 1 else value

    if not isinstance(result, Mapping):
        raise ValueError(f"지원하지 않는 유사도 반환 형식입니다: {type(result)}")

    if "score_hundredths" in result:
        hundredths = result["score_hundredths"]
        if isinstance(hundredths, Mapping):
            return extract_similarity_score(hundredths)
        return float(hundredths) / 100

    for key in (
        "score",
        "similarity",
        "similarity_score",
        "similarity_percentage",
        "percentage",
        "percent",
        "유사도",
        "유사도 점수",
        "점수",
    ):
        if key in result:
            return extract_similarity_score(result[key])

    numeric_values = [
        value for value in result.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    if len(numeric_values) == 1:
        return extract_similarity_score(numeric_values[0])

    raise ValueError(
        "유사도 딕셔너리에서 점수를 찾지 못했습니다. "
        f"실제 반환값: {result}"
    )


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
        "game_3_screen",
        "selected_news_game_3",
        "candidates_game_3",
        "read_done_game_3",
        "game_3_article_data",
    ]

    for key in keys:
        st.session_state.pop(key, None)

    st.session_state.game_3_round = old_round + 1
    st.session_state.game_3_screen = "choice"


# ==========================================
# 슬롯 디자인
# ==========================================

def fix_game_3_slot_animation():

    st.markdown(
        """
        <style>

        .st-key-btn_game_3_0 button,
        .st-key-btn_game_3_1 button,
        .st-key-btn_game_3_2 button {

            position: relative !important;
            overflow: hidden !important;

            min-height: 85px !important;

            background-color: #ffffff !important;
            color: #2d1842 !important;

            border: 3px solid #2d1842 !important;
            border-radius: 8px !important;

            padding: 15px !important;

            font-size: 16px !important;
            font-weight: 900 !important;

            text-align: left !important;
            white-space: normal !important;

            box-shadow: 4px 4px 0px #2d1842 !important;

            transition: all 0.2s ease !important;
        }

        .st-key-btn_game_3_0 button p,
        .st-key-btn_game_3_1 button p,
        .st-key-btn_game_3_2 button p {

            color: #2d1842 !important;
            font-weight: 900 !important;
            line-height: 1.5 !important;
            white-space: normal !important;
            word-break: keep-all !important;
        }

        .st-key-btn_game_3_0 button:hover,
        .st-key-btn_game_3_1 button:hover,
        .st-key-btn_game_3_2 button:hover {

            background-color: #f3e8ff !important;
            border-color: #a855f7 !important;
            transform: translateY(-2px);
            box-shadow: 5px 5px 0px #2d1842 !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


# ==========================================
# 기사 가져오기
# ==========================================

def load_game_3_article():

    saved_article = st.session_state.get(
        "game_3_article_data"
    )

    if saved_article:

        return (
            saved_article.get("title"),
            saved_article.get("article_text"),
            saved_article.get("url")
        )

    try:

        selection = get_game_news_selection("game_3")

        if selection is None:
            return None, None, None

        if not isinstance(selection, (tuple, list)):
            st.error("뉴스 선택 함수의 반환 형식이 올바르지 않습니다.")
            return None, None, None

        if len(selection) != 3:
            st.error("뉴스 선택 함수에서 반환된 데이터가 올바르지 않습니다.")
            return None, None, None

        title, article_text, url = selection

        if not title or not url:
            return None, None, None

        url = str(url).strip()

        if not url.startswith(("http://", "https://")):
            st.error("올바른 기사 URL이 아닙니다.")
            return None, None, None

        if not article_text or not str(article_text).strip():

            with st.spinner("기사 본문을 가져오는 중입니다..."):

                extracted_title, extracted_text = bring_article(url)

                if extracted_title:
                    title = extracted_title

                article_text = extracted_text

        if not article_text or not str(article_text).strip():
            st.error("기사 본문을 가져오지 못했습니다.")
            return None, None, None

        st.session_state.game_3_article_data = {
            "title": title,
            "article_text": article_text,
            "url": url
        }

        return title, article_text, url

    except Exception as e:

        st.error("뉴스 기사 처리 중 오류가 발생했습니다.")
        st.exception(e)

        return None, None, None


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

def show_bet_screen(ws):
    """Use the shared wager UI; Game 3 retains its half-stake loss rule."""
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
    st.caption("정답 시 순이익 +베팅액, 오답 시 손실 −베팅액의 절반")
    round_number = st.session_state.get("game_3_round", 0)
    user = st.session_state.get("current_user_data") or {}
    confirmed_bet = render_betting_ui(
        current_coins=int(user_info.get("코인", 0)),
        users_data=users_data,
        current_sid=current_sid,
        current_nickname=str(user.get("아이디", user_info.get("아이디", ""))),
        min_bet=MIN_BET,
        payout_multiplier=1.0,
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

    st.markdown("### 📰 STEP 3. 뉴스 기사 선택")

    st.info("슬롯이 멈추면 분석할 뉴스 기사를 선택하세요.")

    fix_game_3_slot_animation()

    title, article_text, url = load_game_3_article()

    if not title or not article_text or not url:
        return

    st.markdown("---")
    st.markdown("### 📄 선택한 뉴스 기사")

    st.markdown(f"**뉴스 제목: {title}**")

    with st.expander("뉴스 본문 확인하기", expanded=True):
        st.write(article_text)

    st.markdown(f"[기사 원문 열기]({url})")

    st.session_state.game_3_screen = "analysis"

    st.rerun()


# ==========================================
# STEP 4. AI 분석 및 코인 정산
# ==========================================

def analyze_game_3(ws):

    article = st.session_state.get("game_3_article_data")

    if not article:

        st.error("분석할 뉴스 기사가 없습니다.")
        return

    title = article["title"]
    article_text = article["article_text"]
    url = article["url"]

    bet_coin = st.session_state.game_3_bet

    current_sid = str(
        st.session_state.current_user
    ).strip().replace(".0", "")

    st.markdown("### 🤖 STEP 4. AI 유사도 분석")

    st.info(
        "AI가 뉴스 본문을 요약하고 "
        "뉴스 제목과 요약문의 유사도를 분석합니다."
    )

    st.markdown(f"**뉴스 제목: {title}**")

    with st.expander("뉴스 본문 확인하기"):
        st.write(article_text)

    st.markdown(f"[기사 원문 열기]({url})")

    if st.button(
        "🤖 뉴스 유사도 분석 및 결과 확인",
        use_container_width=True
    ):

        with similarity_analysis_loading():

            try:

                # 뉴스 요약
                summary_text = asyncio.run(summary(article_text))

                if not summary_text:
                    raise ValueError("뉴스 요약 결과가 비어 있습니다.")

                # 유사도 계산
                similarity_result = similarity_check(
                    summary_text,
                    title
                )

                # 딕셔너리 또는 숫자 반환값 처리
                actual_score = extract_similarity_score(
                    similarity_result
                )

                if (
                    not math.isfinite(actual_score)
                    or not 0 <= actual_score <= 100
                ):

                    raise ValueError(
                        f"유사도 점수가 0~100 범위를 벗어났습니다: {actual_score}"
                    )

                integer_score = int(actual_score)

                ai_result = (
                    "짝" if integer_score % 2 == 0 else "홀"
                )

                user_choice = st.session_state.game_3_choice

                is_win = user_choice == ai_result

                if is_win:
                    reward = bet_coin
                else:
                    reward = -(bet_coin // 2)

                settled = settle_game_round("game_3", int(bet_coin), is_win)
                reward = settled["reward"]
                new_balance = settled["new_coins"]
                new_streak = settled["new_streak"]

                # 결과 저장
                st.session_state.game_3_result = {

                    "actual_score": actual_score,
                    "score_details": (
                        similarity_result
                        if isinstance(similarity_result, Mapping)
                        and {"model_name", "logit", "normalized", "token_count"}.issubset(similarity_result)
                        else None
                    ),
                    "integer_score": integer_score,
                    "ai_result": ai_result,
                    "user_choice": user_choice,
                    "bet": bet_coin,
                    "reward": reward,
                    "is_win": is_win,
                    "new_coins": new_balance,
                    "new_streak": new_streak,
                    "title": title,
                    "url": url,
                    "summary": summary_text

                }

                st.session_state.game_3_screen = "result"

                st.rerun()

            except BalanceChanged as changed:
                update_session_balances(changed.balances)
                st.error(str(changed))
            except TransactionError as exc:
                st.error(str(exc))
            except Exception as e:

                st.error(f"게임 진행 중 오류가 발생했습니다: {e}")


# ==========================================
# STEP 5. 결과 화면
# ==========================================

def show_result_screen():

    res = st.session_state.game_3_result
    if not apply_end_of_turn_interest("game_3"):
        return

    if not show_summary_before_score(
        res["summary"], "game_3_summary_revealed",
        title=res["title"], score=res["actual_score"],
        details=res.get("score_details"), score_precision=2,
    ):
        return
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

    ws = init_gspread()

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

        show_bet_screen(ws)
        return

    elif screen == "news":

        show_news_screen()
        return

    elif screen == "analysis":

        analyze_game_3(ws)
        return

    elif screen == "result":

        show_result_screen()
        return
