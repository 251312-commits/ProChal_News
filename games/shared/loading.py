"""Reusable similarity-analysis loading display."""
from contextlib import contextmanager
from pathlib import Path
import streamlit as st


# Shared animated waiting screen for title-to-summary similarity analysis.
_SIMILARITY_LOADING_HTML = """
<div id="pc-sim-load" role="status" aria-live="polite"
     aria-label="뉴스 제목과 본문 요약의 유사도를 분석 중입니다">
  <div class="pc-sim-screen">
    <div class="pc-sim-chrome" aria-hidden="true">
      <span>NEWS ANALYSIS <span class="pc-sim-slashes">///</span></span>
      <span class="pc-sim-controls">− □ ×</span>
    </div>
    <div class="pc-sim-heading">
      <div class="pc-sim-folder" aria-hidden="true"></div>
      <h2 class="pc-sim-title">유사도 계산 중<span class="pc-sim-dots">...</span></h2>
      <p class="pc-sim-subtitle">뉴스 제목과 본문 요약을 비교하고 있습니다.</p>
    </div>
    <div class="pc-sim-compare" aria-hidden="true">
      <div class="pc-sim-paper pc-sim-paper-left">
        <span class="pc-sim-tape">기사 제목</span>
        <div class="pc-sim-rule"></div>
        <div class="pc-sim-photo"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
      </div>
      <div class="pc-sim-paper pc-sim-paper-right">
        <span class="pc-sim-tape">본문 요약</span>
        <div class="pc-sim-rule"></div>
        <div class="pc-sim-photo"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
      </div>
      <div class="pc-sim-rect"></div>
      <div class="pc-sim-beam"></div>
    </div>
    <div class="pc-sim-panel" aria-hidden="true">
      <div class="pc-sim-panel-title">분석 항목</div>
      <div class="pc-sim-panel-body">
        <div class="pc-sim-venn">
          <div class="pc-sim-venn-shapes"></div>
          <div class="pc-sim-venn-label">내용 일치율 탐색...</div>
        </div>
        <ul class="pc-sim-list">
          <li><span class="pc-sim-checkbox"></span>기사 본문 분석</li>
          <li><span class="pc-sim-checkbox"></span>핵심 내용 요약</li>
          <li><span class="pc-sim-checkbox"></span>제목·요약문 비교</li>
          <li><span class="pc-sim-checkbox"></span>유사도 점수 산출</li>
        </ul>
      </div>
    </div>
    <div class="pc-sim-meter" aria-hidden="true">
      <span class="pc-sim-meter-fill"></span>
    </div>
    <div class="pc-sim-meter-caption" aria-hidden="true">ANALYZING ···</div>
    <div class="pc-sim-stacks pc-sim-stacks-left" aria-hidden="true"></div>
    <div class="pc-sim-stacks pc-sim-stacks-right" aria-hidden="true"></div>
  </div>
</div>
"""


@contextmanager
def similarity_analysis_loading():
    """Show a mobile-friendly neon loader and clear it after work or errors.

    The moving bar is intentionally indeterminate: model inference does not
    report real percentage progress.
    """
    placeholder = st.empty()
    css = Path(__file__).with_name("similarity_loading.css").read_text(encoding="utf-8")
    placeholder.markdown(
        f"<style>{css}</style>{_SIMILARITY_LOADING_HTML}",
        unsafe_allow_html=True,
    )
    try:
        yield
    finally:
        placeholder.empty()
