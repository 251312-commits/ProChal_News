import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread, init_news_sheet
from modules.ui_components import change_page
from games.common import get_game_news_selection

ws = init_gspread()
ws_news = init_news_sheet()

# 정의된 함수: show_game_1

def show_game_1():
    st.title("🎮 게임 1: 뉴스 유사도 예측 게임")

    # [1단계] 베팅 금액 선택
    if "game_1_bet" not in st.session_state:
        current_coins = int(st.session_state.current_user_data.get('코인', 0))
        st.markdown("### 💰 1단계: 베팅 금액 선택")
        st.write(f"현재 보유 코인: **{current_coins:,} C**")
        
        bet_val = st.number_input(
            "베팅할 코인을 입력하세요", 
            min_value=100, 
            max_value=max(100, current_coins), 
            step=100, 
            value=min(500, max(100, current_coins))
        )
        
        if st.button("🎲 베팅 금액 확정", use_container_width=True):
            if current_coins < 100:
                st.error("코인이 부족합니다! (최소 100 C 필요)")
                return
            st.session_state.game_1_bet = bet_val
            st.rerun()
        return

    # [2단계 & 3단계] 기사 선택
    title, article_text, url = get_game_news_selection("game_1")
    if not title:
        return

    # [4단계] 점수 예측 UI
    if "game_1_predicted_score" not in st.session_state:
        st.markdown("---")
        st.markdown("### 🎯 4단계: AI 유사도 점수 예측")
        st.caption("AI가 제목과 본문을 분석해 산출할 유사도 점수(00~99점)를 예측해 보세요!")

        @st.fragment
        def render_neon_digit_picker():
            if "tens_val" not in st.session_state:
                st.session_state.tens_val = 5
            if "ones_val" not in st.session_state:
                st.session_state.ones_val = 0

            st.markdown(
                """
                <style>
                .digit-display-container { display: flex; justify-content: center; align-items: center; margin: 15px 0; }
                .large-digit {
                    font-family: 'Press Start 2P', monospace, sans-serif;
                    font-size: 4.2rem; font-weight: 900; color: #00ffcc;
                    text-shadow: 0 0 15px #00ffcc, 0 0 25px #ff00ff;
                    background: #110022; border: 3.5px solid #8A2BE2; border-radius: 12px;
                    padding: 10px 20px; min-width: 85px; text-align: center;
                    box-shadow: 0 0 15px rgba(138, 43, 226, 0.6);
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            _, col_tens, col_ones, _ = st.columns([1, 1.2, 1.2, 1])

            with col_tens:
                st.markdown("<p style='text-align:center; font-weight:bold; color:#a382de; margin-bottom:5px;'>십의 자리</p>", unsafe_allow_html=True)
                if st.button("▲", key="btn_tens_up", use_container_width=True):
                    st.session_state.tens_val = (st.session_state.tens_val + 1) % 10
                    st.rerun(scope="fragment")
                st.markdown(f"<div class='digit-display-container'><div class='large-digit'>{st.session_state.tens_val}</div></div>", unsafe_allow_html=True)
                if st.button("▼", key="btn_tens_down", use_container_width=True):
                    st.session_state.tens_val = (st.session_state.tens_val - 1) % 10
                    st.rerun(scope="fragment")

            with col_ones:
                st.markdown("<p style='text-align:center; font-weight:bold; color:#a382de; margin-bottom:5px;'>일의 자리</p>", unsafe_allow_html=True)
                if st.button("▲", key="btn_ones_up", use_container_width=True):
                    st.session_state.ones_val = (st.session_state.ones_val + 1) % 10
                    st.rerun(scope="fragment")
                st.markdown(f"<div class='digit-display-container'><div class='large-digit'>{st.session_state.ones_val}</div></div>", unsafe_allow_html=True)
                if st.button("▼", key="btn_ones_down", use_container_width=True):
                    st.session_state.ones_val = (st.session_state.ones_val - 1) % 10
                    st.rerun(scope="fragment")

            pred_score = st.session_state.tens_val * 10 + st.session_state.ones_val
            st.markdown(f"<h3 style='text-align:center; color:#fffb00; margin-top:15px;'>내 예측 점수: {pred_score:02d}점</h3>", unsafe_allow_html=True)

            if st.button("✅ 선택 완료 (예측 점수 제출)", use_container_width=True):
                st.session_state.game_1_predicted_score = pred_score
                st.rerun()

        render_neon_digit_picker()
        return

    # [5단계 & 6단계] AI 점수 측정 및 정산
    pred_score = st.session_state.game_1_predicted_score
    bet_coin = st.session_state.game_1_bet

    if "game_1_result" not in st.session_state:
        with st.spinner("🤖 AI가 유사도를 분석 중입니다..."):
            summary_text = summary(article_text)
            actual_score = similarity_check(summary_text, title)
            
            # diff 변수 선언 추가
            diff = abs(pred_score - actual_score)

            if diff == 0:
                reward = int(bet_coin * 100.0)
                is_win = True
                result_msg = f"🎉 대박 성공! (오차 {diff}점)"
            else:
                reward = -bet_coin
                is_win = False
                result_msg = f"💥 실패 (오차 {diff}점)"

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
                "actual_score": actual_score,
                "diff": diff,
                "reward": reward,
                "is_win": is_win,
                "msg": result_msg,
                "new_coins": new_coins,
                "new_streak": new_streak
            }

    # 최종 결과 출력
    res = st.session_state.game_1_result
    st.markdown("---")
    st.markdown("### 🏆 6단계: 최종 결과")

    if res["is_win"]:
        st.balloons()
        st.success(f"{res['msg']} | 획득 코인: +{res['reward']:,} C")
    else:
        st.error(f"{res['msg']} | 차감 코인: {res['reward']:,} C")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1: st.metric("내 예측 점수", f"{pred_score:02d}점")
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
            "read_done_game_1", "game_1_predicted_score", "game_1_result",
            "tens_val", "ones_val"
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
