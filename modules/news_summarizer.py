
import asyncio
import time

import streamlit as st
from google import genai


# ==========================================
# Gemini API 설정
# ==========================================

API_KEY = st.secrets["GEMINI_API_KEY"]

client = genai.Client(api_key=API_KEY)

MODEL_NAME = "gemini-3.5-flash-lite"


# ==========================================
# 요청 큐 설정
# ==========================================

MAX_QUEUE_SIZE = 200
REQUEST_INTERVAL = 6.0
MAX_RETRIES = 3

request_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

worker_task = None
last_request_time = 0
closing = False


# ==========================================
# Gemini 뉴스 요약 함수
# ==========================================

async def _generate_summary(news_text):

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

    response = await asyncio.to_thread(
        client.models.generate_content,
        model=MODEL_NAME,
        contents=prompt
    )

    return response.text.strip()


# ==========================================
# 요청 처리 Worker
# ==========================================

async def _worker():

    global last_request_time

    while True:

        request = await request_queue.get()

        try:

            # 종료 신호 확인
            if request is None:
                break

            news_text, future = request

            # 이미 취소된 요청이면 건너뛰기
            if future.cancelled():
                continue

            # Gemini API 요청 및 재시도
            for attempt in range(MAX_RETRIES):

                try:

                    # 요청 간격 유지
                    elapsed = time.monotonic() - last_request_time
                    wait_time = REQUEST_INTERVAL - elapsed

                    if wait_time > 0:
                        await asyncio.sleep(wait_time)

                    last_request_time = time.monotonic()

                    summary = await _generate_summary(news_text)

                    if not future.done():
                        future.set_result(summary)

                    break

                except Exception as e:

                    error_message = str(e)

                    # 재시도 가능한 오류 확인
                    retryable = (
                        "429" in error_message
                        or "500" in error_message
                        or "502" in error_message
                        or "503" in error_message
                        or "504" in error_message
                        or "RESOURCE_EXHAUSTED" in error_message
                    )

                    if retryable and attempt < MAX_RETRIES - 1:

                        wait_time = 2 ** attempt

                        await asyncio.sleep(wait_time)

                    else:

                        if not future.done():
                            future.set_exception(e)

                        break

        finally:
            request_queue.task_done()


# ==========================================
# 외부에서 사용하는 뉴스 요약 함수
# ==========================================

async def summarize_news(news_text: str) -> str:

    global worker_task

    if closing:
        raise RuntimeError("뉴스 요약 서비스가 종료되었습니다.")

    if not isinstance(news_text, str) or not news_text.strip():
        raise ValueError("뉴스 전문이 비어 있습니다.")

    # Worker가 실행 중이지 않으면 시작
    if worker_task is None or worker_task.done():
        worker_task = asyncio.create_task(_worker())

    # 결과를 전달받을 Future 생성
    future = asyncio.get_running_loop().create_future()

    # 요청을 큐에 추가
    await request_queue.put((news_text, future))

    # 요약 결과가 반환될 때까지 대기
    return await future


# ==========================================
# 서비스 종료 함수
# ==========================================

async def close_summarizer():

    global closing
    global worker_task

    if worker_task is None:
        return

    if closing:
        return

    closing = True

    # 대기 중인 요청이 모두 처리될 때까지 기다림
    await request_queue.join()

    # Worker 종료 신호 전달
    await request_queue.put(None)

    # Worker 종료 대기
    await worker_task

    worker_task = None

    # Gemini 클라이언트 종료
    client.close()
