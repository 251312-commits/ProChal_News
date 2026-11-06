def show_game3():
  show_placeholder_page(title_name)


current_balance + reward
                    )

                    new_streak = (
                        current_streak + 1 if is_win else 0
                    )

                    # ==================================
                    # STEP 6. Google Sheets 업데이트
                    # ==================================

                    ws.update_cell(user_row_idx, 3, new_balance)
                    ws.update_cell(user_row_idx, 4, new_streak)

                    st.session_state.current_user_data["코인"] = new_balance
                    st.session_state.current_user_data["연승"] = new_streak

                    # 결과 저장
                    st.session_state.game_3_result = {

                        "actual_score": actual_score,
                        "score_details": score_details,
                        "integer_score": integer_score,
                        "ai_result": ai_result,
                        "user_choice": user_choice,
                        "bet": bet_coin,
                        "reward": reward,
                        "is_win": is_win,
                        "new_coins": new_balance,
                        "new_streak": new_streak,
                        "title": title,
                        "url": url,
                        "summary": summary_text

                    }

                    st.rerun()

                except Exception as e:

                    st.error(
                        f"게임 진행 중 오류가 발생했습니다: {e}"
                    )


def _show_game_3_result(res):
    show_summary_before_score(
        res["summary"], "game_3_summary_revealed",
        title=res["title"], score=res["actual_score"],
        details=res.get("score_details"),
    )

    st.markdown("---")
    st.markdown("### 🏆 최종 게임 결과")

    if res["is_win"]:

        st.balloons()
        st.success("정답입니다! 베팅 성공!")

    else:

        st.error("아쉽습니다! 베팅 실패!")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("내 선택", res["user_choice"])

    with col2:
        st.metric("정수 부분의 홀짝", f"{res['integer_score']} · {res['ai_result']}")

    with st.expander("분석한 뉴스 기사 정보"):

        st.write(res["title"])
        st.markdown(f"[기사 원문 열기]({res['url']})")

    st.markdown(f"""
    <div style="
        background:#110022;
        border:2px solid #8A2BE2;
        padding:20px;
        border-radius:12px;
        text-align:center;
        color:white;
    ">
        <p>베팅 금액: {res['bet']:,} C</p>

        <h1 style="color:{'#00ffcc' if res['is_win'] else '#ff5555'};">
            {res['reward']:+,} C
        </h1>

        <p>현재 보유 코인</p>

        <h2 style="color:#ffd700;">
            {res['new_coins']:,} C
        </h2>

        <p>현재 연승 기록: {res['new_streak']} 연승</p>

    </div>
    """, unsafe_allow_html=True)

    # ======================================
    # STEP 8. 다시 도전하기 / 메인으로
    # ======================================

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "🔄 다시 도전하기",
            use_container_width=True
        ):

            reset_game_3_state()
            st.rerun()

    with col2:

        if st.button(
            "⬅️ 메인으로 돌아가기",
            use_container_width=True
        ):

            reset_game_3_state()
            change_page("main")
