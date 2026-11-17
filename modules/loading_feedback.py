"""Immediate loading feedback for Streamlit actions.

Call after rendering the page (and at the end of fragment dialogs). A fresh
run token clears the previous click's indicator after server work completes.
"""
import json
from pathlib import Path
from uuid import uuid4

import streamlit.components.v1 as components


_CLIENT_SCRIPT = Path(__file__).with_name("loading_feedback.js").read_text(encoding="utf-8")


def render_loading_feedback() -> None:
    """Set up one persistent browser event listener and finish this render."""
    token = json.dumps(uuid4().hex)
    components.html(
        "<!doctype html><html lang='ko'><body><script>\n"
        f"const pcRunToken = {token};\n{_CLIENT_SCRIPT}\n"
        "</script></body></html>",
        height=0,
        width=0,
    )
