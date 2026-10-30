import streamlit as st
from modules.db_handler import init_gspread
from modules.ui_components import change_page

ws = init_gspread()

# 정의된 함수: show_ranking

def show_ranking():
    users_data = ws.get_all_records()
    if not users_data:
        st.warning("등록된 유저 데이터가 없습니다.")
        if st.button("⬅️ 메인으로 돌아가기"): change_page('main')
        return

    processed_users = []
    for u in users_data:
        try:
            coin_val = int(u.get('코인', 0))
        except:
            coin_val = 0
        processed_users.append({
            'id': str(u.get('학번', '')).strip().replace('.0', ''),
            'nickname': str(u.get('아이디', '익명')).strip(),
            'coins': coin_val
        })
    
    sorted_users = sorted(processed_users, key=lambda x: x['coins'], reverse=True)
    for idx, u in enumerate(sorted_users):
        u['rank'] = idx + 1

    current_sid = st.session_state.get('current_user', '')
    my_info = next((u for u in sorted_users if u['id'] == current_sid), None)
    
    if not my_info and st.session_state.get('current_user_data'):
        my_nick = st.session_state.current_user_data.get('아이디', '')
        my_info = next((u for u in sorted_users if u['nickname'] == my_nick), None)

    my_rank = my_info['rank'] if my_info else 0
    my_nickname = my_info['nickname'] if my_info else (st.session_state.current_user_data.get('아이디', '나') if st.session_state.get('current_user_data') else '나')
    my_coins = my_info['coins'] if my_info else 0

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Gowun+Dodum&family=Noto+Sans+KR:wght@700;900&display=swap');

        .ranking-container, .ranking-container * {
            box-sizing: border-box !important;
        }

        .ranking-container {
            font-family: 'Gowun Dodum', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #110022 0%, #1a0933 50%, #0d001a 100%);
            padding: 18px 14px;
            border-radius: 20px;
            color: #ffffff;
            border: 2px solid #00ffcc;
            animation: pulseGlow 3s infinite alternate;
            margin-bottom: 20px;
            width: 100%;
        }

        @keyframes pulseGlow {
            0% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
            50% { border-color: #ff00ff; box-shadow: 0 0 25px rgba(255, 0, 255, 0.6); }
            100% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
        }

        .ranking-header-title {
            text-align: center;
            font-family: 'Press Start 2P', monospace;
            font-size: 13px;
            color: #fffb00;
            text-shadow: 0 0 8px #ff00ff, 0 0 15px #00ffff;
            margin-bottom: 16px;
            letter-spacing: 1px;
        }

        .my-rank-card {
            background: linear-gradient(120deg, #1f113a 0%, #2e1052 50%, #1a0833 100%);
            border: 2px solid #ffd700;
            border-radius: 14px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 22px;
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.4), inset 0 0 8px rgba(255, 215, 0, 0.2);
            width: 100%;
        }
        .my-rank-badge {
            font-size: 1.1rem;
            font-weight: 900;
            color: #ffd700;
            text-shadow: 0 0 8px rgba(255, 215, 0, 0.8);
            margin-right: 8px;
            white-space: nowrap;
        }
        .my-nickname {
            font-size: 1rem;
            font-weight: 800;
            color: #ffffff;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .top3-container {
            display: flex;
            justify-content: center;
            align-items: flex-end;
            gap: 8px;
            margin-bottom: 24px;
            width: 100%;
        }
        
        /* 공통 현수막 스타일 (클릭 호버 확대 제거) */
        .banner-box {
            flex: 1;
            min-width: 0;
            border-radius: 14px;
            padding: 12px 4px 14px 4px;
            text-align: center;
            color: #ffffff;
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        /* 디폴트 커졌다 작아지는 애니메이션 적용 */
        .banner-gold {
            background: linear-gradient(180deg, #ffd700 0%, #b8860b 60%, #5c4000 100%);
            border: 2.5px solid #fffb00;
            min-height: 135px;
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.7);
            animation: goldPulse 2s ease-in-out infinite alternate;
        }
        .banner-silver {
            background: linear-gradient(180deg, #e0e0e0 0%, #757575 60%, #303030 100%);
            border: 2px solid #ffffff;
            min-height: 115px;
            box-shadow: 0 0 12px rgba(255, 255, 255, 0.4);
            animation: silverPulse 2.4s ease-in-out infinite alternate 0.3s;
        }
        .banner-bronze {
            background: linear-gradient(180deg, #cd7f32 0%, #8b4513 60%, #3e1e07 100%);
            border: 2px solid #ffaa66;
            min-height: 102px;
            box-shadow: 0 0 12px rgba(205, 127, 50, 0.5);
            animation: bronzePulse 2.8s ease-in-out infinite alternate 0.6s;
        }

        @keyframes goldPulse {
            0% { transform: translateY(-5px) scale(0.96); }
            100% { transform: translateY(-5px) scale(1.05); }
        }
        @keyframes silverPulse {
            0% { transform: scale(0.96); }
            100% { transform: scale(1.04); }
        }
        @keyframes bronzePulse {
            0% { transform: scale(0.96); }
            100% { transform: scale(1.04); }
        }

        .crown-icon {
            font-size: 1.8rem;
            line-height: 1;
            margin-bottom: 4px;
            filter: drop-shadow(0 0 6px rgba(255,255,255,0.8));
        }
        .crown-gold {
            animation: crownFloat 2s ease-in-out infinite;
            font-size: 2.2rem;
        }

        @keyframes crownFloat {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-6px) rotate(-6deg); }
        }

        .banner-nickname {
            font-size: 0.88rem;
            font-weight: 900;
            margin: 4px 0;
            text-shadow: 1px 1px 4px rgba(0,0,0,0.9);
            width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .banner-coin-tag {
            background: rgba(0, 0, 0, 0.5);
            border-radius: 20px;
            padding: 3px 8px;
            font-size: 0.75rem;
            font-weight: 800;
            display: inline-block;
            border: 1px solid rgba(255,255,255,0.4);
            white-space: nowrap;
            color: #00ffcc;
            text-shadow: 0 0 5px #00ffcc;
        }

        .rank-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            width: 100%;
        }
        .rank-item {
            background: rgba(255, 255, 255, 0.07);
            backdrop-filter: blur(5px);
            border-radius: 12px;
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #ffffff;
            width: 100%;
        }
        .rank-item.is-me {
            background: linear-gradient(90deg, rgba(255,0,255,0.25) 0%, rgba(138,43,226,0.3) 100%);
            border: 2px solid #ff00ff;
            box-shadow: 0 0 10px rgba(255, 0, 255, 0.5);
        }
        .rank-number {
            font-size: 1rem;
            font-weight: 900;
            color: #00ffcc;
            text-shadow: 0 0 6px #00ffcc;
            width: 30px;
            flex-shrink: 0;
        }
        .rank-nickname {
            font-size: 0.9rem;
            font-weight: 800;
            color: #ffffff;
            flex: 1;
            padding: 0 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .coin-box {
            background: rgba(0, 0, 0, 0.4);
            border: 1.5px solid #ffd700;
            border-radius: 20px;
            padding: 3px 9px;
            font-size: 0.8rem;
            font-weight: 900;
            color: #ffd700;
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
            white-space: nowrap;
            box-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
        }
        .ellipsis-divider {
            text-align: center;
            color: #ff00ff;
            font-size: 1.1rem;
            font-weight: bold;
            margin: 4px 0;
            letter-spacing: 4px;
            text-shadow: 0 0 8px #ff00ff;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    rank_str = f"{my_rank}위" if my_rank > 0 else "순위 밖"
    
    top1 = next((u for u in sorted_users if u['rank'] == 1), None)
    top2 = next((u for u in sorted_users if u['rank'] == 2), None)
    top3 = next((u for u in sorted_users if u['rank'] == 3), None)

    top2_html = f'<div class="banner-box banner-silver"><div class="crown-icon">🥈</div><div class="banner-nickname">{top2["nickname"]}</div><div class="banner-coin-tag">🪙 {top2["coins"]:,}</div></div>' if top2 else '<div class="banner-box banner-silver" style="opacity:0.3;"><div class="crown-icon">🥈</div>-</div>'
    top1_html = f'<div class="banner-box banner-gold"><div class="crown-icon crown-gold">👑</div><div class="banner-nickname">{top1["nickname"]}</div><div class="banner-coin-tag">🪙 {top1["coins"]:,}</div></div>' if top1 else '<div class="banner-box banner-gold" style="opacity:0.3;"><div class="crown-icon crown-gold">👑</div>-</div>'
    top3_html = f'<div class="banner-box banner-bronze"><div class="crown-icon">🥉</div><div class="banner-nickname">{top3["nickname"]}</div><div class="banner-coin-tag">🪙 {top3["coins"]:,}</div></div>' if top3 else '<div class="banner-box banner-bronze" style="opacity:0.3;"><div class="crown-icon">🥉</div>-</div>'

    list_items_html = ""
    display_ranks = set()
    for r in [4, 5]:
        if r <= len(sorted_users):
            display_ranks.add(r)
    if my_rank > 0:
        for r in range(my_rank - 1, my_rank + 2):
            if 4 <= r <= len(sorted_users):
                display_ranks.add(r)

    sorted_ranks = sorted(list(display_ranks))
    if sorted_ranks:
        prev_r = 3
        for r in sorted_ranks:
            if r > prev_r + 1:
                list_items_html += '<div class="ellipsis-divider">• • •</div>'
            row = next((u for u in sorted_users if u['rank'] == r), None)
            if row:
                is_me = (my_info and row['id'] == my_info['id'])
                is_me_class = "is-me" if is_me else ""
                me_label = " (나)" if is_me else ""
                list_items_html += f'<div class="rank-item {is_me_class}"><div class="rank-number">{r}</div><div class="rank-nickname">{row["nickname"]}{me_label}</div><div class="coin-box">🪙 {row["coins"]:,}</div></div>'
            prev_r = r

    full_ranking_html = f'''
    <div class="ranking-container">
        <div class="ranking-header-title">🏆 HALL OF FAME 🏆</div>
        <div class="my-rank-card">
            <div style="display:flex; align-items:center; overflow:hidden;">
                <span class="my-rank-badge">{rank_str}</span>
                <span class="my-nickname">👤 {my_nickname} (나)</span>
            </div>
            <div class="coin-box">🪙 {my_coins:,} C</div>
        </div>
        <div class="top3-container">
            {top2_html}
            {top1_html}
            {top3_html}
        </div>
        {'<div class="rank-list">' + list_items_html + '</div>' if list_items_html else ''}
    </div>
    '''

    st.markdown(full_ranking_html, unsafe_allow_html=True)

    if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
        change_page('main')
