"""Loan documents and the bank's Google Sheets balance update."""

from contextlib import contextmanager
from pathlib import Path

import streamlit as st

from modules.account_math import account_amount
from modules.db_handler import BankBalancesChanged, init_gspread, save_bank_balances
from .bank_scene import asset_uri

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
        [("대출 잔액", loan), ("추가 대출 가능액", available)],
        f"한도 {MAX_LOAN:,} C · {UNIT:,} C 단위<br>"
        f"대출 잔액에 턴마다 {INTEREST_RATE:.0%} 복리 이자 적용",
    ):
        if limit < UNIT:
            st.html('<p class="bank-empty">추가로 신청할 수 있는 금액이 없습니다.</p>')
            return
        amount = _amount_selector("신청 금액", "bank_borrow_amount", limit, min(5_000, limit))
        st.html(
            f'<p class="bank-estimate">신청 금액의 다음 턴 이자 '
            f'<b>+{int(amount * INTEREST_RATE):,} C</b></p>'
        )
        if st.button("대출 신청 확정", key="bank-borrow-submit", type="primary", width="stretch"):
            _save_balances(coins + amount, loan + amount, f"{amount:,} C를 대출받았습니다.")


def pay_loan(coins: int, loan: int) -> None:
    """Compatibility entrypoint for the illustrated repayment view."""
    from .bank_repay import pay_loan as render_repayment

    render_repayment(coins, loan)
