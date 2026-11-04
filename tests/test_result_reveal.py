"""Checks for the news comparison reveal."""

from base64 import b64decode
from math import log
import re
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
    with patch.dict("sys.modules", streamlit=st), patch("games.result_reveal.time.sleep") as sleep:
        show_summary_before_score(summary, "round", title=title, score=87.04, details=details, prediction=4)
        html = "\n".join(
            call.args[0] for call in st.mock_calls if call[0] in ("html", "empty().html")
        )
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


def test_old_round_keeps_the_saved_integer_even_with_an_old_logit():
    st = MagicMock()
    old_details = {
        "model_name": "BAAI/bge-reranker-v2-m3", "token_count": 37,
        "logit": 1.25, "normalized": 0.77729986, "score": 78,
    }
    with patch.dict("sys.modules", streamlit=st), patch("games.result_reveal.time.sleep"):
        for details in (old_details, None):
            st.reset_mock()
            st.session_state = {}
            show_summary_before_score("폭우로 하천이 범람했다.", "round", title="도심 침수", score=78, details=details)
            html = "\n".join(call.args[0] for call in st.mock_calls if call[0] in ("html", "empty().html"))
            assert "78점" in html
            assert "78.00" not in html and "77.73" not in html
            if details is None:
                assert "data:image/svg+xml" not in html
