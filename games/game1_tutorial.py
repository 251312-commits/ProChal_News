from pathlib import Path

import streamlit as st

from modules.ui_components import change_page, load_local_image_as_base64


def show_game_1_tutorial():
    art = Path(__file__).resolve().parents[1] / "assets" / "game1_guide"
    steps = (
        ("bet", "코인 베팅", "금액을 정해 베팅한다.<br>최소 <b>1,000 C</b>"),
        ("news", "기사 선택", "레버를 내린 뒤<br>기사 한 편을 골라 읽는다."),
        ("digits", "두 자리 예측", "▲▼로 소수점 뒤 두 자리 선택<br>예시　87.04점 → <b>04</b>"),
        ("result", "결과 확인", "적중　+베팅액의 <b>100배</b><br>실패　−베팅액"),
    )
    cards = "".join(
        f'<li><h2><span>{number:02d}</span>{title}</h2>'
        f'<img src="{load_local_image_as_base64(str(art / (name + ".webp")))}" alt="">'
        f'<p>{caption}</p></li>'
        for number, (name, title, caption) in enumerate(steps, 1)
    )
    with st.container(key="game1-guide", gap=None):
        st.html(Path(__file__).with_suffix(".css"))
        with st.container(key="game1-guide-nav", horizontal=True, gap=None):
            if st.button("메인으로", key="game1-guide-back"):
                change_page("main")
            if st.button("건너뛰기", key="game1-guide-skip"):
                change_page("game_1")
        st.html(f"""
            <section class="game1-guide-sheet" aria-labelledby="game1-guide-title" lang="ko">
                <header class="game1-guide-heading">
                    <span>GAME 01</span><h1 id="game1-guide-title">뉴스 유사도 예측</h1>
                    <p>기사 제목과 AI 요약문은 얼마나 비슷할까?</p>
                </header>
                <ol aria-label="게임 진행 순서" role="list">{cards}</ol>
            </section>
        """)
        if st.button("베팅하러 가기", key="game1-guide-start", type="primary", width="stretch"):
            change_page("game_1")
