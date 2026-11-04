"""Checks for the news comparison reveal."""

from unittest.mock import MagicMock, patch

from games.result_reveal import show_summary_before_score, type_summary_characters


def test_unicode_summary_is_streamed_without_changes():
    sample = "첫 문장이다. 다음 문장도 이어진다! 😀"
    with patch("games.result_reveal.time.sleep"):
        assert "".join(type_summary_characters(sample)) == sample


def test_summary_strips_surrounding_whitespace_and_handles_empty():
    with patch("games.result_reveal.time.sleep"):
        assert "".join(type_summary_characters("  뉴스 요약.  ")) == "뉴스 요약."
        assert list(type_summary_characters("   ")) == []
        assert list(type_summary_characters(None)) == []


def test_typing_delays_do_not_exceed_expected_pause():
    with patch("games.result_reveal.time.sleep") as sleeper:
        chunks = list(type_summary_characters("뉴스, 요약."))
    assert "".join(chunks) == "뉴스, 요약."
    assert sleeper.call_count == len(chunks) - 1
    assert max(call.args[0] for call in sleeper.call_args_list) <= 0.12


def test_reveals_stored_model_values_before_score_and_skips_replay():
    st = MagicMock()
    st.session_state = {}
    summary = "서울역 앞에 전기버스 & 택시"
    title = "전기버스 <서울>"
    details = {
        "model_name": "BAAI/bge-reranker-v2-m3", "token_count": 37,
        "logit": 1.25, "normalized": 0.77729986, "score": 78,
    }
    with patch.dict("sys.modules", streamlit=st), patch("games.result_reveal.time.sleep") as sleep:
        show_summary_before_score(summary, "round", title=title, score=78, details=details)
        events = st.mock_calls
        score_index = next(i for i, event in enumerate(events) if event[0] == "progress")
        before_score = "\n".join(
            event.args[0] for event in events[:score_index]
            if event[0] in ("html", "empty().html")
        )
        assert "<mark>" not in before_score and "&lt;서울&gt;" in before_score
        steps = ["서울역 앞에 전기버스 &amp; 택시", details["model_name"], "37토큰", "1.2500", "0.7773"]
        positions = [before_score.index(step) for step in steps]
        assert positions == sorted(positions)
        assert st.progress.call_args.args[0] == 78

        st.reset_mock()
        sleep.reset_mock()
        show_summary_before_score(summary, "round", title=title, score=78, details=details)
        sleep.assert_not_called()
        assert st.progress.call_args.args[0] == 78


def test_old_round_keeps_saved_score_without_fabricating_inference_values():
    st = MagicMock()
    st.session_state = {}
    with patch.dict("sys.modules", streamlit=st), patch("games.result_reveal.time.sleep"):
        show_summary_before_score("폭우로 하천이 범람했다.", "round", title="도심 침수", score=78)
    assert st.progress.call_args.args[0] == 78
    assert "최종 점수만 저장" in st.caption.call_args.args[0]
    assert all("<data " not in call.args[0] for call in st.html.call_args_list)
