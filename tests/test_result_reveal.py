"""Checks for the news comparison reveal."""

from base64 import b64decode
from math import isclose, log
import re
from unittest import TestCase
from unittest.mock import MagicMock, patch

from games.shared.result import show_summary_before_score, type_summary_characters


def _rendered_html(calls):
    return "\n".join(
        call.args[0] for call in calls if call[0] in ("html", "empty().html")
    )


def test_unicode_summary_is_streamed_without_changes():
    sample = "첫 문장이다. 다음 문장도 이어진다! 😀"
    with patch("games.shared.result.time.sleep"):
        assert "".join(type_summary_characters(sample)) == sample


def test_summary_strips_surrounding_whitespace_and_handles_empty():
    with patch("games.shared.result.time.sleep"):
        assert "".join(type_summary_characters("  뉴스 요약.  ")) == "뉴스 요약."
        assert list(type_summary_characters("   ")) == []
        assert list(type_summary_characters(None)) == []


def test_typing_delays_do_not_exceed_expected_pause():
    with patch("games.shared.result.time.sleep") as sleeper:
        chunks = list(type_summary_characters("뉴스, 요약."))
    assert "".join(chunks) == "뉴스, 요약."
    assert sleeper.call_count == len(chunks) - 1
    assert max(call.args[0] for call in sleeper.call_args_list) <= 0.12


def test_round_graph_uses_stored_score_and_skips_replay():
    st = MagicMock()
    st.session_state = {}
    summary = "서울역 앞에 전기버스 & 택시"
    title = "전기버스 <서울>"
    details = {
        "model_name": "BAAI/bge-reranker-v2-m3", "token_count": 37,
        "logit": log(0.8704 / (1 - 0.8704)), "normalized": 0.8704,
        "score_hundredths": 8704, "score": 87.04,
    }
    with (
        patch.dict("sys.modules", streamlit=st),
        patch("games.shared.result.time.monotonic", return_value=0),
        patch("games.shared.result.time.sleep") as sleep,
    ):
        st.attach_mock(sleep, "pause")
        show_summary_before_score(summary, "round", title=title, score=87.04, details=details, prediction=4)
        events = st.mock_calls
        hold = next(i for i, c in enumerate(events) if c[0] == "pause" and c.args == (2.6,))
        early = _rendered_html(events[:hold])
        late = _rendered_html(events[hold + 1:])
        assert 'data-reveal-phase="rolling">' in early and "??.??" in early
        assert "87.04" not in early and "data:image/svg+xml" not in early
        assert late.index('data-reveal-phase="landed">') < late.index("87.04점") < late.index("data:image/svg+xml")
        html = early + late
        assert "전기버스 &lt;서울&gt;" in html
        assert html.index("서울역 앞에 전기버스 &amp; 택시") < html.index("87.04점")
        assert 'aria-label="AI 유사도 87.04점"' in html
        assert '<span class="score-fraction">04</span>' in html
        assert '내 예측 <b>04</b>' in html
        assert "<mark>" not in html
        image = re.search(r'data:image/svg\+xml;base64,([a-zA-Z0-9+/=]+)', html)
        assert image, "The measured score should be visualized."
        diagram = b64decode(image.group(1)).decode()
        assert "<polyline" in diagram and "<circle" in diagram
        assert details["model_name"] in html and "bge-reranker-v2-m3" in diagram
        assert "37토큰" in diagram
        assert f"{details['logit']:.4f}" in diagram and "0.8704" in diagram

        st.reset_mock()
        sleep.reset_mock()
        show_summary_before_score(summary, "round", title=title, score=87.04, details=details, prediction=4)
        sleep.assert_not_called()
        rerun_html = _rendered_html(st.mock_calls)
        assert 'data-reveal-phase="settled">' in rerun_html
        assert 'data-reveal-phase="rolling">' not in rerun_html
        assert 'data-reveal-phase="landed">' not in rerun_html


def test_interrupted_drumroll_resumes_same_cue_for_remaining_time():
    st = MagicMock()
    st.session_state = {}
    with (
        patch.dict("sys.modules", streamlit=st),
        patch("games.shared.result.time.monotonic", return_value=0) as clock,
        patch("games.shared.result.time.sleep") as sleep,
    ):
        sleep.side_effect = InterruptedError
        with TestCase().assertRaises(InterruptedError):
            show_summary_before_score("글", "round", title="제목", score=87.04, score_precision=2)
        first_stage = st.empty.return_value.html.call_args.args[0]
        cue = re.search(r'data-reveal-id="([^"]+)"', first_stage).group(1)
        assert 'data-reveal-phase="rolling">' in first_stage
        clock.return_value = 1
        st.reset_mock()
        sleep.reset_mock()
        sleep.side_effect = None
        show_summary_before_score("글", "round", title="제목", score=87.04, score_precision=2)
        sleep.assert_called_once()
        assert isclose(sleep.call_args.args[0], 1.6)
        stages = [
            c.args[0] for c in st.empty.return_value.html.call_args_list
            if 'class="score-stage"' in c.args[0]
        ]
        assert len(stages) == 2 and all(f'data-reveal-id="{cue}"' in s for s in stages)
        assert 'data-reveal-phase="rolling">' in stages[0] and "87.04점" in stages[1]


def test_old_round_keeps_the_saved_integer_even_with_an_old_logit():
    st = MagicMock()
    old_details = {
        "model_name": "BAAI/bge-reranker-v2-m3", "token_count": 37,
        "logit": 1.25, "normalized": 0.77729986, "score": 78,
    }
    with patch.dict("sys.modules", streamlit=st), patch("games.shared.result.time.sleep"):
        for details in (old_details, None):
            st.reset_mock()
            st.session_state = {}
            show_summary_before_score("폭우로 하천이 범람했다.", "round", title="도심 침수", score=78, details=details)
            html = "\n".join(call.args[0] for call in st.mock_calls if call[0] in ("html", "empty().html"))
            assert "78점" in html
            assert "78.00" not in html and "77.73" not in html
            if details is None:
                assert "data:image/svg+xml" not in html
