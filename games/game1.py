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
    
    if "game_1_bet" not in st.session_state:
    current_coins = int(st.session_state.current_user_data.get('코인', 0))

    # 🔥 반짝이는 화려한 UI 스타일 및 애니메이션 정의
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Gowun+Dodum&family=Noto+Sans+KR:wght@700;900&display=swap');

        .bet-card-container {
            font-family: 'Gowun Dodum', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #110022 0%, #1a0933 50%, #0d001a 100%);
            border: 2px solid #00ffcc;
            border-radius: 20px;
            padding: 22px 18px;
            text-align: center;
            box-shadow: 0 0 20px rgba(0, 255, 204, 0.35);
            animation: neonPulse 3s infinite alternate;
            margin-bottom: 20px;
        }

        @keyframes neonPulse {
            0% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
            50% { border-color: #ff00ff; box-shadow: 0 0 25px rgba(255, 0, 255, 0.6); }
            100% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
        }

        .bet-header-title {
            font-family: 'Press Start 2P', monospace;
            font-size: 1.1rem;
            color: #fffb00;
            text-shadow: 0 0 10px #ff00ff, 0 0 20px #00ffff;
            margin-bottom: 14px;
            letter-spacing: 1px;
        }

        .coin-balance-badge {
            background: rgba(255, 255, 255, 0.07);
            border: 1.5px solid rgba(0, 255, 204, 0.5);
            border-radius: 30px;
            padding: 8px 18px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
        }

        .payout-preview-box {
            background: linear-gradient(135deg, rgba(255,215,0,0.15) 0%, rgba(255,0,255,0.15) 100%);
            border: 2px dashed #ffd700;
            border-radius: 16px;
            padding: 15px;
            margin: 18px 0 10px 0;
            animation: payoutFloat 2.5s ease-in-out infinite alternate;
        }

        @keyframes payoutFloat {
            0% { transform: scale(0.98); box-shadow: 0 0 10px rgba(255, 215, 0, 0.3); }
            100% { transform: scale(1.02); box-shadow: 0 0 22px rgba(255, 215, 0, 0.7); }
        }

        .payout-title {
            font-size: 0.88rem;
            color: #e2e8f0;
            margin-bottom: 4px;
            font-weight: bold;
        }

        .payout-value {
            font-size: 1.9rem;
            font-weight: 900;
            color: #ffd700;
            text-shadow: 0 0 10px #ffd700, 0 0 20px #ff00ff;
            letter-spacing: 0.5px;
        }

        .jackpot-tag {
            background: linear-gradient(90deg, #ff00ff, #8a2be2);
            color: #ffffff;
            font-size: 0.75rem;
            font-weight: 900;
            padding: 3px 8px;
            border-radius: 12px;
            margin-left: 8px;
            vertical-align: middle;
            box-shadow: 0 0 8px #ff00ff;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # 1. 상단 화려한 타이틀 및 현재 잔액
    st.markdown(
        f"""
        <div class="bet-card-container">
            <div class="bet-header-title">🎰 STEP 1: BETTING PLACE 🎰</div>
            <div class="coin-balance-badge">
                <span style="color:#ffffff; font-weight:bold;">보유 코인:</span>
                <span style="color:#00ffcc; font-weight:900; font-size:1.2rem; text-shadow:0 0 8px #00ffcc;">
                    🪙 {current_coins:,} C
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. 베팅 금액 선택 (슬라이더 + 정밀 입력)
    min_bet = 100
    max_bet = max(100, current_coins)
    default_bet = min(500, max_bet)

    col_bet1, col_bet2 = st.columns([2.2, 1])

    with col_bet1:
        bet_val = st.slider(
            "🎚️ 베팅 금액 조절", 
            min_value=min_bet, 
            max_value=max_bet, 
            step=100, 
            value=default_bet,
            key="game1_bet_slider"
        )

    with col_bet2:
        bet_val = st.number_input(
            "✏️ 수치 직접 입력", 
            min_value=min_bet, 
            max_value=max_bet, 
            step=100, 
            value=bet_val,
            key="game1_bet_num"
        )

    # 3. 실시간 보상(100배 대박 금액) 계산
    potential_jackpot = bet_val * 100

    # 4. 반짝이는 실시간 예상 획득 금액 표시 카드
    st.markdown(
        f"""
        <div class="payout-preview-box">
            <div class="payout-title">✨ 대박 성공 시 획득 가능 금액 (오차 0점 완벽 예측) ✨</div>
            <div class="payout-value">
                +{potential_jackpot:,} C <span class="jackpot-tag">100x JACKPOT</span>
            </div>
        </div>
        <br>
        """,
        unsafe_allow_html=True
    )

    # 5. 베팅 확정 버튼
    if st.button("🔥 베팅 완료 & 게임 시작하기 🔥", use_container_width=True):
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
