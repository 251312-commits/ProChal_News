"""Temporary deployment diagnostics for identifying the Streamlit runtime."""

import os
import socket

import streamlit as st


def show_runtime_identity() -> None:
    """Display the current process identity when explicitly enabled."""
    enabled = os.getenv("SHOW_RUNTIME_DIAGNOSTICS", "")
    if not enabled:
        enabled = str(st.secrets.get("SHOW_RUNTIME_DIAGNOSTICS", ""))
    if enabled.lower() not in {"1", "true", "yes"}:
        return

    st.info(
        f"임시 실행 환경 진단 — PID: `{os.getpid()}` · "
        f"Host: `{socket.gethostname()}`"
    )
