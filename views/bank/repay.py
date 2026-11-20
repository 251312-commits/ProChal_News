"""Portrait bank repayment screen with an animated coin deposit."""

from pathlib import Path

import streamlit as st

from .forms import _save_balances
from .scene import asset_uri


REPAY_AMOUNT_KEY = "bank_repay_amount"
REPAY_SUCCESS_KEY = "bank_repay_success"
# Repayment amounts follow 1,000 C increments and the current debt remainder.
REPAY_UNIT = 1_000


def _repayment_options(coins: int, loan: int) -> tuple[int, ...]:
    """Return valid repayments affordable with the wallet's current coins.

    For a 2,532 C loan the options are 1,000, 1,532, 2,000, 2,532.
    The remainder alone (532 C) is not an option unless the entire loan
    is below 1,000 C, in which case only full repayment is offered.
    """
    if coins <= 0 or loan <= 0:
        return ()
    if loan < REPAY_UNIT:
        return (loan,) if coins >= loan else ()

    limit = min(coins, loan)
    remainder = loan % REPAY_UNIT
    amounts = []
    for base in range(REPAY_UNIT, limit + 1, REPAY_UNIT):
        amounts.append(base)
        if remainder and base + remainder <= limit:
            amounts.append(base + remainder)
    return tuple(sorted(amounts))


def _selected_repayment(options: tuple[int, ...], selected: int | None) -> int:
    """Keep the chosen amount valid after wallet or loan changes."""
    if not options:
        return 0
    try:
        chosen = int(selected) if selected is not None else options[0]
    except (TypeError, ValueError):
        chosen = options[0]
    return max((amount for amount in options if amount <= chosen), default=options[0])


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

    options = _repayment_options(coins, loan)
    amount = _selected_repayment(options, st.session_state.get(REPAY_AMOUNT_KEY))
    if options:
        # Set this before rendering widgets, as required by Streamlit's state API.
        st.session_state[REPAY_AMOUNT_KEY] = amount
    else:
        st.session_state.pop(REPAY_AMOUNT_KEY, None)

    successful = bool(st.session_state.pop(REPAY_SUCCESS_KEY, False))
    visual_class = "bank-repay-vault-scene is-success" if successful else "bank-repay-vault-scene"

    with st.container(key="bank-repay-screen", gap=None):
        st.html(
            '<header class="bank-repay-header">'
            '<h1>대출 상환</h1>'
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
            if options:
                with st.container(key="bank-repay-slider-field", gap=None):
                    st.html(
                        f'<output class="bank-repay-amount" aria-live="polite">{amount:,} C</output>'
                    )
                    if len(options) > 1:
                        amount = st.select_slider(
                            "상환 금액", options=options, key=REPAY_AMOUNT_KEY,
                            format_func=lambda value: f"{value:,} C",
                            label_visibility="collapsed",
                        )
                        st.html(
                            '<div class="bank-repay-range" aria-hidden="true">'
                            f'<span>{options[0]:,} C</span><span>{options[-1]:,} C</span></div>'
                        )
            else:
                minimum = loan if 0 < loan < REPAY_UNIT else REPAY_UNIT
                reason = "상환할 대출금이 없습니다." if loan <= 0 else (
                    f"상환하려면 보유 코인이 {minimum:,} C 이상 필요합니다."
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
            st.caption("상환액은 발생한 이자부터 차감하고, 남은 금액으로 대출원금을 갚습니다.")

        label = f"{amount:,} C 상환하기" if amount else "상환할 금액 없음"
        if st.button(
            label, key="bank-repay-submit", icon=":material/savings:",
            type="primary", width="stretch", disabled=amount == 0,
        ):
            # Reject stale or manipulated selections before creating a transaction.
            if amount not in options:
                st.error("선택할 수 없는 상환 금액입니다. 금액을 다시 선택하세요.")
                return
            # Only animate once the update to Google Sheets succeeds.
            _save_balances(
                coins - amount, loan - amount, f"{amount:,} C를 상환했습니다.",
                success_state_key=REPAY_SUCCESS_KEY,
            )
