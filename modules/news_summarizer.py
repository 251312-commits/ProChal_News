"""Rate-limited, loop-independent Gemini news summarization service."""

import asyncio
from concurrent.futures import Future
import os
import queue
import random
import threading
import time

import streamlit as st
from google import genai
from google.genai import types


API_KEY = st.secrets["GEMINI_API_KEY"]
MODEL_NAME = "gemini-3.5-flash-lite"

MAX_QUEUE_SIZE = int(os.getenv("GEMINI_MAX_QUEUE_SIZE", "200"))
REQUEST_INTERVAL = float(os.getenv("GEMINI_REQUEST_INTERVAL", "6"))
REQUEST_TIMEOUT = float(os.getenv("GEMINI_REQUEST_TIMEOUT", "90"))
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
RETRY_BASE_DELAY = float(os.getenv("GEMINI_RETRY_BASE_DELAY", "2"))
RETRY_MAX_DELAY = float(os.getenv("GEMINI_RETRY_MAX_DELAY", "30"))


def _new_client():
    return genai.Client(
        api_key=API_KEY,
        http_options=types.HttpOptions(timeout=int(REQUEST_TIMEOUT * 1000)),
    )


class _SummaryService:
    """Owns one queue and worker thread, independent of caller event loops."""

    def __init__(self):
        self._queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
        self._thread = None
        self._state_lock = threading.Lock()
        self._last_request_time = 0.0
        self._client = None

    def _ensure_started(self):
        with self._state_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._client = _new_client()
            self._thread = threading.Thread(
                target=self._run,
                name="gemini-summary-worker",
                daemon=True,
            )
            self._thread.start()

    def submit(self, news_text: str) -> Future:
        self._ensure_started()
        result = Future()
        try:
            self._queue.put_nowait((news_text, result))
        except queue.Full as exc:
            raise RuntimeError(
                "뉴스 요약 요청이 많습니다. 잠시 후 다시 시도해 주세요."
            ) from exc
        return result

    def _run(self):
        while True:
            request = self._queue.get()
            try:
                if request is None:
                    return
                news_text, result = request
                if result.cancelled():
                    continue
                self._process(news_text, result)
            finally:
                self._queue.task_done()

    def _process(self, news_text: str, result: Future):
        for attempt in range(MAX_RETRIES):
            try:
                self._wait_for_rate_limit()
                summary = _generate_summary(self._client, news_text)
                if not result.cancelled():
                    result.set_result(summary)
                return
            except Exception as exc:
                if _is_retryable(exc) and attempt < MAX_RETRIES - 1:
                    delay = min(
                        RETRY_MAX_DELAY,
                        RETRY_BASE_DELAY * (2**attempt) + random.uniform(0, 0.5),
                    )
                    time.sleep(delay)
                    continue
                if not result.cancelled():
                    result.set_exception(exc)
                return

    def _wait_for_rate_limit(self):
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < REQUEST_INTERVAL:
            time.sleep(REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.monotonic()

    def close(self):
        with self._state_lock:
            thread = self._thread
            if thread is None or not thread.is_alive():
                return
            self._queue.put(None)
        thread.join(timeout=REQUEST_TIMEOUT)
        if thread.is_alive():
            raise TimeoutError("뉴스 요약 작업자가 종료되지 않았습니다.")
        if self._client is not None:
            self._client.close()
        with self._state_lock:
            self._thread = None
            self._client = None


def _generate_summary(client, news_text: str) -> str:
    prompt = f"""
다음 뉴스 전문을 읽고 핵심 내용을 한국어로 요약하시오.

조건:
1. 요약은 1~3문장으로 작성할 것.
2. 뉴스의 핵심 정보와 주요 내용을 유지할 것.
3. 원문에 없는 내용을 임의로 추가하지 말 것.
4. 제목, 번호, 글머리 기호, Markdown 없이 순수 문장으로 작성할 것.

뉴스 전문:
{news_text}
"""
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
    )
    return response.text.strip()


def _is_retryable(error: Exception) -> bool:
    message = str(error).upper()
    return any(
        marker in message
        for marker in ("429", "500", "502", "503", "504", "RESOURCE_EXHAUSTED")
    )


_service = _SummaryService()


async def summarize_news(news_text: str) -> str:
    if not isinstance(news_text, str) or not news_text.strip():
        raise ValueError("뉴스 전문이 비어 있습니다.")

    result = _service.submit(news_text)
    wrapped_result = asyncio.wrap_future(result)
    try:
        return await asyncio.wait_for(wrapped_result, timeout=REQUEST_TIMEOUT)
    except asyncio.TimeoutError as exc:
        result.cancel()
        raise TimeoutError(
            f"뉴스 요약 요청이 {REQUEST_TIMEOUT:.0f}초 안에 완료되지 않았습니다."
        ) from exc


async def close_summarizer():
    await asyncio.to_thread(_service.close)
