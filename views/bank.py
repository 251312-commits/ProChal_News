import streamlit as st
from modules.ui_components import change_page  # 페이지 이동 함수 불러오기

@st.dialog("🚨 잔액 부족!")
def _no_money_modal(min_required, current_coins):
    """코인 부족 시 뜨는 네온 스타일 모달 팝업"""
    st.markdown(
        f"""
        <style>
        .bank-popup-container {{
            text-align: center;
            padding: 10px 5px;
        }}
        .bank-popup-icon {{
            font-size: 3.5rem;
            margin-bottom: 10px;
            animation: bankBounce 1.5s infinite ease-in-out;
        }}
        @keyframes bankBounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-8px); }}
        }}
        .bank-popup-title {{
            color: #ff0055;
            font-size: 1.3rem;
            font-weight: 900;
            text-shadow: 0 0 10px rgba(255, 0, 85, 0.6);
            margin-bottom: 12px;
        }}
        .bank-popup-desc {{
            color: #e0e0e0;
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 18px;
        }}
        .bank-popup-highlight {{
            color: #ffd700;
            font-weight: bold;
        }}
        </style>

        <div class="bank-popup-container">
            <div class="bank-popup-icon">🏦</div>
            <div class="bank-popup-title">탕진잼! 코인이 부족합니다</div>
            <div class="bank-popup-desc">
                게임 참여에 최소 <span class="bank-popup-highlight">{min_required:,} C</span>가 필요하지만<br>
                현재 보유 코인은 <span style="color:#ff9999; font-weight:bold;">{current_coins:,} C</span> 입니다.<br><br>
                💡 <b>은행</b>에 들러 대출이나 충전을 진행하시겠습니까?
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏛️ 은행으로 가기", use_container_width=True, type="primary"):
            change_page('bank')
            st.rerun()

    with col2:
        if st.button("⬅️ 메인으로", use_container_width=True):
            change_page('main')
            st.rerun()


def check_user_coins_or_pop_bank(min_required=1000):
    """
    유저의 코인을 검사하고, 부족하면 은행 유도 팝업을 띄운 뒤 False를 반환합니다.
    코인이 충분하면 True를 반환합니다.
    
    사용 예시:
    if not check_user_coins_or_pop_bank(1000):
        return
    """
    current_coins = int(st.session_state.current_user_data.get('코인', 0)) if st.session_state.get('current_user_data') else 0

    if current_coins < min_required:
        _no_money_modal(min_required, current_coins)
        return False
    return True
