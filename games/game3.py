
import streamlit as st
import time
import math
import asyncio

from modules.news_ai import summary, similarity_check, bring_article
from modules.db_handler import init_gspread
from modules.ui_components import change_page
from games.result_reveal import show_summary_before_score
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
        "game_3_summary_revealed",
        "selected_news_game_3",
        "candidates_game_3",
        "read_done_game_3",
        "game_3_article_data",
    ]

    for key in keys:
        st.session_state.pop(key, None)

    st.session_state.game_3_round = old_round + 1


# ==========================================
# 슬롯 애니메이션 CSS 수정
# common.py는 수정하지 않음
# ==========================================


def fix_game_3_slot_animation():

    st.markdown(
        """
        <style>

        /* 기사 버튼 기본 디자인 */
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

        /* 기사 제목 글씨 */
        .st-key-btn_game_3_0 button p,
        .st-key-btn_game_3_1 button p,
        .st-key-btn_game_3_2 button p {

            color: #2d1842 !important;
            font-weight: 900 !important;
            line-height: 1.5 !important;
            white-space: normal !important;
            word-break: keep-all !important;

        }

        /* 마우스 오버 효과 */
        .st-key-btn_game_3_0 button:hover,
        .st-key-btn_game_3_1 button:hover,
        .st-key-btn_game_3_2 button:hover {

            background-color: #f3e8ff !important;
            border-color: #a855f7 !important;

            transform: translateY(-2px);

            box-shadow: 5px 5px 0px #2d1842 !important;
        }

        /* 버튼 클릭 효과 */
        .st-key-btn_game_3_0 button:active,
        .st-key-btn_game_3_1 button:active,
        .st-key-btn_game_3_2 button:active {

            background-color: #e9d5ff !important;
            transform: scale(0.98);

        }

        </style>
        """,
        unsafe_allow_html=True
    )



# ==========================================
# 기사 URL 및 본문 가져오기
# ==========================================

