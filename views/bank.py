import streamlit as st
from modules.ui_components import change_page
from modules.db_handler import init_gspread

# 정의된 함수: show_bank, process_turn_interest

def show_bank():
    # 로그인 체크
    if 'current_user_data' not in st.session_state or not st.session_state.current_user_data:
        st.error("⚠️ 로그인 정보가 없습니다. 메인 화면으로 이동합니다.")
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            change_page('main')
        return

    # 금융 상수 설정
    MAX_LOAN = 10000        # 대출 상한액
    INTEREST_RATE = 0.20    # 턴 당 이자율 20%
    UNIT = 1000             # 거래 단위

    # 유저 데이터 참조
    user_data = st.session_state.current_user_data
    current_coins = int(user_data.get('코인', 0))
    current_loan = int(user_data.get('대출금', 0))

    # 대출 가능 잔여 한도 계산
    available_loan = max(0, MAX_LOAN - current_loan)
    next_interest = int(current_loan * INTEREST_RATE)

    # 은행 전용 네온 카지노 스타일 CSS
    st.markdown(
        """
        <style>
        .bank-container {
            background: linear-gradient(135deg, #0d001a 0%, #1a0933 50%, #110022 100%);
            border: 2px solid #ffd700;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
            margin-bottom: 20px;
        }
        .bank-title {
            font-family: 'Press Start 2P', monospace;
            font-size: 1.2rem;
            color: #ffd700;
            text-align: center;
            text-shadow: 0 0 10px #ffd700, 0 0 20px #ff00ff;
            margin-bottom: 15px;
        }
        .status-card {
            background: rgba(0, 0, 0, 0.45);
            border: 1.5px solid rgba(255, 215, 0, 0.5);
            border-radius: 14px;
            padding: 14px;
            margin-bottom: 15px;
        }
        .status-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 0;
            border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
            font-size: 0.95rem;
            color: #ffffff;
        }
        .status-row:last-child {
            border-bottom: none;
        }
        .status-value {
            font-weight: 900;
        }
        .interest-badge {
            background: rgba(255, 0, 85, 0.2);
            border: 1px solid #ff0055;
            color: #ff6699;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.8rem;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.title("🏦 로얄 네온 중앙은행")

    # 상단 요약 현황판
    st.markdown(
        f"""
        <div class="bank-container">
            <div class="bank-title">🏛️ BANK FINANCIAL CENTER</div>
            <div class="status-card">
                <div class="status-row">
                    <span>🪙 보유 코인</span>
                    <span class="status-value" style="color:#00ffcc;">{current_coins:,} C</span>
                </div>
                <div class="status-row">
                    <span>💳 현재 대출 잔액</span>
                    <span class="status-value" style="color:#ff9999;">{current_loan:,} C / {MAX_LOAN:,} C</span>
                </div>
                <div class="status-row">
                    <span>📈 턴 당 이자율</span>
                    <span class="interest-badge">20% (다음 턴 이자: +{next_interest:,} C)</span>
                </div>
                <div class="status-row">
                    <span>🔓 추가 대출 가능액</span>
                    <span class="status-value" style="color:#ffd700;">{available_loan:,} C</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 탭 구성 (대출 신청 / 대출 상환)
    tab_borrow, tab_repay = st.tabs(["💰 대출 신청", "💳 대출 상환"])

    # ------------------ [1] 대출 신청 탭 ------------------
    with tab_borrow:
        st.subheader("💰 신용 대출 신청")
        st.caption(f"· 대출 단위: {UNIT:,} C | 최대 대출 가능 금액: {MAX_LOAN:,} C")
        st.caption("· 턴이 지날 때마다 남아있는 대출금의 20% 이자가 복리로 추가됩니다.")

        if available_loan < UNIT:
            st.warning("⚠️ 이미 최대 대출 한도(10,000 C)에 도달하여 추가 대출이 불가능합니다.")
        else:
            borrow_amount = st.slider(
                "대출할 금액을 선택하세요",
                min_value=UNIT,
                max_value=available_loan,
                step=UNIT,
                value=min(UNIT, available_loan),
                key="borrow_slider"
            )

            expected_interest = int(borrow_amount * INTEREST_RATE)
            st.info(f"💡 **{borrow_amount:,} C** 대출 시, 다음 턴에 추가되는 이자는 **+{expected_interest:,} C** 입니다.")

            if st.button("💵 선택한 금액 대출받기", use_container_width=True, type="primary"):
                # 세션 상태 즉시 반영
                st.session_state.current_user_data['코인'] = current_coins + borrow_amount
                st.session_state.current_user_data['대출금'] = current_loan + borrow_amount

                # 구글 시트 동기화
                try:
                    ws = init_gspread()
                    cell = ws.find(str(st.session_state.current_user_data.get('학번', '')))
                    if cell:
                        # 시트 열 위치에 맞춰 대출금/코인 업데이트
                        ws.update_cell(cell.row, 3, st.session_state.current_user_data['코인'])
                        # 대출금 컬럼이 있을 경우 신규 업데이트 (예: 4번째 열)
                        ws.update_cell(cell.row, 4, st.session_state.current_user_data['대출금'])
                except Exception:
                    pass

                st.success(f"🎉 {borrow_amount:,} C 대출이 완료되었습니다!")
                st.rerun()

    # ------------------ [2] 대출 상환 탭 ------------------
    with tab_repay:
        st.subheader("💳 대출금 상환")

        if current_loan <= 0:
            st.success("✨ 상환할 대출금이 없습니다! 깨끗한 신용 상태입니다.")
        elif current_coins < UNIT:
            st.error(f"⚠️ 상환에 필요한 최소 코인({UNIT:,} C)이 부족합니다.")
        else:
            max_repay_possible = min(current_coins, current_loan)
            max_repay_unit = (max_repay_possible // UNIT) * UNIT

            if max_repay_unit < UNIT:
                st.warning(f"⚠️ 대출 상환은 최소 {UNIT:,} C 단위로 가능합니다.")
            else:
                repay_amount = st.slider(
                    "상환할 금액을 선택하세요",
                    min_value=UNIT,
                    max_value=max_repay_unit,
                    step=UNIT,
                    value=max_repay_unit,
                    key="repay_slider"
                )

                remaining_loan_after = current_loan - repay_amount
                st.info(f"💡 상환 후 남은 대출 잔액: **{remaining_loan_after:,} C**")

                if st.button("✨ 선택한 금액 상환하기", use_container_width=True, type="primary"):
                    # 세션 상태 즉시 반영
                    st.session_state.current_user_data['코인'] = current_coins - repay_amount
                    st.session_state.current_user_data['대출금'] = current_loan - repay_amount

                    # 구글 시트 동기화
                    try:
                        ws = init_gspread()
                        cell = ws.find(str(st.session_state.current_user_data.get('학번', '')))
                        if cell:
                            ws.update_cell(cell.row, 3, st.session_state.current_user_data['코인'])
                            ws.update_cell(cell.row, 4, st.session_state.current_user_data['대출금'])
                    except Exception:
                        pass

                    st.success(f"✅ {repay_amount:,} C를 성공적으로 상환하셨습니다!")
                    st.rerun()

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

    # 하단 메인 이동 버튼
    if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
        change_page('main')
