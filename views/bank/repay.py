"""Portrait bank repayment screen with an animated coin deposit."""

from pathlib import Path

import streamlit as st

from .forms import _save_balances
from .scene import asset_uri


REPAY_AMOUNT_KEY = "bank_repay_amount"
REPAY_SUCCESS_KEY = "bank_repay_success"
# Repayment has its own 1-coin step; new borrowing still uses 1,000 C.
REPAY_UNIT = 1


def _repayment_limit(coins: int, loan: int) -> int:
    """Allow repayment down to 1 C without exceeding wallet or total debt."""
    return max(0, min(coins, loan))


def _selected_repayment(limit: int, selected: int | None) -> int:
    """Clamp previous slider state when the wallet or loan balance changes."""
    if limit < REPAY_UNIT:
        return 0
    default = min(1_000, limit)
    try:
        selected = int(selected) if selected is not None else default
    except (TypeError, ValueError):
        selected = default
    return max(REPAY_UNIT, min(limit, selected))


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
                with st.container(key="bank-repay-slider-field", gap=None):
                    st.html(
                        f'<output class="bank-repay-amount" aria-live="polite">{amount:,} C</output>'
                    )
                    if limit > REPAY_UNIT:
                        amount = st.slider(
                            "상환 금액", min_value=REPAY_UNIT, max_value=limit,
                            step=REPAY_UNIT, key=REPAY_AMOUNT_KEY, format="%d C",
                            label_visibility="collapsed",
                        )
                        st.html(
                            '<div class="bank-repay-range" aria-hidden="true">'
                            f'<span>{REPAY_UNIT:,} C</span><span>{limit:,} C</span></div>'
                        )
            else:
                reason = "상환할 대출금이 없습니다." if loan <= 0 else (
                    f"상환하려면 보유 코인이 {REPAY_UNIT:,} C 이상 필요합니다."
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
            # Only animate once the update to Google Sheets succeeds.
            _save_balances(
                coins - amount, loan - amount, f"{amount:,} C를 상환했습니다.",
                success_state_key=REPAY_SUCCESS_KEY,
            )
