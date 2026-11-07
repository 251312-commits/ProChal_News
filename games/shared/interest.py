"""Shared end-of-turn loan interest, applied before any settled result is shown.

Google Sheets/Apps Script is authoritative: its locked interest:<round_id>
transaction updates debt and the ledger exactly once, including after retries.
"""

import streamlit as st

from modules.account_math import account_amount
from modules.transactions import TransactionError, apply_round_interest

INTEREST_RATE_PERCENT = 20


def compound_balance_after_turn(principal: int) -> int:
    """Return debt after one 20%-compound-interest turn (round up to whole C)."""
    debt = account_amount(principal, strict=True)
    return debt + (debt * INTEREST_RATE_PERCENT + 99) // 100


def apply_end_of_turn_interest(game: str) -> bool:
    """Close a settled turn once; return False to suppress results if not confirmed."""
    round_id = st.session_state.get(f"{game}_round_id")
    if not round_id:
        st.error("이자를 처리할 라운드 번호를 찾을 수 없습니다.")
        return False

    receipt_key = f"{game}_interest_receipt"
    receipt = st.session_state.get(receipt_key)
    if not isinstance(receipt, dict) or receipt.get("round_id") != round_id:
        try:
            confirmed = apply_round_interest(game)
        except TransactionError as exc:
            st.error(f"턴 종료 이자를 확정하지 못했습니다: {exc}")
            return False
        receipt = {"round_id": round_id, **confirmed}
        st.session_state[receipt_key] = receipt

    # Verify the server receipt against the documented interest formula.
    if receipt["new_loan"] != compound_balance_after_turn(receipt["loan_before"]):
        st.error("이자 계산 기록이 일치하지 않아 결과를 표시할 수 없습니다.")
        return False

    if receipt["charged"]:
        st.caption(
            f"턴 종료 · 대출 이자 {INTEREST_RATE_PERCENT}% (복리): "
            f"+{receipt['charged']:,} C · 이자 부과 후 대출금: {receipt['new_loan']:,} C"
        )
    return True
