# 업다운 (하) ½ (2배)

import random
import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread, init_news_sheet
from modules.ui_components import change_page  # show_placeholder_page 대신 change_page 사용
from games.common import get_game_news_selection

ws = init_gspread()
ws_news = init_news_sheet()

# 기존 def show_game_2(): show_placeholder_page("게임 2") 줄은 지우고 
# 아래의 전체 구현 코드로 대체합니다.

def show_game_2():
    st.title("🎮 게임 2: 뉴스 유사도 HIGH / LOW 게임")

    # [1단계] 베팅 금액 선택
    if "game_2_bet" not in st.session_state:
        current_coins = int(st.session_state.current_user_data.get('코인', 0))
        current_sid = str(st.session_state.get('current_user', '')).strip().replace('.0', '')
        min_bet = 1000
        
        if current_coins < min_bet:
            st.error(f"⚠️ 베팅을 위한 코인이 부족합니다! (최소 베팅금: {min_bet:,} C / 보유: {current_coins:,} C)")
            if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
                change_page('main')
            return

        if "ranking_users_cache" not in st.session_state:
            try:
                st.session_state.ranking_users_cache = ws.get_all_records()
            except Exception:
                st.session_state.ranking_users_cache = []

        users_data = st.session_state.ranking_users_cache

        default_bet = max(min_bet, ((current_coins // 2) // 50) * 50)
        if "bet_slider_key_2" not in st.session_state:
            st.session_state["bet_slider_key_2"] = default_bet

        bet_val = st.slider(
            "💰 베팅할 금액을 선택하세요",
            min_value=min_bet,
            max_value=current_coins,
            step=50,
            key="bet_slider_key_2"
        )

        bet_ratio = (bet_val - min_bet) / max(1, (current_coins - min_bet)) if current_coins > min_bet else 1.0
        is_all_in = (bet_val == current_coins)

        pulse_speed = max(0.35, round(1.2 - bet_ratio * 0.85, 2))
        heartbeat_interval = int(pulse_speed * 1000)
        sound_vol = round(0.45 + bet_ratio * 1.15, 2)

        glow_size = int(14 + bet_ratio * 46)
        glow_opacity = round(0.4 + bet_ratio * 0.6, 2)
        
        if bet_ratio < 0.4:
            primary_color = "#00e5ff"
            border_color = "#0088ff"
            card_bg_glow = f"rgba(0, 229, 255, {glow_opacity})"
        elif bet_ratio < 0.8:
            primary_color = "#00ff88"
            border_color = "#00cc66"
            card_bg_glow = f"rgba(0, 255, 136, {glow_opacity})"
        else:
            primary_color = "#ffd700"
            border_color = "#ff3300"
            card_bg_glow = f"rgba(255, 215, 0, {glow_opacity})"

        allin_class = "allin-multi-glow" if is_all_in else ""

        st.markdown(
            f"""
            <style>
            .bet-card-container {{
                background: linear-gradient(135deg, #001122 0%, #001a33 50%, #000d1a 100%);
                border: 2px solid {border_color};
                border-radius: 20px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 0 {glow_size}px {card_bg_glow};
                margin-bottom: 15px;
                transition: all 0.2s ease;
            }}
            .coin-pile-wrapper {{
                display: flex;
                justify-content: center;
                align-items: flex-end;
                gap: 12px;
                min-height: 150px;
                padding: 22px 10px 15px 10px;
                background: radial-gradient(ellipse at bottom, rgba(0, 229, 255, {0.12 + bet_ratio * 0.38}) 0%, rgba(0, 10, 20, 0.85) 75%);
                border-radius: 16px;
                border: 1.5px dashed {border_color};
                box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.9), 0 0 {glow_size}px {card_bg_glow};
                margin: 15px 0;
                transition: all 0.2s ease;
                animation: pulseScale {pulse_speed}s infinite ease-in-out;
            }}
            .payout-card {{
                background: linear-gradient(90deg, rgba(0,229,255,0.2) 0%, rgba(0,255,136,0.2) 100%);
                border: 2px solid {border_color};
                border-radius: 14px;
                padding: 12px;
                text-align: center;
                box-shadow: 0 0 {glow_size}px {card_bg_glow};
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                transition: all 0.2s ease;
                animation: pulseScale {pulse_speed}s infinite ease-in-out;
            }}

            @keyframes pulseScale {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale({1.0 + bet_ratio * 0.045:.3f}); }}
                100% {{ transform: scale(1); }}
            }}

            .allin-multi-glow {{
                animation: multiNeonCycle 0.6s infinite linear, pulseScale {pulse_speed}s infinite ease-in-out !important;
            }}
            @keyframes multiNeonCycle {{
                0% {{ border-color: #00e5ff; box-shadow: 0 0 40px #00e5ff, inset 0 0 15px #00e5ff; }}
                25% {{ border-color: #00ff88; box-shadow: 0 0 45px #00ff88, inset 0 0 15px #00ff88; }}
                50% {{ border-color: #ffd700; box-shadow: 0 0 50px #ffd700, inset 0 0 20px #ffd700; }}
                75% {{ border-color: #ff0055; box-shadow: 0 0 45px #ff0055, inset 0 0 15px #ff0055; }}
                100% {{ border-color: #00e5ff; box-shadow: 0 0 40px #00e5ff, inset 0 0 15px #00e5ff; }}
            }}

            .bet-header-title {{
                font-family: 'Press Start 2P', monospace;
                font-size: 1.1rem;
                color: #00e5ff;
                text-shadow: 0 0 8px #0088ff, 0 0 15px #00ff88;
                margin-bottom: 8px;
            }}
            .coin-stack-col {{ display: flex; flex-direction: column-reverse; align-items: center; }}
            .gold-coin-item {{
                width: 46px; height: 12px; border-radius: 50%;
                background: linear-gradient(180deg, #FFE57F 0%, #FFC107 40%, #FF8F00 70%, #A76D00 100%);
                border: 1px solid #FFF59D; box-shadow: 0 3px 0 #5D4037, inset 0 1px 2px rgba(255, 255, 255, 0.9);
                margin-top: -6px;
            }}
            .gold-coin-item.top {{
                background: radial-gradient(ellipse at 35% 35%, #FFFFFF 0%, #FFEE58 40%, #FFA000 85%);
                border: 1.5px solid #FFFFFF; box-shadow: 0 3px 0 #5D4037, 0 0 12px rgba(255, 215, 0, 0.9);
            }}
            .payout-amount {{
                font-size: 1.6rem; font-weight: 900; color: {primary_color}; text-shadow: 0 0 12px {primary_color};
            }}
            .rank-sim-card {{
                background: linear-gradient(135deg, rgba(0, 20, 40, 0.9) 0%, rgba(0, 35, 60, 0.9) 100%);
                border: 2px solid {border_color}; border-radius: 14px; padding: 12px 14px;
                box-shadow: 0 0 {glow_size}px {card_bg_glow}; height: 100%;
                display: flex; flex-direction: column; justify-content: space-between; transition: all 0.2s ease;
            }}
            .rank-up-badge {{ color: #00ff88; font-size: 1.05rem; font-weight: 900; text-shadow: 0 0 8px #00ff88; }}
            .rival-row {{
                font-size: 0.82rem; color: #ffffff; background: rgba(0, 0, 0, 0.4);
                padding: 4px 8px; border-radius: 8px; margin-top: 4px; border-left: 3px solid #00e5ff;
            }}
            .target-num-card {{
                background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%);
                border: 3px solid #00e5ff; border-radius: 16px; padding: 20px;
                text-align: center; box-shadow: 0 0 20px rgba(0, 229, 255, 0.5); margin: 20px 0;
            }}
            .target-digit {{
                font-family: 'Press Start 2P', monospace, sans-serif;
                font-size: 4rem; font-weight: 900; color: #00ff88;
                text-shadow: 0 0 15px #00ff88, 0 0 25px #00e5ff;
            }}
            </style>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            f"""
            <script>
            (function() {{
                if (window.heartbeatInterval) clearInterval(window.heartbeatInterval);
                try {{
                    const ctx = window.heartbeatAudioCtx || new (window.AudioContext || window.webkitAudioContext)();
                    window.heartbeatAudioCtx = ctx;
                    const intervalMs = {heartbeat_interval};
                    const vol = {sound_vol};
                    function playBeat() {{
                        if (ctx.state === 'suspended') ctx.resume();
                        const now = ctx.currentTime;
                        const osc1 = ctx.createOscillator();
                        const gain1 = ctx.createGain();
                        osc1.type = 'sine'; osc1.frequency.setValueAtTime(120, now);
                        osc1.frequency.exponentialRampToValueAtTime(22, now + 0.18);
                        gain1.gain.setValueAtTime(vol, now); gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.18);
                        osc1.connect(gain1); gain1.connect(ctx.destination);
                        osc1.start(now); osc1.stop(now + 0.18);

                        const osc2 = ctx.createOscillator();
                        const gain2 = ctx.createGain();
                        osc2.type = 'sine'; osc2.frequency.setValueAtTime(95, now + 0.22);
                        osc2.frequency.exponentialRampToValueAtTime(18, now + 0.42);
                        gain2.gain.setValueAtTime(vol * 0.8, now + 0.22);
                        gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.42);
                        osc2.connect(gain2); gain2.connect(ctx.destination);
                        osc2.start(now + 0.22); osc2.stop(now + 0.42);
                    }}
                    window.heartbeatInterval = setInterval(playBeat, intervalMs);
                    playBeat();
                }} catch(e) {{}}
            }})();
            </script>
            """,
            unsafe_allow_html=True
        )

        if is_all_in:
            st.markdown(
                """
                <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js"></script>
                <script>
                    if (typeof confetti === 'function') {
                        confetti({
                            particleCount: 120, spread: 125, origin: { y: 0.6 },
                            colors: ['#00e5ff', '#00ff88', '#ffd700', '#ffffff', '#ff0055']
                        });
                    }
                </script>
                """,
                unsafe_allow_html=True
            )

        st.markdown(
            f"""
            <div class="bet-card-container {allin_class}">
                <div class="bet-header-title">🎰 STEP 1: BETTING PLACE</div>
                <div style="font-size: 1rem; color: #ffffff; font-weight: bold;">
                    현재 보유 코인: <span style="color:#ffd700;">🪙 {current_coins:,} C</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        total_coins = int(4 + bet_ratio * 36)
        num_cols = min(5, max(1, (total_coins + 7) // 8))
        weights = [1.0] if num_cols == 1 else [1.0, 1.0] if num_cols == 2 else [1.0, 2.2, 1.0] if num_cols == 3 else [1.0, 2.2, 2.2, 1.0] if num_cols == 4 else [1.0, 2.0, 3.5, 2.0, 1.0]
        sum_w = sum(weights)
        raw_heights = [int(round(total_coins * (w / sum_w))) for w in weights]
        diff = total_coins - sum(raw_heights)
        center_idx = num_cols // 2
        indices_order = sorted(range(num_cols), key=lambda x: abs(x - center_idx))
        for i in range(abs(diff)):
            idx = indices_order[i % num_cols]
            if diff > 0: raw_heights[idx] += 1
            elif diff < 0 and raw_heights[idx] > 1: raw_heights[idx] -= 1

        cols_html = ""
        for c, col_h in enumerate(raw_heights):
            coins_in_col_html = "".join([f'<div class="gold-coin-item{" top" if h == col_h - 1 else ""}"></div>' for h in range(col_h)])
            cols_html += f'<div class="coin-stack-col">{coins_in_col_html}</div>'

        st.markdown(
            f"""
            <div class="coin-pile-wrapper {allin_class}">
                {cols_html}
            </div>
            <div style="text-align:center; color:#00e5ff; font-size:0.95rem; font-weight:800; margin-top:-5px; margin-bottom:15px;">
                현재 선택 칩: {bet_val:,} C {"(🔥 ALL-IN!)" if is_all_in else ""}
            </div>
            """,
            unsafe_allow_html=True
        )

        max_reward = bet_val
        simulated_total_coins = current_coins + max_reward

        processed_users = []
        for u in users_data:
            try: c_val = int(u.get('코인', 0))
            except Exception: c_val = 0
            processed_users.append({
                'id': str(u.get('학번', '')).strip().replace('.0', ''),
                'nickname': str(u.get('아이디', '익명')).strip(),
                'coins': c_val
            })

        curr_sorted = sorted(processed_users, key=lambda x: x['coins'], reverse=True)
        curr_rank = next((idx + 1 for idx, u in enumerate(curr_sorted) if u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', '')), len(curr_sorted) + 1)

        sim_list = [{
            'id': u['id'], 'nickname': u['nickname'],
            'coins': simulated_total_coins if (u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', '')) else u['coins'],
            'is_me': (u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', ''))
        } for u in processed_users]

        sim_sorted = sorted(sim_list, key=lambda x: x['coins'], reverse=True)
        sim_me_idx = next((idx for idx, u in enumerate(sim_sorted) if u['is_me']), None)
        sim_rank = sim_me_idx + 1 if sim_me_idx is not None else len(sim_sorted) + 1

        rank_climb = curr_rank - sim_rank if curr_rank else 0
        above_user = sim_sorted[sim_me_idx - 1] if sim_me_idx and sim_me_idx > 0 else None
        below_user = sim_sorted[sim_me_idx + 1] if sim_me_idx is not None and sim_me_idx < len(sim_sorted) - 1 else None

        above_str = f"🔺 <b>위:</b> {above_user['nickname']} <span style='color:#ff9999;'>({above_user['coins'] - simulated_total_coins:,} C 부족)</span>" if above_user else "👑 <b>예상 랭킹 1위 달성!</b>"
        below_str = f"🔻 <b>아래:</b> {below_user['nickname']} <span style='color:#00ff88;'>({simulated_total_coins - below_user['coins']:,} C 제침)</span>" if below_user else "🛡️ <b>최하위 라이벌 없음</b>"

        col_card1, col_card2 = st.columns(2)
        with col_card1:
            st.markdown(
                f"""
                <div class="payout-card {allin_class}">
                    <div style="font-size:0.8rem; color:#ffffff; font-weight:bold;">✨ 적중 시 보상금</div>
                    <div class="payout-amount">+{max_reward:,} C</div>
                    <div style="font-size:0.75rem; color:#00ff88; margin-top:4px;">(배팅 코인 2배 환급 / 실익 1배)</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_card2:
            rank_climb_text = f"▲ {rank_climb}등 상승!" if rank_climb > 0 else "순위 유지"
            st.markdown(
                f"""
                <div class="rank-sim-card {allin_class}">
                    <div>
                        <div style="font-size:0.78rem; color:#aaa; font-weight:bold;">🏆 승리 시 예상 랭킹</div>
                        <div style="font-size:1.1rem; font-weight:900; color:#fff;">
                            {curr_rank}위 ➔ <span style="color:#00e5ff;">{sim_rank}위</span>
                            <span class="rank-up-badge">({rank_climb_text})</span>
                        </div>
                    </div>
                    <div style="margin-top:6px;">
                        <div class="rival-row">{above_str}</div>
                        <div class="rival-row">{below_str}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

        if st.button("🎲 베팅 확정 & 게임 시작", use_container_width=True):
            st.session_state.game_2_bet = bet_val
            st.rerun()

        return

    # [2단계] 뉴스 불러오기 및 제시
    title, article_text, url = get_game_news_selection("game_2")
    if not title:
        return

    # [3단계] '다음으로' 버튼 클릭 전
    if "game_2_target_num" not in st.session_state:
        st.markdown("---")
        st.markdown("### 📰 뉴스 기사 확인")
        st.markdown(f"#### **제목: {title}**")
        with st.expander("📄 뉴스 본문 전체보기", expanded=True):
            st.write(article_text)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("▶️ 다음으로 (기준 점수 뽑기)", use_container_width=True):
            st.session_state.game_2_target_num = random.randint(0, 100)
            st.rerun()
        return

    # [4단계] 임의의 숫자 제시 및 HIGH / LOW 선택 UI
    target_num = st.session_state.game_2_target_num

    if "game_2_user_choice" not in st.session_state:
        st.markdown("---")
        st.markdown("### 🎯 HIGH / LOW 예측 선택")
        st.info(f"📌 기사 제목: **{title}**")

        st.markdown(
            f"""
            <div class="target-num-card">
                <div style="color:#ffffff; font-weight:bold; font-size:1.1rem; margin-bottom:8px;">🎲 뽑힌 기준 점수</div>
                <div class="target-digit">{target_num}점</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("이 기사 제목과 본문의 **실제 AI 유사도 점수**는 기준 점수보다 **높을까요(이상), 낮을까요(미만)?**")

        col_high, col_low = st.columns(2)
        with col_high:
            if st.button(f"⬆️ HIGH (이상: ≥ {target_num}점)", use_container_width=True):
                st.session_state.game_2_user_choice = "HIGH"
                st.rerun()

        with col_low:
            if st.button(f"⬇️ LOW (미만: < {target_num}점)", use_container_width=True):
                st.session_state.game_2_user_choice = "LOW"
                st.rerun()

        return

    # [5단계] AI 측정 및 결과 판정
    bet_coin = st.session_state.game_2_bet
    user_choice = st.session_state.game_2_user_choice

    if "game_2_result" not in st.session_state:
        with st.spinner("🤖 AI가 유사도를 분석 중입니다..."):
            summary_text = summary(article_text)
            actual_score = similarity_check(summary_text, title)

            if user_choice == "HIGH":
                is_win = (actual_score >= target_num)
            else:
                is_win = (actual_score < target_num)

            if is_win:
                reward = bet_coin
                result_msg = f"🎉 예측 성공! (실제 유사도: {actual_score}점)"
            else:
                reward = -bet_coin
                result_msg = f"💥 예측 실패! (실제 유사도: {actual_score}점)"

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

            st.session_state.game_2_result = {
                "actual_score": actual_score,
                "target_num": target_num,
                "reward": reward,
                "is_win": is_win,
                "msg": result_msg,
                "new_coins": new_coins,
                "new_streak": new_streak
            }

    # [6단계] 최종 결과 출력
    res = st.session_state.game_2_result
    st.markdown("---")
    st.markdown("### 🏆 6단계: 최종 결과")

    if res["is_win"]:
        st.balloons()
        st.success(f"{res['msg']} | 획득 코인: +{res['reward']:,} C")
    else:
        st.error(f"{res['msg']} | 차감 코인: -{abs(res['reward']):,} C")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1: st.metric("기준 점수", f"{res['target_num']}점")
    with col_r2: st.metric("내 선택", "이상 (≥)" if user_choice == "HIGH" else "미만 (<)")
    with col_r3: st.metric("AI 실제 유사도", f"{res['actual_score']}점")

    st.markdown(
        f"""
        <div style="background:#001122; border:2px solid #00e5ff; padding:15px; border-radius:10px; text-align:center; margin:15px 0;">
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 보유 코인: <span style="color:#00ff88;">{res['new_coins']:,} C</span></p>
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 연승 기록: <span style="color:#00e5ff;">{res['new_streak']} 연승</span></p>
        </div>
        """,
        unsafe_allow_html=True
    )

    def reset_game_2_state():
        keys_to_clear = [
            "game_2_bet", "selected_news_game_2", "candidates_game_2", 
            "read_done_game_2", "game_2_target_num", "game_2_user_choice", "game_2_result"
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            reset_game_2_state()
            st.rerun()

    with col_btn2:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            reset_game_2_state()
            change_page('main')