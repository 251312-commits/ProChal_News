"""Loan documents and the bank's Google Sheets balance update."""


import streamlit as st

from modules.account_math import account_amount
from modules.db_handler import BankBalancesChanged, init_gspread, save_bank_balances

UNIT = 1_000
MAX_LOAN = 10_000
INTEREST_RATE = 0.20


def _save_balances(coins: int, loan: int, message: str, *, success_state_key: str | None = None) -> None:
    user = st.session_state.current_user_data
    student_id = st.session_state.get("current_user") or user.get("학번")
    try:
        save_bank_balances(
            init_gspread(), student_id, coins, loan,
            expected_coins=account_amount(user.get("코인")),
            expected_loan=account_amount(user.get("대출금")),
        )
    except BankBalancesChanged as changed:
        user.update({"코인": changed.coins, "대출금": changed.loan})
        st.toast("잔액이 변경되었습니다. 새 잔액을 확인한 뒤 다시 신청하세요.")
        st.rerun()
        return
    except ValueError:
        st.error("시트의 코인(C열)과 대출금(G열)에 올바른 숫자가 입력되어 있는지 확인하세요.")
        return
    except Exception:
        st.error("거래를 저장하지 못했습니다. 잠시 후 다시 시도하세요.")
        return

    user.update({"코인": coins, "대출금": loan})
    if success_state_key:
        st.session_state[success_state_key] = True
    st.toast(message)
    st.rerun()


def _change_amount(key: str, amount: int) -> None:
    st.session_state[key] = amount


def _amount_selector(label: str, key: str, limit: int, default: int) -> int:
    """Keep slider and step buttons in sync, including a single available unit."""
    chosen = st.session_state.get(key, default)
    chosen = max(UNIT, min(limit, (chosen // UNIT) * UNIT))
    # Streamlit can recreate the slider when its maximum changes after a payment.
    st.session_state[key] = chosen

    st.html(f'<p class="bank-amount-label">{label}</p>')
    with st.container(key="bank-stepper", horizontal=True, vertical_alignment="center"):
        st.button("−", key=f"{key}_minus", help=f"{UNIT:,} C 줄이기",
                  disabled=chosen <= UNIT, on_click=_change_amount, args=(key, chosen - UNIT))
        st.html(f'<output class="bank-amount-value">{chosen:,} C</output>')
        st.button("＋", key=f"{key}_plus", help=f"{UNIT:,} C 늘리기",
                  disabled=chosen >= limit, on_click=_change_amount, args=(key, chosen + UNIT))

    if limit == UNIT:
        return UNIT
    return st.slider(label, UNIT, limit, step=UNIT, key=key, format="%d C",
                     label_visibility="collapsed")

