def show_main_page():
    st_autorefresh(interval=600000, limit=None, key="auto_refresh")

    users_data = ws.get_all_records()
    updated_info = next((item for item in users_data if str(item.get('학번', '')).strip().replace('.0', '') == st.session_state.current_user), None)
    
    if updated_info:
        st.session_state.current_user_data = updated_info

    user = st.session_state.current_user_data
    
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
    
    img_urls = [
        "https://github.com/user-attachments/assets/331b7b2e-c4f5-4087-9f6b-9e672afb9568", 
        "https://github.com/user-attachments/assets/24bc9c42-e6c0-4f6f-a3a1-e1cce8fd66f3", 
        "https://github.com/user-attachments/assets/caf0511f-54f9-4d1e-8d6d-318e6886f2b4", 
        "https://github.com/user-attachments/assets/2893591d-30c2-485a-adcc-f8bd2ed94aa6", 
        "https://picsum.photos/id/50/800/110", 
        "https://picsum.photos/id/60/800/110", 
        "https://picsum.photos/id/70/800/110", 
        "https://picsum.photos/id/80/800/110"  
    ]
    
    clicked_menu = clickable_images(
        img_urls,
        titles=["🏦 은행", "🏆 랭킹", "게임 1", "게임 2", "게임 3", "게임 4", "게임 5", "🛒 교환소"],
        div_style={
            "display": "flex", 
            "flex-direction": "column", 
            "gap": "15px",
            "justify-content": "center",
            "padding-bottom": "30px",
            "background-color": "#05000a" 
        },
        img_style={
            "width": "100%",            
            "height": "110px",          
            "object-fit": "cover",      
            "border-radius": "5px", 
            "border": "2px solid #8A2BE2", 
            "box-shadow": "0 0 10px rgba(138, 43, 226, 0.8)",
            "cursor": "pointer"
        },
        key="main_menu_banners"
    )
    
    if clicked_menu == 0: change_page('bank')
    elif clicked_menu == 1: change_page('ranking')
    elif clicked_menu == 2: change_page('game_1')
    elif clicked_menu == 3: change_page('game_2')
    elif clicked_menu == 4: change_page('game_3')
    elif clicked_menu == 5: change_page('game_4')
    elif clicked_menu == 6: change_page('game_5')
    elif clicked_menu == 7: change_page('exchange')
