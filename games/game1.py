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

    # [1단계] 베팅 금액 선택 (화려한 네온 UI 및 dynamic 코인 스택 적용)
    if "game_1_bet" not in st.session_state:
        current_coins = int(st.session_state.current_user_data.get('코인', 0))
        min_bet = 1000
        
        # 코인이 최소 베팅 금액보다 적을 경우 예외 처리
        if current_coins < min_bet:
            st.error(f"⚠️ 베팅을 위한 코인이 부족합니다! (최소 베팅금: {min_bet:,} C / 보유: {current_coins:,} C)")
            if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
                change_page('main')
            return

        # 베팅 화면 전용 카지노 네온 CSS 스타일링
        st.markdown(
            """
            <style>
            .bet-card-container {
                background: linear-gradient(135deg, #110022 0%, #1a0933 50%, #0d001a 100%);
                border: 2px solid #00ffcc;
                border-radius: 20px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 0 20px rgba(0, 255, 204, 0.4);
                margin-bottom: 15px;
                animation: pulseGlow 3s infinite alternate;
            }
            @keyframes pulseGlow {
                0% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
                50% { border-color: #ff00ff; box-shadow: 0 0 25px rgba(255, 0, 255, 0.6); }
                100% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
            }
            .bet-header-title {
                font-family: 'Press Start 2P', monospace;
                font-size: 1.1rem;
                color: #fffb00;
                text-shadow: 0 0 8px #ff00ff, 0 0 15px #00ffff;
                margin-bottom: 8px;
            }
            .coin-stack-box {
                min-height: 110px;
                display: flex;
                flex-direction: column-reverse;
                align-items: center;
                justify-content: center;
                margin: 15px 0;
                padding: 12px;
                background: rgba(0, 0, 0, 0.45);
                border-radius: 16px;
                border: 1.5px dashed rgba(255, 215, 0, 0.5);
            }
            .coin-row {
                font-size: 1.8rem;
                letter-spacing: 3px;
                animation: popIn 0.25s ease-out;
                filter: drop-shadow(0 0 8px #ffd700);
            }
            @keyframes popIn {
                0% { transform: scale(0.6); opacity: 0.5; }
                100% { transform: scale(1); opacity: 1; }
            }
            .payout-card {
                background: linear-gradient(90deg, rgba(255,0,255,0.2) 0%, rgba(0,255,204,0.2) 100%);
                border: 2px solid #ff00ff;
                border-radius: 14px;
                padding: 12px;
                margin: 15px 0;
                text-align: center;
                box-shadow: 0 0 15px rgba(255, 0, 255, 0.4);
            }
            .payout-amount {
                font-size: 1.7rem;
                font-weight: 900;
                color: #00ffcc;
                text-shadow: 0 0 12px #00ffcc;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # 상단 헤더 카드
        st.markdown(
            f"""
            <div class="bet-card-container">
                <div class="bet-header-title">🎰 STEP 1: BETTING PLACE</div>
                <div style="font-size: 1rem; color: #ffffff; font-weight: bold;">
                    현재 보유 코인: <span style="color:#ffd700;">🪙 {current_coins:,} C</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 슬라이더로 베팅 금액 선택 (최소 1,000 C ~ 최대 올인)
        step_val = 1000 if (current_coins - min_bet) >= 1000 else 100
        bet_val = st.slider(
            "💰 베팅할 금액을 선택하세요",
            min_value=min_bet,
            max_value=current_coins,
            step=step_val,
            value=min(5000, current_coins)
        )

        # 베팅 비율에 따라 동적으로 코인 아이콘 개수 산출 (1개 ~ 최대 10개 탑 쌓기 연출)
        bet_ratio = (bet_val - min_bet) / max(1, (current_coins - min_bet)) if current_coins > min_bet else 1.0
        coin_count = int(1 + bet_ratio * 9)

        # 코인 탑 Visual 생성 (5개 단위 줄바꿈)
        coins_html = ""
        for i in range(0, coin_count, 5):
            chunk = min(5, coin_count - i)
            coins_html = f"<div class='coin-row'>{'🪙' * chunk}</div>" + coins_html

        # 정답(오차 0점) 달성 시 획득 가능한 최고 금액 (100배)
        max_reward = bet_val * 100

        # 동적 코인 탑 & 예상 최고 수령액 카드 출력
        st.markdown(
            f"""
            <div class="coin-stack-box">
                {coins_html}
                <div style="color:#ffd700; font-size:0.9rem; margin-top:8px; font-weight:800;">
                    현재 선택 칩: {bet_val:,} C
                </div>
            </div>

            <div class="payout-card">
                <div style="font-size:0.85rem; color:#ffffff; font-weight:bold;">✨ 정답(오차 0점) 적중 시 최대 획득 금액 (100배)</div>
                <div class="payout-amount">+{max_reward:,} C</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 하단 버튼부 (올인 버튼 & 확정 버튼)
        col_b1, col_b2 = st.columns([1, 2])
        with col_b1:
            if st.button("💥 ALL-IN (올인)", use_container_width=True):
                st.session_state.game_1_bet = current_coins
                st.rerun()

        with col_b2:
            if st.button("🎲 베팅 확정 & 게임 시작", use_container_width=True):
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
