"""Bank lobby and its two transaction routes."""

from pathlib import Path

import streamlit as st

from modules.account_math import account_amount
from modules.ui_components import change_page, load_local_image_as_base64
from views.bank_draw import draw_loan
from views.bank_forms import pay_loan
from views.bank_scene import bank_home, opening_scene


def _navigate(destination: str) -> None:
    # A widget callback runs before Streamlit redraws the selected page.
    st.session_state.bank_open_letter = (
        st.session_state.page == "bank" and destination == "draw_loan"
    )
    st.session_state.page = destination


def _navigation(page: str, coins: int) -> None:
    with st.container(key="bank-nav", horizontal=True, vertical_alignment="center"):
        back = "메인으로 돌아가기" if page == "bank" else "은행으로 돌아가기"
        st.button(
            back, icon=":material/arrow_back_ios_new:", key="bank-back", help=back,
            on_click=_navigate, args=("main" if page == "bank" else "bank",),
        )
        with st.container(key="bank-wallet", horizontal=True, vertical_alignment="center",
                          width="content", gap=None):
            st.html(
                '<div class="bank-balance"><span class="bank-coin" aria-hidden="true">₵</span>'
                f'<span><span class="bank-sr">보유 코인 </span>{coins:,} C</span></div>'
            )
            if page != "draw_loan":
                st.button(
                    "대출 신청서 열기", icon=":material/add:", key="bank-wallet-plus",
                    help="대출 신청서 열기", on_click=_navigate, args=("draw_loan",),
                )


def show_bank() -> None:
    user = st.session_state.get("current_user_data")
    if not user:
        st.error("로그인 정보를 찾을 수 없습니다. 다시 로그인해 주세요.")
        st.button("로그인 화면으로", on_click=change_page, args=("login",))
        return

    view_dir = Path(__file__).resolve().parent
    backdrop = load_local_image_as_base64(str(view_dir.parent / "assets" / "bet_background.jpg"))
    st.html(f'<style>.stApp:has(.st-key-bank-page) {{ --bank-backdrop: url("{backdrop}"); }}</style>')
    st.html(view_dir / "bank.css")
    st.html(view_dir / "bank_scene.css")

    page = st.session_state.page
    coins = account_amount(user.get("코인"))
    loan = account_amount(user.get("대출금"))
    with st.container(key="bank-page", gap=None):
        _navigation(page, coins)
        with st.container(key="bank-body", gap=None):
            if page == "bank":
                bank_home(_navigate)
            else:
                if st.session_state.pop("bank_open_letter", False):
                    opening_scene()
                if page == "draw_loan":
                    draw_loan(coins, loan)
                elif page == "pay_loan":
                    pay_loan(coins, loan)
