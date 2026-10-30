# 홀짝(정수부분만) (하) (10초안에 선택) ½ (2배)

import streamlit as st
import time
import math
import re
import asyncio

from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread
from modules.ui_components import change_page
from games.common import get_game_news_selection


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
        "game_3_result",
        "game_3_analysis_done",
        "selected_news_game_3",
        "candidates_game_3",
        "read_done_game_3",
    ]

    for key in keys:
        st.session_state.pop(key, None)

    st.session_state.game_3_round = old_round + 1


# ==========================================
# 게임 메인 함수
# ==========================================

def show_game_3():

    st.title("🎰 뉴스 유사도 홀짝 게임")

    ws = init_gspread()

    # ======================================
    # STEP 1. 홀짝 선택 (10초 제한)
    # ======================================

    if (
        "game_3_choice" not in st.session_state
        and not st.session_state.get("game_3_choice_timeout", False)
    ):

        if "game_3_choice_deadline" not in st.session_state:
            st.session_state.game_3_choice_deadline = time.time() + 10

    if st.session_state.get("game_3_choice_timeout", False):

        st.error("⏰ 선택 시간이 초과되었습니다!")

        if st.button("🔄 다시 도전하기"):
            reset_game_3_state()
            st.rerun()

        if st.button("⬅️ 메인으로 돌아가기"):
            reset_game_3_state()
            change_page("main")

        return

    if "game_3_choice" not in st.session_state:

        st.markdown("### 🎯 STEP 1. 홀짝 선택")
        st.info("10초 안에 홀 또는 짝을 선택하세요!")

        @st.fragment(run_every="1s")
        def choice_screen():

            remaining = max(
                0,
                math.ceil(
                    st.session_state.game_3_choice_deadline - time.time()
                )
            )

            st.markdown(
                f"## ⏳ 남은 시간: {remaining}초"
            )

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
                    else:
                        st.session_state.game_3_choice_timeout = True

                    st.rerun()

        choice_screen()
        return

    # ======================================
    # STEP 2. 현재 보유 코인 확인
    # ======================================

    st.markdown("---")
    st.markdown("### 💰 STEP 2. 베팅 금액 선택")

    current_sid = str(
        st.session_state.current_user
    ).strip().replace(".0", "")

    users_data = ws.get_all_records()

    user_row_idx = None
    user_info = None

    for idx, user in enumerate(users_data):

        sid = str(user.get("학번", "")).strip().replace(".0", "")

        if sid == current_sid:
            user_row_idx = idx + 2
            user_info = user
            break

    if user_info is None:
        st.error("사용자 정보를 찾을 수 없습니다.")
        return

    current_coins = int(user_info.get("코인", 0))

    st.metric("💰 현재 보유 코인", f"{current_coins:,} C")

    st.success(f"내 선택: {st.session_state.game_3_choice}")

    MIN_BET = 500

    if current_coins < MIN_BET:

        st.error("최소 베팅 금액인 500코인이 부족합니다.")
        return

    round_number = st.session_state.get("game_3_round", 0)

    default_bet = max(
        MIN_BET,
        min(current_coins, (current_coins // 2 // 50) * 50)
    )

    bet_val = st.slider(
        "베팅할 코인을 선택하세요.",
        min_value=MIN_BET,
        max_value=current_coins,
        value=default_bet,
        step=50,
        key=f"game_3_bet_slider_{round_number}"
    )

    st.write(f"정답 시 순이익: +{bet_val:,} C")
    st.write(f"오답 시 손실: -{bet_val // 2:,} C")

    if st.button("🎲 베팅 확정", use_container_width=True):

        if bet_val > current_coins:
            st.error("보유 코인이 부족합니다.")
            return

        st.session_state.game_3_bet = bet_val
        st.rerun()

    if st.button("🔄 홀짝 다시 선택하기"):
        reset_game_3_state()
        st.rerun()

    if "game_3_bet" not in st.session_state:
        return

    bet_coin = st.session_state.game_3_bet

    # ======================================
    # STEP 3. 뉴스 기사 선택
    # ======================================

    st.markdown("---")
    st.markdown("### 📰 STEP 3. 뉴스 기사 선택")

    title, article_text, url = get_game_news_selection("game_3")

    if not title:
        return

    # ======================================
    # STEP 4. AI 유사도 분석
    # ======================================

    if "game_3_result" not in st.session_state:

        with st.spinner("🤖 AI가 뉴스 유사도를 분석하고 있습니다..."):

            try:

                # 비동기 뉴스 요약 함수 실행
                try:
                    asyncio.get_running_loop()
                except RuntimeError:
                    summary_text = asyncio.run(summary(article_text))
                else:
                    raise RuntimeError(
                        "이미 실행 중인 이벤트 루프가 있습니다. "
                        "뉴스 요약 실행 환경을 확인해주세요."
                    )

                if not summary_text:
                    raise ValueError("뉴스 요약 결과가 비어 있습니다.")

                actual_score = similarity_check(
                    summary_text,
                    title
                )

                actual_score = float(actual_score)

                if not math.isfinite(actual_score) or not 0 <= actual_score <= 100:
                    raise ValueError("유사도 점수가 올바르지 않습니다.")

                # 정수 부분만 사용
                integer_score = int(actual_score)

                # 홀짝 판정
                ai_result = (
                    "짝" if integer_score % 2 == 0 else "홀"
                )

                # 사용자 선택과 비교
                user_choice = st.session_state.game_3_choice

                is_win = user_choice == ai_result

                # ==================================
                # STEP 5. 코인 정산
                # ==================================

                if is_win:
                    reward = bet_coin
                else:
                    reward = -(bet_coin // 2)

                # 최신 사용자 정보 다시 확인
                users_data = ws.get_all_records()

                user_row_idx = None
                user_info = None

                for idx, user in enumerate(users_data):

                    sid = str(
                        user.get("학번", "")
                    ).strip().replace(".0", "")

                    if sid == current_sid:
                        user_row_idx = idx + 2
                        user_info = user
                        break

                if user_info is None:
                    raise ValueError("사용자 정보를 다시 찾을 수 없습니다.")

                current_balance = int(user_info.get("코인", 0))
                current_streak = int(user_info.get("연승", 0))

                if current_balance < bet_coin:
                    raise ValueError("현재 보유 코인이 부족합니다.")

                new_balance = current_balance + reward

                new_streak = (
                    current_streak + 1 if is_win else 0
                )

                # ==================================
                # STEP 6. Google Sheets 업데이트
                # ==================================

                ws.update_cell(user_row_idx, 3, new_balance)
                ws.update_cell(user_row_idx, 4, new_streak)

                st.session_state.current_user_data["코인"] = new_balance
                st.session_state.current_user_data["연승"] = new_streak

                # 결과 저장
                st.session_state.game_3_result = {
                    "actual_score": actual_score,
                    "integer_score": integer_score,
                    "ai_result": ai_result,
                    "user_choice": user_choice,
                    "bet": bet_coin,
                    "reward": reward,
                    "is_win": is_win,
                    "new_coins": new_balance,
                    "new_streak": new_streak
                }

            except Exception as e:

                st.error(f"게임 진행 중 오류가 발생했습니다: {e}")
                st.stop()

    # ======================================
    # STEP 7. 결과 화면
    # ======================================

    res = st.session_state.game_3_result

    st.markdown("---")
    st.markdown("### 🏆 최종 게임 결과")

    if res["is_win"]:
        st.balloons()
        st.success("🎉 정답입니다! 베팅 성공!")
    else:
        st.error("💥 아쉽습니다! 베팅 실패!")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("내 선택", res["user_choice"])

    with col2:
        st.metric("AI 판정", res["ai_result"])

    st.markdown(f"""
    <div style="
        background:#110022;
        border:2px solid #8A2BE2;
        padding:20px;
        border-radius:12px;
        text-align:center;
        color:white;
    ">
        <h3>📊 뉴스 유사도</h3>
        <h1 style="color:#00ffcc;">
            {res['actual_score']:.2f}%
        </h1>
        <p>홀짝 판정 기준 정수: {res['integer_score']}</p>
        <h1 style="color:#ffd700;">{res['ai_result']}</h1>
        <hr>
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

    # ======================================
    # STEP 8. 다시 도전
    # ======================================

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            reset_game_3_state()
            st.rerun()

    with col2:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            reset_game_3_state()
            change_page("main")

