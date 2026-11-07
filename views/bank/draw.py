"""Mobile loan application."""

from pathlib import Path

import streamlit as st

from modules.ui_components import load_local_image_url
from .draw_icons import icon
from .forms import INTEREST_RATE, MAX_LOAN, UNIT, _amount_selector, _save_balances
from .scene import BANK_ART, asset_uri


BORROW_SUCCESS_KEY = "bank_borrow_success"


def draw_loan(coins: int, loan: int, principal: int) -> None:
    st.html(Path(__file__).with_suffix(".css"))
    paper = asset_uri("bank_paper")
    temple = asset_uri("bank_temple")
    seal = asset_uri("bank_wax_seal")
    stamp = asset_uri("bank_stamp")
    postmark = load_local_image_url(str(BANK_ART / "bank_postmark.svg"))
    st.html(
        '<style>.st-key-bank-draw-screen {'
        f'--paper:url("{paper}"); --temple:url("{temple}"); --seal:url("{seal}");'
        f'--postmark:url("{postmark}"); --stamp:url("{stamp}");'
        '}</style>'
    )

    # The 10,000C limit applies to outstanding principal, NOT accrued interest.
    available = max(0, MAX_LOAN - principal)
    limit = available // UNIT * UNIT
    rate = int(INTEREST_RATE * 100)
    # The confirmation animation runs only on the rerun after Sheets saves.
    approved = bool(st.session_state.pop(BORROW_SUCCESS_KEY, False))
    # Use the real stamp already beside the submit button; no second stamp
    # is rendered at the top of the application.
    title_class = (
        "bank-draw-document-title bank-borrow-approved"
        if approved else "bank-draw-document-title"
    )

    with st.container(key="bank-draw-screen", gap=None):
        st.html(
            '<header class="bank-draw-masthead"><h1>은행 대출</h1>'
            '<p>지금 필요한 코인을 대출받으세요.</p></header>'
        )
        with st.container(key="bank-draw-parchment", gap=None):
            st.html(
                f'<div class="{title_class}"><h2>대출 신청서</h2>'
                '<span lang="en">LOAN APPLICATION</span></div>'
                '<dl class="bank-draw-terms" aria-label="대출 조건">'
                f'<div><dt>{icon("bag")}대출 단위</dt><dd>{UNIT:,} C</dd></div>'
                f'<div><dt>{icon("percent")}이자율</dt>'
                f'<dd class="bank-draw-rate">턴당 {rate}% (복리)</dd></div>'
                f'<div><dt>{icon("coins")}최대 대출 한도</dt><dd>{MAX_LOAN:,} C</dd></div></dl>'
            )
            with st.container(key="bank-draw-controls", gap=None):
                if limit >= UNIT:
                    amount = _amount_selector(
                        "신청 금액", "bank_borrow_amount", limit, min(5_000, limit)
                    )
                    if limit > UNIT:
                        st.html(
                            '<div class="bank-draw-range" aria-hidden="true">'
                            f'<span>{UNIT:,} C</span><span>{limit:,} C</span></div>'
                        )
                else:
                    amount = 0
                    st.html('<p class="bank-draw-no-credit">현재 추가로 대출할 수 있는 금액이 없습니다.</p>')

            st.html(
                '<section class="bank-draw-summary" aria-label="현재 대출 현황">'
                '<dl class="bank-draw-summary-grid">'
                f'<div><dt>{icon("coins", "#f2b454")}대출원금</dt><dd>{principal:,} C</dd></div>'
                f'<div><dt>{icon("bank", "#d99ae9")}총대출금</dt><dd>{loan:,} C</dd></div>'
                f'<div><dt>{icon("coins-plus", "#f2b454")}추가 대출 가능액</dt><dd>{limit:,} C</dd></div>'
                '</dl>'
                f'<p>ⓘ &nbsp;한도 {MAX_LOAN:,} C는 <strong>대출원금</strong> 기준입니다. '
                f'턴당 {rate}%의 복리 이자는 한도에 포함되지 않습니다.</p></section>'
            )
            if st.button(
                "대출 신청하기", key="bank-borrow-submit", icon=":material/account_balance:",
                type="primary", width="stretch", disabled=amount == 0,
            ):
                _save_balances(
                    coins + amount, loan + amount, f"{amount:,} C를 대출받았습니다.",
                    success_state_key=BORROW_SUCCESS_KEY,
                )
