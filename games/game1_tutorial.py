from pathlib import Path

import streamlit as st

from modules.ui_components import change_page, load_local_image_as_base64


def show_game_1_tutorial():
    poster = Path(__file__).resolve().parents[1] / "assets" / "game1_tutorial.webp"
    with st.container(key="game1-guide", gap="small"):
        st.html(Path(__file__).with_suffix(".css"))
        st.html(f"""
            <section class="game1-guide-sheet" aria-labelledby="game1-guide-title" lang="ko">
                <img src="{load_local_image_as_base64(str(poster))}" alt="" width="1122" height="1402">
                <div class="game1-guide-copy">
                    <h1 id="game1-guide-title">뉴스 유사도 예측</h1>
                    <p>기사 제목과 AI 요약문의 유사도 점수가 87.04점이면 정답은 <strong>04</strong>다.</p>
                    <ol>
                        <li>1,000 C 이상 베팅한다.</li>
                        <li>추천 기사 중 한 편을 골라 읽는다.</li>
                        <li>▲▼로 소수점 뒤 두 자리를 골라 제출한다.</li>
                    </ol>
                    <p>적중하면 베팅액의 100배를 얻고, 실패하면 베팅액을 잃는다.</p>
                </div>
            </section>
        """)
        with st.container(key="game1-guide-actions", horizontal=True, gap="small"):
            if st.button("메인으로", key="game1-guide-back", width="stretch"):
                change_page("main")
            if st.button("베팅하러 가기", key="game1-guide-start", type="primary", width="stretch"):
                change_page("game_1")
