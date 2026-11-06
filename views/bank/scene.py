"""Layered illustrations for the bank lobby and the opening letter."""

from pathlib import Path

import streamlit as st

from modules.ui_components import load_local_image_as_base64


BANK_ART = Path(__file__).resolve().parents[2] / "assets" / "bank"


def asset_uri(stem: str) -> str:
    for suffix in (".avif", ".png"):
        path = BANK_ART / (stem + suffix)
        if path.is_file():
            return load_local_image_as_base64(str(path))
    return ""


def _art(stem: str, css_class: str) -> str:
    src = asset_uri(stem)
    return f'<img src="{src}" class="{css_class}" alt="" draggable="false">' if src else ""


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
    crest = load_local_image_as_base64(str(BANK_ART / "bank_crest.svg"))
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
        + f'<img class="bank-crest" src="{crest}" alt="">'
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
