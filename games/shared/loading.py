"""Reusable similarity-analysis loading display."""
from contextlib import contextmanager
from html import escape
import json
from pathlib import Path
from random import choice

import streamlit as st
import streamlit.components.v1 as components

_VIDEO_SOUND_JS = Path(__file__).with_name("similarity_video_controls.js").read_text(encoding="utf-8")


# Video clips are stored as regular static assets, not inline Base64. Keep
# the original newspaper art as a fallback if clips have not been installed.
_VIDEO_DIRECTORY = Path(__file__).resolve().parents[2] / "assets" / "similarity_clips"
_VIDEO_FILENAMES = ("Video1.mp4", "Video2.mp4", "Video3.mp4")
_VIDEO_ASPECTS = {"Video1.mp4": "4 / 3", "Video2.mp4": "4 / 3", "Video3.mp4": "16 / 9"}
_PUBLIC_VIDEO_BASE = (
    "https://raw.githubusercontent.com/251312-commits/"
    "ProChal_News/main/assets/similarity_clips/"
)


def _similarity_video_markup() -> str:
    """Play every available clip in sequence during similarity analysis.

    A pair of video elements lets the next asset preload while the current one
    plays. The parent browser soundtrack controller owns volume/mute and BGM
    ducking; no independent video sound toggle is rendered.
    """
    available = [name for name in _VIDEO_FILENAMES if (_VIDEO_DIRECTORY / name).is_file()]
    if not available:
        return ""  # Keep the existing newspaper animation.

    first = choice(available)
    start = available.index(first)
    ordered = available[start:] + available[:start]
    playlist = []
    for name in ordered:
        stat = (_VIDEO_DIRECTORY / name).stat()
        version = f"{stat.st_mtime_ns:x}-{stat.st_size:x}"
        playlist.append({
            "src": f"{_PUBLIC_VIDEO_BASE}{name}?v={version}",
            "aspect": _VIDEO_ASPECTS[name],
        })
    playlist_attr = escape(json.dumps(playlist), quote=True)
    first_src = escape(playlist[0]["src"], quote=True)
    return f"""
      <div class="pc-sim-video-frame" style="--pc-video-aspect:{playlist[0]['aspect']}"
           data-playlist="{playlist_attr}">
        <div class="pc-sim-video-banner" aria-hidden="true">
          <span>PROCHAL TV</span><span>ADVERTISEMENT / ANALYZING</span>
        </div>
        <div class="pc-sim-video-viewport">
          <video class="pc-sim-video is-active" autoplay playsinline
                 preload="auto" src="{first_src}"
                 aria-label="유사도 분석 중 재생되는 짧은 광고 영상"></video>
          <video class="pc-sim-video" playsinline preload="auto"
                 aria-hidden="true"></video>
        </div>
        <div class="pc-sim-video-note">로딩 중 영상 방송</div>
      </div>
    """


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
    <div class="pc-sim-compare" aria-label="뉴스 자료와 짧은 광고 영상">
      <div class="pc-sim-paper pc-sim-paper-left" aria-hidden="true">
        <span class="pc-sim-tape">기사 제목</span>
        <div class="pc-sim-rule"></div>
        <div class="pc-sim-photo"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
      </div>
      <div class="pc-sim-paper pc-sim-paper-right" aria-hidden="true">
        <span class="pc-sim-tape">본문 요약</span>
        <div class="pc-sim-rule"></div>
        <div class="pc-sim-photo"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
        <div class="pc-sim-rule"></div><div class="pc-sim-rule"></div>
      </div>
      <div class="pc-sim-rect"></div>
      <div class="pc-sim-beam" aria-hidden="true"></div>
      <!-- PC_SIM_VIDEO_SLOT -->
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
    video = _similarity_video_markup()
    markup = _SIMILARITY_LOADING_HTML.replace("<!-- PC_SIM_VIDEO_SLOT -->", video)
    # Dynamic video markup includes blank lines and nested indentation.
    # Markdown can interpret it as a fenced/indented code block and print
    # literal HTML tags. st.html bypasses the Markdown parser entirely.
    placeholder.html(f"<style>{css}</style>{markup}")
    if video:
        # A tiny component installs the parent-window playlist/sound bridge.
        # It is persistent across Streamlit reruns and unmounts cleanly.
        components.html(f"<script>{_VIDEO_SOUND_JS}</script>", height=0, width=0)
    try:
        yield
    finally:
        placeholder.empty()
