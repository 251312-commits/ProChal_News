from pathlib import Path

import streamlit as st

from modules.ui_components import change_page


GAME_5_TUTORIAL_SEEN_KEY = "game_5_tutorial_seen"


def _start_game_5() -> None:
    st.session_state[GAME_5_TUTORIAL_SEEN_KEY] = True
    change_page("game_5")


def show_game_5_tutorial():
    with st.container(key="game5-guide", gap=None):
        st.html(Path(__file__).with_suffix(".css"))
        with st.container(key="game5-guide-nav", horizontal=True, gap=None):
            if st.button("메인으로", key="game5-guide-back"):
                change_page("main")
            if st.button("건너뛰기", key="game5-guide-skip"):
                _start_game_5()
        st.html(
            """
            <section class="game5-guide-sheet" aria-labelledby="game5-guide-title" lang="ko">
                <header class="game5-guide-heading">
                    <span>GAME 05</span><h1 id="game5-guide-title">일치율 구간 뉴스 맞히기</h1>
                    <p>제시된 구간에 들어갈 뉴스는 무엇일까?</p>
                </header>
                <ol aria-label="게임 진행 순서" role="list">
                    <li>
                        <h2><span>01</span>코인 베팅</h2>
                        <div class="game5-guide-icon">C</div>
                        <p>게임에 사용할 코인을<br><b>최소 1,000 C</b>부터 베팅한다.</p>
                    </li>
                    <li>
                        <h2><span>02</span>정답 구간 확인</h2>
                        <div class="game5-guide-icon">%</div>
                        <p>서로 다른 뉴스의 일치율을 가르는<br>정답 구간이 제시된다.</p>
                    </li>
                    <li>
                        <h2><span>03</span>뉴스 선택</h2>
                        <div class="game5-guide-icon">?</div>
                        <p>후보 뉴스 세 편을 읽고<br>구간에 해당하는 한 편을 고른다.</p>
                    </li>
                    <li>
                        <h2><span>04</span>결과 확인</h2>
                        <div class="game5-guide-icon">5x</div>
                        <p>정답이면 <b>베팅액의 5배</b>를 받고,<br>틀리면 베팅액을 잃는다.</p>
                    </li>
                </ol>
            </section>
            """
        )
        if st.button("게임 시작", key="game5-guide-start", type="primary", width="stretch"):
            _start_game_5()
