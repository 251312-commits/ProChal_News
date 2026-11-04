"""Loan documents and the bank's Google Sheets balance update."""

from contextlib import contextmanager
from pathlib import Path

import streamlit as st

from modules.db_handler import init_gspread
from .bank_scene import asset_uri

UNIT = 1_000
MAX_LOAN = 10_000
INTEREST_RATE = 0.20


def _save_balances(coins: int, loan: int, message: str) -> None:
    user = st.session_state.current_user_data
    student_id = str(user.get("학번", "")).strip()
    try:
        if not student_id:
            raise ValueError("Missing student ID")
        worksheet = init_gspread()
        # Column A identifies the student. C and D must be written together.
        student = worksheet.find(student_id, in_column=1)
        if student is None:
            raise LookupError("Student row unavailable")
        worksheet.update(range_name=f"C{student.row}:D{student.row}", values=[[coins, loan]])
    except Exception:
        st.error("거래를 저장하지 못했습니다. 잠시 후 다시 시도하세요.")
        return

    user.update({"코인": coins, "대출금": loan})
    st.toast(message)
    st.rerun()


@contextmanager
def _document(title: str, english: str, figures, terms: str):
    st.html(Path(__file__).with_suffix(".css"))
    paper = asset_uri("bank_paper")
    if paper:
        st.html(f'<style>.st-key-bank-form {{ --bank-paper: url("{paper}") }}</style>')
    wax = asset_uri("bank_wax_seal")
    seal = f'<img alt="" src="{wax}">' if wax else ""
    rows = "".join(f"<div><dt>{label}</dt><dd>{value:,} C</dd></div>" for label, value in figures)
    with st.container(key="bank-form"):
        st.html(
            f'<header class="bank-document-heading">{seal}<h1>{title}</h1>'
            f'<span lang="en">{english}</span></header>'
            f'<dl class="bank-figures">{rows}</dl>'
            f'<p class="bank-contract">{terms}</p>'
        )
        with st.container(key="bank-fields"):
            yield


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


def draw_loan(coins: int, loan: int) -> None:
    available = max(0, MAX_LOAN - loan)
    limit = available // UNIT * UNIT
    with _document(
        "대출 신청서", "LOAN APPLICATION",
        [("대출 단위", UNIT), ("이자율", "턴당 20% (복리)"), ("최대 대출 한도", MAX_LOAN)],
        f"한도 {MAX_LOAN:,} C · {UNIT:,} C 단위<br>"
        f"대출 잔액에 턴마다 {INTEREST_RATE:.0%} 복리 이자 적용",
    ):
        if limit < UNIT:
            st.html('<p class="bank-empty">추가로 신청할 수 있는 금액이 없습니다.</p>')
            return
        amount = _amount_selector("신청 금액", "bank_borrow_amount", limit, min(5_000, limit))
        st.html(
            '<div class="bank-summary">'
            f'<div><span>보유 코인</span><b>{coins:,} C</b></div>'
            f'<div><span>대출 잔액</span><b>{loan:,} C</b></div>'
            f'<div><span>추가 대출 가능액</span><b>{available:,} C</b></div>'
            '<p>ⓘ 대출 잔액에 대해 턴마다 20%의 이자가 복리로 추가됩니다.</p>'
            '</div>'
        )
        if st.button("대출 신청하기", key="bank-borrow-submit", type="primary", width="stretch"):
            _save_balances(coins + amount, loan + amount, f"{amount:,} C를 대출받았습니다.")


def pay_loan(coins: int, loan: int) -> None:
    limit = min(coins, loan) // UNIT * UNIT
    with _document(
        "대출 상환서", "LOAN REPAYMENT",
        [("대출 잔액", loan), ("보유 코인", coins)],
        f"보유 코인에서 {UNIT:,} C 단위로 상환<br>"
        f"남은 잔액에 턴마다 {INTEREST_RATE:.0%} 복리 이자 적용",
    ):
        if limit < UNIT:
            message = "상환할 대출금이 없습니다." if loan <= 0 else (
                f"상환하려면 대출 잔액과 보유 코인이 각각 {UNIT:,} C 이상이어야 합니다."
            )
            st.html(f'<p class="bank-empty">{message}</p>')
            return
        amount = _amount_selector("상환 금액", "bank_repay_amount", limit, limit)
        st.html(f'<p class="bank-estimate">상환 후 대출 잔액 <b>{loan - amount:,} C</b></p>')
        if st.button("대출 상환 확정", key="bank-repay-submit", type="primary", width="stretch"):
            _save_balances(coins - amount, loan - amount, f"{amount:,} C를 상환했습니다.")
