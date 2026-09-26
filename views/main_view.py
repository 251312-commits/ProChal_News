import streamlit as st
from modules.db_handler import init_gspread

def change_page(page_name: str):
    """페이지 이동 핸들러"""
    st.session_state.page = page_name
    st.rerun()

def show_main_page():
    """메인 대시보드 화면 뷰"""
    # 사용자 데이터 로드
    user_data = st.session_state.get('current_user_data', {})
    student_id = st.session_state.get('current_user', '미인증')
    username = user_data.get('아이디', '사용자')
    coins = user_data.get('코인', 0)
    streak = user_data.get('연승', 0)

    # --------------------------------------------------
    # [1] 상단 프로필 대시보드
    # --------------------------------------------------
    st.title("🏠 메인 로비")
    
    col_user, col_coin, col_streak = st.columns(3)
    with col_user:
        st.metric(label="👤 사용자 (학번)", value=f"{username} ({student_id})")
    with col_coin:
        st.metric(label="💰 보유 코인", value=f"{coins:,} C")
    with col_streak:
        st.metric(label="🔥 현재 연승", value=f"{streak} 연승")

    st.divider()

    # --------------------------------------------------
    # [2] 주요 메뉴 카드리스트
    # --------------------------------------------------
    st.subheader("🎮 메뉴 선택")
    
    m_col1, m_col2, m_col3 = st.columns(3)

    with m_col1:
        with st.container(border=True):
            st.markdown("### 📰 뉴스 예측")
            st.write("오늘의 뉴스를 읽고 결과를 예측해 코인을 획득해보세요.")
            if st.button("뉴스 예측하러 가기", key="btn_go_news", use_container_width=True):
                change_page('news')

    with m_col2:
        with st.container(border=True):
            st.markdown("### 🎲 카지노 / 미니게임")
            st.write("스릴 넘치는 미니게임으로 코인을 불려보세요.")
            if st.button("게임장 입장", key="btn_go_casino", use_container_width=True):
                change_page('casino')

    with m_col3:
        with st.container(border=True):
            st.markdown("### 🏆 순위 및 정보")
            st.write("전체 사용자 랭킹을 확인하고 개인 정보를 관리합니다.")
            if st.button("랭킹 및 정보 확인", key="btn_go_ranking", use_container_width=True):
                change_page('ranking')

    st.divider()

    # --------------------------------------------------
    # [3] 하단 세션 및 계정 관리 버튼
    # --------------------------------------------------
    col_sub1, col_sub2 = st.columns([3, 1])
    with col_sub2:
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.current_user = None
            st.session_state.current_user_data = None
            st.session_state.login_step = 1
            change_page('login')