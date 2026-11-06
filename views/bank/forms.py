"""Loan documents and the bank's Google Sheets balance update."""


import streamlit as st

from modules.account_math import account_amount
from modules.transactions import (
    BalanceChanged, TransactionError, bank_transaction, transaction_id, update_session_balances,
)

UNIT = 1_000
MAX_LOAN = 10_000
INTEREST_RATE = 0.20


def _save_balances(coins: int, loan: int, message: str, *, success_state_key: str | None = None) -> None:
    """Apply one bank operation via the locked ledger before showing success."""
    user = st.session_state.current_user_data
    before_coins = account_amount(user.get("코인"), strict=True)
    before_loan = account_amount(user.get("대출금"), strict=True)
    coin_delta, loan_delta = coins - before_coins, loan - before_loan
    if not coin_delta or coin_delta != loan_delta:
        st.error("대출 거래 금액이 올바르지 않습니다.")
        return
    kind = "borrow" if loan_delta > 0 else "repay"
    amount = abs(loan_delta)
    pending_key = "bank_pending_transaction"
    pending = st.session_state.get(pending_key)
    if pending and (pending["kind"], pending["amount"]) != (kind, amount):
        st.error("확인되지 않은 은행 거래가 있습니다. 이전 금액으로 다시 시도하세요.")
        return
    if not pending:
        pending = {"kind": kind, "amount": amount, "id": transaction_id(kind)}
        st.session_state[pending_key] = pending

    try:
        bank_transaction(kind, amount, pending["id"])
    except BalanceChanged as changed:
        # A rejected stale request is safe to abandon. Refresh the UI first.
        update_session_balances(changed.balances)
        st.session_state.pop(pending_key, None)
        st.toast("잔액이 변경되었습니다. 새 잔액을 확인한 뒤 다시 신청하세요.")
        st.rerun()
        return
    except (TransactionError, ValueError) as exc:
        # Keep the transaction ID for a retry after an ambiguous timeout.
        st.error(str(exc))
        return

    st.session_state.pop(pending_key, None)
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

