"""Layered illustrations for the bank lobby and the opening letter."""

from pathlib import Path

import streamlit as st

from modules.ui_components import load_local_image_as_base64


BANK_ART = Path(__file__).resolve().parents[1] / "assets" / "bank"


def asset_uri(stem: str) -> str:
    return load_local_image_as_base64(str(BANK_ART / f"{stem}.avif"))


def _art(stem: str, css_class: str) -> str:
    return f'<img src="{asset_uri(stem)}" class="{css_class}" alt="" draggable="false">'


def _heading() -> str:
    return (
        '<header class="bank-lobby-heading">'
        '<div class="bank-facade">'
        + _art("bank_temple", "bank-temple-art")
        + '<h1>은행 대출</h1></div>'
        '<p>필요한 만큼 코인을 대출받고,<br>원하는 시점에 상환하세요.</p>'
        '</header>'
    )


def _letter(opening: bool = False) -> str:
    crest = (
        '<svg viewBox="0 0 64 36" fill="none" stroke="currentColor" '
        'stroke-width="2.3" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M13 12 32 3l19 9zM16 15h32M21 17v12m7-12v12m8-12v12m7-12v12'
        'M16 31h32m-36 4h40"/><circle cx="32" cy="9" r="1.1"/></svg>'
    )
    layers = ""
    if opening:
        layers = (
            '<div class="bank-unsealed">'
            + _art("bank_envelope_open", "bank-inside")
            + _art("bank_paper", "bank-emerging-sheet")
            + _art("bank_envelope_open", "bank-front-pocket")
            + '</div>'
        )
    return (
        '<div class="bank-lobby-art" aria-hidden="true"><div class="bank-still-life">'
        + _art("bank_cushion", "bank-velvet")
        + '<div class="bank-letter">'
        + layers
        + '<div class="bank-sealed">'
        + _art("bank_envelope_closed", "bank-envelope-face")
        + '<div class="bank-inscription">'
        + crest
        + '<span class="bank-calligraphy">대출 신청서</span>'
        '<span class="bank-engraving">LOAN APPLICATION</span>'
        '</div></div></div></div></div>'
    )


def bank_home(open_view) -> None:
    with st.container(key="bank-home"):
        st.html(_heading())
        st.html(_letter())
        with st.container(key="bank-actions", horizontal=True):
            st.button(
                "대출 신청하기", icon=":material/paid:", key="bank-home-draw",
                width="stretch", on_click=open_view, args=("draw_loan",),
            )
            st.button(
                "대출 상환하기", icon=":material/event_available:", key="bank-home-pay",
                width="stretch", on_click=open_view, args=("pay_loan",),
            )
        st.html(
            '<div class="bank-benefits"><span><i>%</i>턴당 이자 20%</span>'
            '<span><i>₵</i>유연한 상환</span><span><i>✓</i>안전한 거래</span></div>'
        )


def opening_scene() -> None:
    st.html(
        '<div class="bank-opening" aria-hidden="true">'
        + _heading() + _letter(opening=True)
        + '</div>'
    )
