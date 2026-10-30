import streamlit as st
from modules.ui_components import change_page, show_placeholder_page
from modules.db_handler import init_gspread

# 정의된 함수: show_bank, process_turn_interest

def show_bank(): show_placeholder_page("🏦 은행")
