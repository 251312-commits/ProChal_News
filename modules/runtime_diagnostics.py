"""Temporary deployment diagnostics for identifying the Streamlit runtime."""

import os
import socket

import streamlit as st


def show_runtime_identity() -> None:
    """Display the current process identity when explicitly enabled."""
    if os.getenv("SHOW_RUNTIME_DIAGNOSTICS", "").lower() not in {"1", "true", "yes"}:
        return

    st.sidebar.caption("임시 실행 환경 진단")
    st.sidebar.write("PID:", os.getpid())
    st.sidebar.write("Host:", socket.gethostname())
