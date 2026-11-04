"""Checks for the shared AI-summary typing stream."""

from unittest.mock import patch

from games.result_reveal import type_summary_characters


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
