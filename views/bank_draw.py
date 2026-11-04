"""Illustrated, viewport-sized loan application. Repayment remains independent."""

from pathlib import Path
from html import escape

import streamlit as st

from .bank_scene import asset_uri
from .bank_forms import MAX_LOAN, INTEREST_RATE, UNIT, _amount_selector, _save_balances


def _image(stem: str, css_class: str) -> str:
    uri = asset_uri(stem)
    return f'<img class="{css_class}" src="{uri}" alt="" draggable="false">' if uri else ""


def draw_loan(coins: int, loan: int) -> None:
    """Render the reference-style application without altering loan accounting."""
    st.html(Path(__file__).with_suffix(".css"))
    paper = asset_uri("bank_paper")
    if paper:
        st.html(
            '<style>.st-key-bank-draw-parchment {'
            f'--bank-draw-paper:url("{paper}");'
            '}</style>'
        )

    available = max(0, MAX_LOAN - loan)
    limit = (available // UNIT) * UNIT
    rate = int(INTEREST_RATE * 100)

    with st.container(key="bank-draw-screen", gap=None):
        st.html(
            '<header class="bank-draw-masthead">'
            + _image("bank_temple", "bank-draw-temple")
            + '<div class="bank-draw-masthead-text"><h1>은행 대출</h1>'
              '<p>지금 필요한 코인을 대출받으세요.</p></div>'
              '</header>'
        )

        with st.container(key="bank-draw-parchment", gap=None):
            st.html(
                '<div class="bank-draw-document-title">'
                + _image("bank_wax_seal", "bank-draw-wax")
                + _image("bank_stamp", "bank-draw-postmark")
                + '<h2>대출 신청서</h2>'
                  '<div class="bank-draw-english">LOAN APPLICATION</div>'
                  '</div>'
            )
            st.html(
                '<div class="bank-draw-terms" aria-label="대출 조건">'
                f'<div><span class="bank-draw-term-label"><i>♛</i>대출 단위</span><b>{UNIT:,} C</b></div>'
                f'<div><span class="bank-draw-term-label"><i>%</i>이자율</span>'
                f'<b class="bank-draw-rate">턴당 {rate}% (복리)</b></div>'
                f'<div><span class="bank-draw-term-label"><i>▤</i>최대 대출 한도</span>'
                f'<b>{MAX_LOAN:,} C</b></div>'
                '</div>'
                '<div class="bank-draw-ornament" aria-hidden="true"><span>❖</span></div>'
            )

            with st.container(key="bank-draw-controls", gap=None):
                if limit >= UNIT:
                    amount = _amount_selector(
                        "신청 금액", "bank_borrow_amount", limit, min(5_000, limit)
                    )
                    # The range is calculated from actual available credit, not
                    # from the artwork's illustrative 10,000 C example.
                    st.html(
                        '<div class="bank-draw-range">'
                        f'<span>{UNIT:,} C</span><span>{limit:,} C</span></div>'
                    )
                else:
                    amount = 0
                    st.html(
                        '<p class="bank-draw-no-credit">현재 추가로 대출할 수 있는 금액이 없습니다.</p>'
                    )

                st.html(
                    '<section class="bank-draw-summary" aria-label="현재 대출 현황">'
                    '<div class="bank-draw-summary-grid">'
                    f'<div><i>🪙</i><span>보유 코인</span><b>{coins:,} C</b></div>'
                    f'<div><i>♜</i><span>대출 잔액</span><b>{loan:,} C</b></div>'
                    f'<div><i>▤</i><span>추가 대출 가능액</span><b class="bank-draw-gold">{available:,} C</b></div>'
                    '</div>'
                    f'<p><span>ⓘ</span> 대출 잔액에 대해 턴마다 '
                    f'<strong>{rate}%</strong>의 이자가 복리로 추가됩니다.</p>'
                    '</section>'
                )

                st.html('<div class="bank-draw-action-heading" aria-hidden="true"></div>')
                if st.button(
                    "대출 신청하기", key="bank-borrow-submit",
                    icon=":material/account_balance:", type="primary",
                    use_container_width=True, disabled=amount == 0,
                ):
                    _save_balances(
                        coins + amount, loan + amount,
                        f"{amount:,} C를 대출받았습니다.",
                    )
            st.html(_image("bank_stamp", "bank-draw-decorative-stamp"))
