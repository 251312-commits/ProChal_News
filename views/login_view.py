import streamlit as st
from modules.db_handler import init_gspread

# DB 워크시트 객체 로드 (Users 탭)
ws = init_gspread()

def change_page(page_name: str):
    """페이지 이동 핸들러"""
    st.session_state.page = page_name
    st.rerun()

def show_login_page():
    """로그인 및 회원가입(1단계: 학번 검증 -> 2단계: 인증/가입) 뷰"""
    _, col_main, _ = st.columns([1, 2.5, 1])

    with col_main:
        with st.container(border=True):
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 20px;">
                    <div class="user-icon-circle">👤</div>
                    <h2 style="margin-bottom: 6px; margin-top: 0;">Title</h2>
                    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 0;">학번을 입력하여 로그인해주세요.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # --------------------------------------------------
            # [1단계] 학번 입력 및 존재 여부 조회
            # --------------------------------------------------
            if st.session_state.login_step == 1:
                student_id = st.text_input("학번", max_chars=5, placeholder="학번 5자리 입력", key="input_sid")
                
                if st.button("다음 (Next)", use_container_width=True):
                    clean_id = student_id.strip()
                    if clean_id.isdigit() and len(clean_id) == 5:
                        users_data = ws.get_all_records()
                        
                        user_info = None
                        for item in users_data:
                            raw_sheet_id = str(item.get('학번', ''))
                            sheet_id = raw_sheet_id.split('.')[0] if '.' in raw_sheet_id else raw_sheet_id.strip()
                            if sheet_id == clean_id:
                                user_info = item
                                break
                        
                        st.session_state.temp_student_id = clean_id
                        
                        if user_info:
                            st.session_state.temp_user_data = user_info
                            st.session_state.login_step = '2_exist'
                        else:
                            st.session_state.login_step = '2_new'
                        st.rerun()
                    else:
                        st.error("학번은 5자리 숫자로 입력해주세요.")

            # --------------------------------------------------
            # [2단계 - 기존 유저] 비밀번호 입력 및 로그인
            # --------------------------------------------------
            elif st.session_state.login_step == '2_exist':
                st.info(f"현재 {st.session_state.temp_student_id}으로 로그인 중입니다.")
                password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력", key="input_pw_login")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("이전", use_container_width=True):
                        st.session_state.login_step = 1
                        st.rerun()
                with col_b2:
                    if st.button("로그인", use_container_width=True):
                        saved_pw = str(st.session_state.temp_user_data.get('비밀번호', ''))
                        if password == saved_pw:
                            st.session_state.current_user = st.session_state.temp_student_id
                            st.session_state.current_user_data = st.session_state.temp_user_data
                            st.session_state.login_step = 1
                            change_page('main')
                        else:
                            st.error("비밀번호가 일치하지 않습니다.")

            # --------------------------------------------------
            # [2단계 - 신규 유저] 회원가입 폼 및 DB 등록
            # --------------------------------------------------
            elif st.session_state.login_step == '2_new':
                st.success(f"신규 가입 대상 학번: {st.session_state.temp_student_id}")
                
                username = st.text_input("아이디 (닉네임)", placeholder="사용할 닉네임", key="input_uname")
                password = st.text_input("비밀번호", type="password", placeholder="비밀번호 설정", key="input_pw1")
                password_confirm = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호 재입력", key="input_pw2")
                referral = st.text_input("추천인 학번 (선택)", placeholder="초대한 친구 학번", key="input_ref")

                st.markdown(
                    """
                    <div class="warning-note">
                        ⚠️ <b>주의사항:</b> 설정한 비밀번호는 보안상 추후 변경이 어려우니 반드시 기억해 두시기 바랍니다!
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("이전", use_container_width=True):
                        st.session_state.login_step = 1
                        st.rerun()
                with col_b2:
                    if st.button("가입완료", use_container_width=True):
                        if not username.strip():
                            st.error("닉네임을 입력해 주세요.")
                        elif not password:
                            st.error("비밀번호를 입력해 주세요.")
                        elif password != password_confirm:
                            st.error("비밀번호 확인이 일치하지 않습니다.")
                        else:
                            clean_id = st.session_state.temp_student_id
                            final_username = username.strip()
                            initial_coins = 5000
                            users_data = ws.get_all_records()

                            # 추천인 보상 처리
                            if referral.strip():
                                clean_ref = referral.strip()
                                ref_info = next((item for item in users_data if str(item.get('학번', '')).split('.')[0] == clean_ref), None)
                                if ref_info:
                                    row_idx = users_data.index(ref_info) + 2
                                    new_coins = int(ref_info.get('코인', 0)) + 3000
                                    ws.update_cell(row_idx, 3, new_coins)
                                    initial_coins += 1000
                                    st.toast("🎉 추천인 보상 코인이 지급되었습니다!")

                            # 신규 회원 추가
                            new_row = [clean_id, final_username, initial_coins, 0, referral.strip(), password]
                            ws.append_row(new_row)

                            st.session_state.current_user = clean_id
                            st.session_state.current_user_data = {
                                "학번": clean_id,
                                "아이디": final_username,
                                "코인": initial_coins,
                                "연승": 0,
                                "비밀번호": password
                            }
                            st.session_state.login_step = 1
                            change_page('main')

---

### 💡 메인 파일(`news.py`)에서의 호출 방법 예시

`news.py` 메인 라우터 구역에서 아래와 같이 임포트하여 사용하시면 됩니다[span_1](start_span)[span_1](end_span).

```python
from views.login_view import show_login_page
from modules.ui_components import stop_bgm, inject_casino_theme

# 글로벌 테마 적용
inject_casino_theme()

if st.session_state.page == 'login':
    stop_bgm()
    show_login_page()
