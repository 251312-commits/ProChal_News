import streamlit as st
import pandas as pd
from modules.db_handler import init_gspread

# DB 워크시트 로드
ws = init_gspread()

def change_page(page_name: str):
    """페이지 이동 핸들러"""
    st.session_state.page = page_name
    st.rerun()

def show_ranking():
    """전체 사용자 실시간 랭킹(리더보드) 뷰"""
    st.title("🏆 명예의 전당 (실시간 랭킹)")

    st.markdown(
        """
        <style>
        .ranking-card {
            background-color: #ffffff;
            border: 3.5px solid #2d1842;
            border-radius: 8px;
            box-shadow: 4px 4px 0px #2d1842;
            padding: 14px 18px;
            margin-bottom: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .rank-top-1 {
            background: linear-gradient(135deg, #fff9db 0%, #fff3bf 100%);
            border-color: #f59f00;
            box-shadow: 4px 4px 0px #f59f00;
        }
        .rank-top-2 {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-color: #868e96;
            box-shadow: 4px 4px 0px #868e96;
        }
        .rank-top-3 {
            background: linear-gradient(135deg, #fff4e6 0%, #ffe8cc 100%);
            border-color: #d9480f;
            box-shadow: 4px 4px 0px #d9480f;
        }
        .rank-badge {
            font-family: 'Press Start 2P', monospace;
            font-size: 1.1rem;
            font-weight: bold;
            min-width: 60px;
        }
        .user-info {
            font-size: 1.05rem;
            font-weight: bold;
            color: #2d1842;
        }
        .coin-val {
            font-family: 'Press Start 2P', monospace;
            color: #7e22ce;
            font-weight: bold;
            font-size: 1.05rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.spinner("📊 실시간 랭킹 데이터 로딩 중..."):
        try:
            records = ws.get_all_records()
        except Exception as e:
            st.error(f"랭킹 데이터를 불러오지 못했습니다: {e}")
            return

    if not records:
        st.info("등록된 사용자 데이터가 없습니다.")
        return

    # 데이터 정리 및 타입 정제
    data = []
    for r in records:
        sid = str(r.get('학번', '')).strip().replace('.0', '')
        name = str(r.get('이름', '')).strip()
        try:
            coins = int(r.get('코인', 0))
        except:
            coins = 0
        try:
            streak = int(r.get('연승', 0))
        except:
            streak = 0
            
        if sid or name:
            data.append({
                '학번': sid,
                '이름': name,
                '코인': coins,
                '연승': streak
            })

    df = pd.DataFrame(data)

    # 탭 메뉴 구성 (코인 랭킹 / 연승 랭킹)
    tab1, tab2 = st.tabs(["💰 코인 부자 랭킹", "🔥 연속 승리 랭킹"])

    with tab1:
        st.subheader("💰 보유 코인 TOP 랭킹")
        df_coins = df.sort_values(by="코인", ascending=False).reset_index(drop=True)
        
        for idx, row in df_coins.iterrows():
            rank = idx + 1
            rank_class = ""
            icon = f"#{rank}"
            
            if rank == 1:
                rank_class = "rank-top-1"
                icon = "🥇 1등"
            elif rank == 2:
                rank_class = "rank-top-2"
                icon = "🥈 2등"
            elif rank == 3:
                rank_class = "rank-top-3"
                icon = "🥉 3등"

            # 학번 마스킹 (보안용)
            sid_masked = row['학번'][:4] + "****" if len(row['학번']) >= 4 else row['학번']

            st.markdown(
                f"""
                <div class="ranking-card {rank_class}">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="rank-badge">{icon}</span>
                        <span class="user-info">{row['이름']} ({sid_masked})</span>
                    </div>
                    <div class="coin-val">{row['코인']:,} C</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with tab2:
        st.subheader("🔥 최고 연승 TOP 랭킹")
        df_streak = df.sort_values(by="연승", ascending=False).reset_index(drop=True)
        
        for idx, row in df_streak.iterrows():
            rank = idx + 1
            rank_class = ""
            icon = f"#{rank}"
            
            if rank == 1:
                rank_class = "rank-top-1"
                icon = "🥇 1등"
            elif rank == 2:
                rank_class = "rank-top-2"
                icon = "🥈 2등"
            elif rank == 3:
                rank_class = "rank-top-3"
                icon = "🥉 3등"

            sid_masked = row['학번'][:4] + "****" if len(row['학번']) >= 4 else row['학번']

            st.markdown(
                f"""
                <div class="ranking-card {rank_class}">
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="rank-badge">{icon}</span>
                        <span class="user-info">{row['이름']} ({sid_masked})</span>
                    </div>
                    <div class="coin-val" style="color: #e03131;">🔥 {row['연승']} 연승</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("---")
    if st.button("⬅️ 메인 화면으로 돌아가기", use_container_width=True):
        change_page('main')