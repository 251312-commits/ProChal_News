import streamlit as st
from modules.db_handler import init_gspread
from modules.ui_components import change_page, load_local_image_as_base64

ws = init_gspread()

# 정의된 함수: show_main_page
    
@st.fragment(run_every="600s")
def show_main_page():

    # 세션에 유저 정보가 없을 때만 구글 시트에서 데이터를 새로 불러옵니다.
    if not st.session_state.get('current_user_data'):
        users_data = ws.get_all_records()
        updated_info = next((item for item in users_data if str(item.get('학번', '')).strip().replace('.0', '') == st.session_state.current_user), None)
        if updated_info:
            st.session_state.current_user_data = updated_info

    user = st.session_state.get('current_user_data')

    if not user:
        change_page('login')
        return
    
    st.markdown(
        f"""
        <div style="color: white; font-weight: bold; font-size: 0.9rem; margin-bottom: -5px;">안전의대명사 뉴스에이전놀이터</div>
        <div style="color: #FF00FF; font-weight: bold; font-size: 0.8rem; margin-bottom: 5px;">실시간 뉴스 미니게임</div>
        
        <div class="neon-promo-banner">
            <div class="neon-left-box">
                <div class="neon-numbers">
                    VIP <span>{user.get('아이디', '알 수 없음')}</span><br>
                    보유 <span>{user.get('코인', 0)}</span> C<br>
                    🔥<span>{user.get('연승', 0)}</span> 연승중🔥
                </div>
            </div>
            <div class="neon-right-box">
                <div class="neon-logo-text">NEWS</div>
                <div style="background: #FF00FF; color: white; padding: 2px 10px; border-radius: 10px; font-weight: bold; margin-top: 5px;">유익하다!</div>
                <div class="neon-sub-text">친구 초대 시 3000코인 지급</div>
                <div class="neon-sub-text-2">당신도 가능하다 인생역전</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Streamlit native buttons avoid third-party frontend component loading errors.
    # Keep the original image banners and make the entire image area clickable.
    menu_items = [
        ("assets/banner1.png", "🏦 은행", "bank"),
        ("assets/banner2.png", "🏆 랭킹", "ranking"),
        ("assets/banner3.png", "게임 1", "game_1"),
        ("assets/banner4.png", "게임 2", "game_2"),
        ("assets/banner5.png", "게임 3", "game_3"),
        ("assets/banner6.png", "게임 4", "game_4"),
        ("assets/banner7.png", "게임 5", "game_5"),
    ]

    # An image-backed st.button has normal Streamlit click handling and no
    # external JavaScript bundle. The labels remain accessible to screen readers.
    styles = [
        """
        .st-key-main-native-menu [data-testid="stVerticalBlock"] {
            gap: 15px !important;
        }
        .st-key-main-native-menu .stButton > button {
            height: 110px !important;
            min-height: 110px !important;
            width: 100% !important;
            border: 2px solid #8A2BE2 !important;
            border-radius: 5px !important;
            padding: 0 !important;
            box-shadow: 0 0 10px rgba(138,43,226,.8) !important;
            color: transparent !important;
            font-size: 0 !important;
            text-shadow: none !important;
            cursor: pointer !important;
            transition: filter .18s ease, box-shadow .18s ease;
        }
        .st-key-main-native-menu .stButton > button:hover {
            filter: brightness(1.15) !important;
            box-shadow: 0 0 16px rgba(180,66,255,.9) !important;
        }
        .st-key-main-native-menu .stButton > button:focus-visible {
            outline: 3px solid #ffffff !important;
            outline-offset: 3px !important;
        }
        @media(max-width:480px) {
            .st-key-main-native-menu .stButton > button {
                height: 100px !important;
                min-height: 100px !important;
            }
        }
        """
    ]
    for index, (img_path, _label, _route) in enumerate(menu_items):
        image_uri = load_local_image_as_base64(img_path)
        styles.append(
            f'.st-key-main-banner-{index} button {{'
            f'background: #10051d url("{image_uri}") center center / cover no-repeat !important;'
            f'}}'
        )

    st.markdown("<style>" + "\n".join(styles) + "</style>", unsafe_allow_html=True)

    with st.container(key="main-native-menu"):
        for index, (_image, label, route) in enumerate(menu_items):
            if st.button(
                label,
                key=f"main-banner-{index}",
                help=label,
                use_container_width=True,
            ):
                change_page(route)
