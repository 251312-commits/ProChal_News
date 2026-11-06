import asyncio
from pathlib import Path

import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread, init_news_sheet
from modules.ui_components import change_page
from views.ranking import fetch_ranking_data
from games.result_reveal import show_summary_before_score
from games.game1_prediction_ui import render_game1_prediction_picker
from games.common import get_game_news_selection, check_user_coins_or_pop_bank, render_betting_ui

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

        # The existing background is assets/bet_background.jpg (not bg.png).
        confirmed_bet = render_betting_ui(
            current_coins=current_coins,
            users_data=users_data,
            current_sid=current_sid,
            current_nickname=current_nickname,
            bg_image_path=str(Path(__file__).resolve().parents[1] / "assets" / "bet_background.jpg"),
            payout_multiplier=GAME_1_WIN_MULTIPLIER,
            title="title",  # 나중에 실제 게임 제목으로 교체
        )

        if confirmed_bet is not None:
            st.session_state.game_1_bet = confirmed_bet
            st.rerun()

        return

    # [2단계 & 3단계] 기사 선택 / 30초 읽기
    title, article_text, url = get_game_news_selection("game_1")
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
        with st.spinner("🤖 AI가 유사도를 분석 중입니다..."):
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
