"""Portrait bank repayment screen with an animated coin deposit."""

from pathlib import Path

import streamlit as st

from .bank_forms import UNIT, _change_amount, _save_balances
from .bank_scene import asset_uri


REPAY_AMOUNT_KEY = "bank_repay_amount"
REPAY_SUCCESS_KEY = "bank_repay_success"


def _repayment_limit(coins: int, loan: int) -> int:
    """Never let a repayment exceed either the wallet or the loan balance."""
    if 0 < loan < UNIT and coins >= loan:
        return loan
    return max(0, min(coins, loan)) // UNIT * UNIT


def _selected_repayment(limit: int, selected: int | None) -> int:
    """Bound a previous selection when coins or debt have changed."""
    if limit < UNIT:
        return limit
    try:
        selected = int(selected) if selected is not None else UNIT
    except (TypeError, ValueError):
        selected = UNIT
    return max(UNIT, min(limit, selected // UNIT * UNIT))


def _image(name: str, css_class: str) -> str:
    uri = asset_uri(name)
    return f'<img class="{css_class}" src="{uri}" alt="" draggable="false">' if uri else ""


def pay_loan(coins: int, loan: int) -> None:
    """Render the existing loan-payoff transaction in a single mobile frame."""
    st.html(Path(__file__).with_suffix(".css"))
    temple = asset_uri("bank_temple")
    st.html(
        '<style>.st-key-bank-repay-screen {'
        f'--bank-repay-temple:url("{temple}");'
        '}</style>'
    )

    limit = _repayment_limit(coins, loan)
    amount = _selected_repayment(limit, st.session_state.get(REPAY_AMOUNT_KEY))
    if limit:
        # Set this before rendering widgets, as required by Streamlit's state API.
        st.session_state[REPAY_AMOUNT_KEY] = amount
    else:
        st.session_state.pop(REPAY_AMOUNT_KEY, None)

    successful = bool(st.session_state.pop(REPAY_SUCCESS_KEY, False))
    visual_class = "bank-repay-vault-scene is-success" if successful else "bank-repay-vault-scene"

    with st.container(key="bank-repay-screen", gap=None):
        st.html(
            '<header class="bank-repay-header">'
            '<h1>대출 상환</h1><p>갚을 금액을 선택하세요.</p>'
            '</header>'
        )
        st.html(
            f'<div class="{visual_class}" aria-hidden="true">'
            '<div class="bank-repay-spotlight"></div>'
            + _image("bank_repay_podium", "bank-repay-podium")
            + _image("bank_repay_coin", "bank-repay-drop-coin")
            + _image("bank_repay_safe", "bank-repay-safe")
            + '</div>'
        )

        with st.container(key="bank-repay-panel", gap=None):
            st.html('<h2 class="bank-repay-label">상환 금액</h2>')
            if limit:
                with st.container(key="bank-repay-stepper", horizontal=True,
                                  vertical_alignment="center", gap=None):
                    st.button(
                        "−", key=f"{REPAY_AMOUNT_KEY}_minus", help=f"{UNIT:,} C 줄이기",
                        disabled=amount <= UNIT,
                        on_click=_change_amount, args=(REPAY_AMOUNT_KEY, amount - UNIT),
                    )
                    st.html(f'<output class="bank-repay-amount" aria-live="polite">{amount:,} C</output>')
                    st.button(
                        "＋", key=f"{REPAY_AMOUNT_KEY}_plus", help=f"{UNIT:,} C 늘리기",
                        disabled=amount >= limit,
                        on_click=_change_amount, args=(REPAY_AMOUNT_KEY, amount + UNIT),
                    )
            else:
                reason = "상환할 대출금이 없습니다." if loan <= 0 else (
                    f"상환하려면 보유 코인이 {min(UNIT, loan):,} C 이상 필요합니다."
                )
                st.html(f'<p class="bank-repay-unavailable" role="status">{reason}</p>')

            st.html(
                '<div class="bank-repay-balance-row" aria-label="상환 예상 잔액">'
                '<div><span>현재 대출 잔액</span>'
                f'<strong>{loan:,} C</strong></div>'
                '<span class="bank-repay-arrow" aria-hidden="true">→</span>'
                '<div><span>상환 후 잔액</span>'
                f'<strong class="bank-repay-after">{max(0, loan - amount):,} C</strong></div>'
                '</div>'
            )

        label = f"{amount:,} C 상환하기" if amount else "상환할 금액 없음"
        if st.button(
            label, key="bank-repay-submit", icon=":material/savings:",
            type="primary", width="stretch", disabled=amount == 0,
        ):
            # Only animate once the update to Google Sheets succeeds.
            _save_balances(
                coins - amount, loan - amount, f"{amount:,} C를 상환했습니다.",
                success_state_key=REPAY_SUCCESS_KEY,
            )
