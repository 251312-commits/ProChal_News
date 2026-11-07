import streamlit as st
from modules.account_math import account_amount
from modules.db_handler import init_gspread
from modules.transactions import TransactionError, register_player, transaction_id
from modules.ui_components import change_page

ws = init_gspread()

# 정의된 함수: show_login_page

def show_login_page():
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
                            user_info["대출금"] = account_amount(user_info.get("대출금"))
                            if user_info.get("대출원금") not in (None, ""):
                                user_info["대출원금"] = account_amount(user_info["대출원금"])
                            st.session_state.temp_user_data = user_info
                            st.session_state.login_step = '2_exist'
                        else:
                            st.session_state.login_step = '2_new'
                        st.rerun()
                    else:
                        st.error("학번은 5자리 숫자로 입력해주세요.")

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
                            # A stable request ID makes a timed-out registration
                            # and both referral bonuses safe to retry.
                            key = "registration_pending_id"
                            if st.session_state.get("registration_pending_student") != clean_id:
                                st.session_state[key] = transaction_id("register")
                                st.session_state["registration_pending_student"] = clean_id
                            try:
                                balances = register_player(
                                    clean_id, final_username, password, referral.strip(),
                                    st.session_state[key],
                                )
                            except TransactionError as exc:
                                st.error(str(exc))
                                return
                            st.session_state.pop(key, None)
                            st.session_state.pop("registration_pending_student", None)
                            st.session_state.current_user = clean_id
                            st.session_state.current_user_data = {
                                "학번": clean_id,
                                "아이디": final_username,
                                "코인": balances["coins"],
                                "대출금": balances["loan"],
                                "대출원금": balances.get("principal", 0),
                                "연승": balances["streak"],
                                "비밀번호": password,
                            }
                            st.session_state.login_step = 1
                            change_page('main')
        
        st.markdown('</div>', unsafe_allow_html=True)