def load_game_3_article():

    # 이미 가져온 기사가 있으면 재사용
    saved_article = st.session_state.get("game_3_article_data")

    if saved_article:

        return (
            saved_article.get("title"),
            saved_article.get("article_text"),
            saved_article.get("url")
        )

    try:

        # common.py의 뉴스 선택 기능 실행
        selection = get_game_news_selection("game_3")

        # --------------------------------------
        # 중요 수정:
        # common.py에서 None을 반환하는 경우 처리
        # --------------------------------------

        if selection is None:
            return None, None, None

        # 반환값이 튜플 또는 리스트인지 확인
        if not isinstance(selection, (tuple, list)):

            st.error(
                "뉴스 선택 함수의 반환 형식이 올바르지 않습니다."
            )

            return None, None, None

        # 반환값 개수 확인
        if len(selection) != 3:

            st.error(
                "뉴스 선택 함수에서 반환된 데이터가 올바르지 않습니다."
            )

            return None, None, None

        title, article_text, url = selection

        # common.py에서 기사 선택 또는 읽기가 진행 중인 경우
        if not title or not article_text or not url:
            return None, None, None

        url = str(url).strip()

        # URL 유효성 검사
        if not url.startswith(("http://", "https://")):

            st.error("올바른 기사 URL이 아닙니다.")
            st.write(f"가져온 URL: {url}")

            return None, None, None

        # 본문이 비어 있으면 URL로 다시 추출
        if not article_text or not str(article_text).strip():

            with st.spinner("기사 URL에서 본문을 가져오는 중입니다..."):

                extracted_title, extracted_text = bring_article(url)

                if extracted_title:
                    title = extracted_title

                article_text = extracted_text

        # 본문 최종 확인
        if not article_text or not str(article_text).strip():

            st.error("기사 본문을 가져오지 못했습니다.")
            st.caption(f"기사 URL: {url}")

            return None, None, None

        if not title:
            title = "제목을 가져오지 못한 기사"

        # 기사 정보 저장
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
    # STEP 2. 코인 확인 및 베팅
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

        sid = str(
            user.get("학번", "")
        ).strip().replace(".0", "")

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
    # STEP 3. 뉴스 선택 및 기사 본문 가져오기
    # ======================================

    st.markdown("---")
    st.markdown("### 📰 STEP 3. 뉴스 기사 선택")

    st.info(
        "분석할 뉴스 기사를 선택하세요. "
        "선택한 기사의 URL을 이용해 실제 기사 본문을 가져옵니다."
    )

    # 슬롯 애니메이션 CSS 적용
    # common.py는 수정하지 않음
    fix_game_3_slot_animation()

    # 뉴스 선택 및 본문 가져오기
    title, article_text, url = load_game_3_article()

    # 기사가 아직 선택되지 않았거나 읽는 중이면 대기
    if not title or not article_text or not url:
        return

    st.markdown("---")
    st.markdown("### 📄 선택한 뉴스 기사")

    st.markdown(f"**뉴스 제목: {title}**")

    with st.expander("뉴스 본문 확인하기", expanded=True):

        st.write(article_text)

    st.markdown(f"[기사 원문 열기]({url})")
    st.caption(f"기사 URL: {url}")

    # ======================================
    # STEP 4. AI 유사도 분석 및 홀짝 판정
    # ======================================

    if "game_3_result" not in st.session_state:

        st.markdown("---")
        st.markdown("### 🤖 STEP 4. AI 유사도 분석")

        st.info(
            "AI가 뉴스 본문을 요약하고 "
            "뉴스 제목과 본문의 유사도를 분석합니다."
        )

        if st.button(
            "🤖 뉴스 유사도 분석 및 결과 확인",
            use_container_width=True
        ):

            with st.spinner("AI가 뉴스 유사도를 분석하고 있습니다..."):

                try:

                    # 뉴스 본문 요약
                    summary_text = asyncio.run(summary(article_text))

                    if not summary_text:

                        raise ValueError(
                            "뉴스 요약 결과가 비어 있습니다."
                        )

                    # 제목과 요약문의 유사도 계산
                    actual_score = similarity_check(
                        summary_text,
                        title
                    )

                    actual_score = float(actual_score)

                    if (
                        not math.isfinite(actual_score)
                        or not 0 <= actual_score <= 100
                    ):

                        raise ValueError(
                            "유사도 점수가 올바르지 않습니다."
                        )

                    # 정수 부분만 사용
                    integer_score = int(actual_score)

                    # 홀짝 판정
                    ai_result = (
                        "짝" if integer_score % 2 == 0 else "홀"
                    )

                    user_choice = st.session_state.game_3_choice

                    is_win = user_choice == ai_result

                    # ==================================
                    # STEP 5. 코인 정산
                    # ==================================

                    if is_win:
                        reward = bet_coin
                    else:
                        reward = -(bet_coin // 2)

                    # 최신 사용자 정보 확인
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

                        raise ValueError(
                            "사용자 정보를 다시 찾을 수 없습니다."
                        )

                    current_balance = int(user_info.get("코인", 0))
                    current_streak = int(user_info.get("연승", 0))

                    if current_balance < bet_coin:

                        raise ValueError(
                            "현재 보유 코인이 부족합니다."
                        )

                    new_balance = max(
                        0,
                        current_balance + reward
                    )

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
                        "new_streak": new_streak,
                        "title": title,
                        "url": url,
                        "summary": summary_text

                    }

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"게임 진행 중 오류가 발생했습니다: {e}"
                    )

    # ======================================
    # STEP 7. 최종 결과 화면
    # ======================================

    if "game_3_result" not in st.session_state:
        return

    res = st.session_state.game_3_result

    show_summary_before_score(res["summary"], "game_3_summary_revealed")

    st.markdown("---")
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
        st.metric("AI 판정", res["ai_result"])

    st.markdown("### 📊 AI 분석 결과")

    st.metric(
        "뉴스 제목-본문 유사도",
        f"{res['actual_score']:.2f}%"
    )

    st.progress(
        max(
            0.0,
            min(1.0, res["actual_score"] / 100)
        )
    )

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
        <h3>뉴스 유사도</h3>

        <h1 style="color:#00ffcc;">
            {res['actual_score']:.2f}%
        </h1>

        <p>홀짝 판정 기준 정수: {res['integer_score']}</p>

        <h1 style="color:#ffd700;">
            {res['ai_result']}
        </h1>

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
    # STEP 8. 다시 도전하기 / 메인으로
    # ======================================

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🔄 다시 도전하기",
            use_container_width=True
        ):

            reset_game_3_state()
            st.rerun()

    with col2:

        if st.button(
            "⬅️ 메인으로 돌아가기",
            use_container_width=True
        ):

            reset_game_3_state()
            change_page("main")
