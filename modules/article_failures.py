"""Shared article-load failure handling.

Exclusions are immediate in the current Streamlit session. A locked Apps
Script endpoint counts failures across all users; failure to reach that endpoint
must never trap a player in a broken article.
"""
from __future__ import annotations

import logging
import re
from uuid import uuid4

import requests

LOGGER = logging.getLogger(__name__)
EXCLUDED_URLS_KEY = "_unavailable_article_urls"

# These failures may affect every article at once, so never delete pool entries
# because of timeouts, DNS errors, rate limits or server-side outages.
_TRANSIENT_MARKERS = re.compile(
    r"timed?\s*out|timeout|connection\s*(?:error|reset|refused|aborted)|"
    r"network|dns|name\s+resolution|temporary|too\s+many\s+requests|"
    r"(?:http\s*)?(?:429|500|502|503|504)\b",
    re.IGNORECASE,
)


def is_transient_article_error(error: Exception | None) -> bool:
    if error is None:
        return False
    if isinstance(error, (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                          ConnectionError, TimeoutError)):
        return True
    return bool(_TRANSIENT_MARKERS.search(str(error)))


def excluded_article_urls() -> set[str]:
    import streamlit as st

    return set(st.session_state.get(EXCLUDED_URLS_KEY, set()))


def report_article_failure(url: str, error: Exception | None = None, *, event_id: str | None = None) -> dict | None:
    """Skip a broken URL now and report a permanent failure, idempotently.

    Each call represents one actual fetch attempt. An optional event_id lets
    callers safely retry confirmation without counting the same attempt twice.
    Returns an acknowledgment when the deployed Apps Script supports tracking.
    """
    import streamlit as st
    from modules.db_handler import article_url_hash, normalize_article_url

    canonical = normalize_article_url(url)
    if not canonical:
        return None
    excluded = st.session_state.setdefault(EXCLUDED_URLS_KEY, set())
    excluded.add(canonical)
    if is_transient_article_error(error):
        return {"tracked": False, "transient": True}

    try:
        endpoint = str(st.secrets["transaction_endpoint"])
        token = str(st.secrets["transaction_token"])
        if not endpoint.startswith("https://script.google.com/macros/s/"):
            return None
        response = requests.post(
            endpoint,
            json={
                "kind": "article_failure",
                "token": token,
                "url": canonical,
                "url_hash": article_url_hash(canonical),
                "event_id": event_id or uuid4().hex,
            },
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and result.get("ok") is True and result.get("tracked") is True:
            return result
        LOGGER.warning("Article failure gateway did not acknowledge: %s", result)
    except (KeyError, TypeError, ValueError, requests.RequestException) as exc:
        LOGGER.warning("Could not persist article failure for %s: %s", canonical, exc)
    return None
