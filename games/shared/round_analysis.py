"""Per-round checkpoints for costly news summaries and similarity inference.

A transaction failure or Streamlit rerun must not produce a new AI verdict for
the same confirmed round. Intermediate summaries survive scoring errors.
"""
import asyncio
from collections.abc import Mapping
from hashlib import sha256
from math import isfinite


def analyze_round_once(
    state, game_id: str, *, title: str, article_text: str,
    summarize, similarity, fallback_to_title: bool = False,
) -> tuple[str, dict]:
    """Cache one summary and one score for one user's round and article.

    Wallet settlements remain owned by the caller. Retrying after a failed
    settlement reuses this score instead of asking the models for a new one.
    """
    title = str(title or "").strip()
    article_text = str(article_text or "").strip()
    if not title or not article_text:
        raise ValueError("분석할 기사 제목 또는 본문이 비어 있습니다.")

    identity = sha256("\0".join((
        str(state.get("current_user") or ""), game_id,
        str(state.get(f"{game_id}_round_id") or ""), title, article_text,
    )).encode("utf-8")).hexdigest()
    key = f"{game_id}_analysis_checkpoint"
    checkpoint = state.get(key)
    if not isinstance(checkpoint, dict) or checkpoint.get("identity") != identity:
        checkpoint = {"identity": identity}
        state[key] = checkpoint

    if "summary" not in checkpoint:
        text = asyncio.run(summarize(article_text))
        if not isinstance(text, str) or not text.strip():
            if not fallback_to_title:
                raise ValueError("뉴스 본문 요약 결과가 비어 있습니다.")
            text = title
        checkpoint["summary"] = text.strip()

    if "score_details" not in checkpoint:
        details = similarity(checkpoint["summary"], title)
        if not isinstance(details, Mapping) or isinstance(details.get("score"), bool):
            raise ValueError("뉴스 유사도 결과가 올바르지 않습니다.")
        try:
            value = float(details["score"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("뉴스 유사도 점수가 비어 있거나 올바르지 않습니다.") from exc
        if not isfinite(value) or not 0 <= value <= 100:
            raise ValueError("뉴스 유사도 점수는 0~100 범위여야 합니다.")
        checkpoint["score_details"] = dict(details)

    return checkpoint["summary"], checkpoint["score_details"]
