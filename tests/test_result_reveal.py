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



def test_score_waits_for_tap_and_never_advances_automatically():
    st = MagicMock()
    st.session_state = {}
    st.button.return_value = False
    details = {
        "model_name": "BAAI/bge-reranker-v2-m3", "token_count": 37,
        "logit": log(0.8704 / (1 - 0.8704)), "normalized": 0.8704,
        "score_hundredths": 8704, "score": 87.04,
    }
    with (
        patch.dict("sys.modules", streamlit=st),
        patch("games.shared.result.time.monotonic", return_value=0) as clock,
        patch("games.shared.result.time.sleep") as sleep,
    ):
        done = show_summary_before_score(
            "서울역 앞에 전기버스 & 택시", "round",
            title="전기버스 <서울>", score=87.04, details=details, prediction=4,
        )
        assert done is False
        hidden = _rendered_html(st.mock_calls)
        assert 'data-reveal-phase="ready">' in hidden
        assert "??.??" in hidden
        assert "87.04" not in hidden and "data:image/svg+xml" not in hidden
        assert "내 예측" not in hidden
        assert st.session_state["round"]["phase"] == "ready"
        assert st.button.call_args.kwargs["key"] == "score_tap_round"

        # Even after arbitrary elapsed time, the same round remains masked.
        st.reset_mock()
        sleep.reset_mock()
        clock.return_value = 100_000
        done = show_summary_before_score(
            "서울역 앞에 전기버스 & 택시", "round",
            title="전기버스 <서울>", score=87.04, details=details, prediction=4,
        )
        assert done is False
        sleep.assert_not_called()
        assert "87.04" not in _rendered_html(st.mock_calls)
        assert st.session_state["round"]["phase"] == "ready"

        # A real button press releases the result after one short drumroll.
        st.reset_mock()
        sleep.reset_mock()
        st.button.return_value = True
        done = show_summary_before_score(
            "서울역 앞에 전기버스 & 택시", "round",
            title="전기버스 <서울>", score=87.04, details=details, prediction=4,
        )
        assert done is True
        sleep.assert_called_once_with(1.05)
        html = _rendered_html(st.mock_calls)
        assert html.index('data-reveal-phase="ready">') < html.index('data-reveal-phase="rolling">')
        assert html.index('data-reveal-phase="rolling">') < html.index('data-reveal-phase="landed">')
        assert html.index('data-reveal-phase="landed">') < html.index("data:image/svg+xml")
        assert 'aria-label="AI 유사도 87.04점"' in html
        assert '<span class="score-fraction">04</span>' in html
        assert '내 예측 <b>04</b>' in html
        assert "<mark>" not in html
        image = re.search(r'data:image/svg\\+xml;base64,([a-zA-Z0-9+/=]+)', html)
        assert image
        diagram = b64decode(image.group(1)).decode()
        assert "<polyline" in diagram and "<circle" in diagram
        assert "bge-reranker-v2-m3" in diagram and "37토큰" in diagram

        st.reset_mock()
        sleep.reset_mock()
        show_summary_before_score("서울역 앞에 전기버스 & 택시", "round",
                                  title="전기버스 <서울>", score=87.04,
                                  details=details, prediction=4)
        sleep.assert_not_called()
        again = _rendered_html(st.mock_calls)
        assert 'data-reveal-phase="settled">' in again
        assert 'data-reveal-phase="ready">' not in again
        st.button.assert_not_called()


def test_interrupted_tapped_drumroll_resumes_remaining_time():
    st = MagicMock()
    st.session_state = {}
    st.button.return_value = True
    with (
        patch.dict("sys.modules", streamlit=st),
        patch("games.shared.result.time.monotonic", return_value=0) as clock,
        patch("games.shared.result.time.sleep") as sleep,
    ):
        sleep.side_effect = InterruptedError
        with TestCase().assertRaises(InterruptedError):
            show_summary_before_score("글", "round", title="제목", score=87.04, score_precision=2)
        first = [
            call.args[0] for call in st.empty.return_value.html.call_args_list
            if 'class="score-stage"' in call.args[0]
        ]
        assert any('data-reveal-phase="rolling">' in stage for stage in first)
        cue = re.search(r'data-reveal-id="([^"]+)"', first[-1]).group(1)
        assert st.session_state["round"]["phase"] == "rolling"
        clock.return_value = 0.45
        st.reset_mock()
        sleep.reset_mock()
        sleep.side_effect = None
        done = show_summary_before_score("글", "round", title="제목", score=87.04, score_precision=2)
        assert done is True
        sleep.assert_called_once()
        assert isclose(sleep.call_args.args[0], 0.60)
        stages = [
            c.args[0] for c in st.empty.return_value.html.call_args_list
            if 'class="score-stage"' in c.args[0]
        ]
        assert len(stages) == 2 and all(f'data-reveal-id="{cue}"' in stage for stage in stages)
        assert 'data-reveal-phase="rolling">' in stages[0]
        assert 'data-reveal-phase="landed">' in stages[1] and "87.04점" in stages[1]
        st.button.assert_not_called()


def test_anywhere_tap_is_delegated_only_when_ready():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    sound = (root / "sounds" / "score_roll.js").read_text(encoding="utf-8")
    assert "revealOnScreenTap" in sound
    assert 'data-reveal-phase="ready"' in sound
    assert 'if (!event.isTrusted)' in sound
    assert "button.click()" in sound
    for file in ("games/game1/game1.py", "games/game2.py", "games/game3.py"):
        source = (root / file).read_text(encoding="utf-8")
        assert "if not show_summary_before_score(" in source

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
