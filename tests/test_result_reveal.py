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


def test_marks_shared_words_before_score_and_skips_replay():
    st = MagicMock()
    st.session_state = {}
    title, summary = "전기버스 <서울>", "서울역 앞에 전기버스 & 택시"
    args = (summary, "round")
    with patch.dict("sys.modules", streamlit=st), patch("games.result_reveal.time.sleep") as sleep:
        show_summary_before_score(*args, title=title, score=83)
        events = st.mock_calls
        score_index = next(i for i, event in enumerate(events) if event[0] == "progress")
        marked = [
            event.args[0] for event in events[:score_index]
            if event[0] == "empty().html" and "<mark>" in event.args[0]
        ]
        assert len(marked) == 2
        assert "<mark>전기버스</mark>" in marked[0] and "&lt;서울&gt;" in marked[0]
        assert "<mark>전기버스</mark>" in marked[1] and " &amp; " in marked[1]
        st.progress.assert_called_once_with(83, text="AI 유사도 · 83 / 100점")

        st.reset_mock()
        sleep.reset_mock()
        show_summary_before_score(*args, title=title, score=83)
        sleep.assert_not_called()
        assert st.empty.return_value.html.call_count == 2


def test_no_shared_words_still_displays_actual_model_score():
    st = MagicMock()
    st.session_state = {}
    with patch.dict("sys.modules", streamlit=st), patch("games.result_reveal.time.sleep"):
        show_summary_before_score("강수량 증가", "round", title="비 소식", score=100)
    assert "낱말" in st.caption.call_args.args[0]
    st.progress.assert_called_once_with(100, text="AI 유사도 · 100 / 100점")
