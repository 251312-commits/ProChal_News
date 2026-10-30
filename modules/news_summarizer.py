
import os
import re
import asyncio

from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types


# ==========================================
# 1. 기본 설정
# ==========================================

load_dotenv()

MODEL_NAME = "gemini-3.5-flash-lite"

# API 요청 사이의 최소 간격 (초)
# 실제 AI Studio 프로젝트의 RPM에 맞춰 조정
REQUEST_INTERVAL = 6.0

# 최대 대기 요청 수
MAX_QUEUE_SIZE = 200

# API 요청 최대 재시도 횟수
MAX_RETRIES = 3


# ==========================================
# 2. 요청 데이터 구조
# ==========================================

@dataclass
class SummaryRequest:
    news_text: str
    future: asyncio.Future


# ==========================================
# 3. 뉴스 요약 관리자
# ==========================================

class NewsSummarizer:

    def __init__(self):

        self.api_key = os.getenv("GEMINI_API_KEY")

        self.client = None
        self.aio_client = None

        self.queue = asyncio.Queue(
            maxsize=MAX_QUEUE_SIZE
        )

        self.worker_task = None

        self.running = False
        self.closing = False

        self.last_request_time = 0.0

    # --------------------------------------
    # 작업자 시작
    # --------------------------------------

    async def start(self):

        if self.closing:
            raise RuntimeError("요약 관리자가 종료 중입니다.")

        if self.running:
            return

        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY가 설정되지 않았습니다."
            )

        self.client = genai.Client(
            api_key=self.api_key
        )

        self.aio_client = self.client.aio

        self.running = True

        self.worker_task = asyncio.create_task(
            self._worker()
        )

    # --------------------------------------
    # 외부 호출용 뉴스 요약 함수
    # --------------------------------------

    async def summarize(self, news_text: str) -> str:

        if not isinstance(news_text, str):
            raise TypeError("뉴스 전문은 문자열이어야 합니다.")

        if not news_text.strip():
            raise ValueError("뉴스 전문이 비어 있습니다.")

        if self.closing:
            raise RuntimeError("요약 관리자가 종료 중입니다.")

        if not self.running:
            await self.start()

        loop = asyncio.get_running_loop()

        # 요청 결과를 전달받을 Future 생성
        future = loop.create_future()

        request = SummaryRequest(
            news_text=news_text,
            future=future
        )

        # 대기열에 요청 추가
        # 대기열이 가득 차면 공간이 생길 때까지 대기
        await self.queue.put(request)

        # 요약이 완료될 때까지 대기
        return await future

    # --------------------------------------
    # 대기열 작업자
    # --------------------------------------

    async def _worker(self):

        while True:

            request = await self.queue.get()

            try:

                # 종료 신호 확인
                if request is None:
                    break

                # 이전 요청과의 간격 조절
                loop = asyncio.get_running_loop()

                elapsed = (
                    loop.time() - self.last_request_time
                )

                wait_time = REQUEST_INTERVAL - elapsed

                if wait_time > 0:
                    await asyncio.sleep(wait_time)

                self.last_request_time = loop.time()

                # Gemini API 호출
                result = await self._generate_summary(
                    request.news_text
                )

                # 요청한 곳에 결과 전달
                if not request.future.done():
                    request.future.set_result(result)

            except Exception as e:

                # 오류를 요청한 곳에 전달
                if (
                    request is not None
                    and not request.future.done()
                ):
                    request.future.set_exception(e)

            finally:

                # 작업 완료 처리
                self.queue.task_done()

    # --------------------------------------
    # 실제 Gemini API 요약 요청
    # --------------------------------------

    async def _generate_summary(self, news_text: str) -> str:

        prompt = f"""
다음 온라인 뉴스 전문을 읽고 핵심 내용을 한국어로 요약하라.

[요약 조건]
1. 반드시 1~3문장으로 작성한다.
2. 핵심 사건, 주요 인물 또는 기관, 중요한 결과를 포함한다.
3. 원문에 없는 사실을 추가하거나 추측하지 않는다.
4. 객관적이고 간결한 문장을 사용한다.
5. 문장 앞에 -, *, •, 숫자 등의 기호를 붙이지 않는다.
6. 제목이나 소제목을 작성하지 않는다.
7. 목록이나 마크다운 형식을 사용하지 않는다.
8. 별도의 설명 없이 순수한 요약 문장만 출력한다.

[뉴스 전문]
{news_text}
"""

        for attempt in range(MAX_RETRIES):

            try:

                response = await self.aio_client.models.generate_content(
                    model=MODEL_NAME,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=160
                    )
                )

                if not response.text:
                    raise RuntimeError(
                        "Gemini 요약 결과가 비어 있습니다."
                    )

                summary = response.text.strip()

                # 문장 앞의 목록 기호 제거
                summary = re.sub(
                    r"(?m)^\s*(?:[-*•]|\d+[.)])\s*",
                    "",
                    summary
                )

                # 마크다운 기호 제거
                summary = re.sub(
                    r"[*_`#]",
                    "",
                    summary
                )

                # 줄바꿈을 공백으로 통합
                summary = re.sub(
                    r"\s*\n\s*",
                    " ",
                    summary
                )

                return summary.strip()

            except Exception as e:

                error_text = str(e).upper()

                # 요청 한도 초과 및 일시적 서버 오류 확인
                retryable = (
                    "429" in error_text
                    or "RESOURCE_EXHAUSTED" in error_text
                    or any(
                        code in error_text
                        for code in ("500", "502", "503", "504")
                    )
                )

                if retryable and attempt < MAX_RETRIES - 1:

                    # 지수형 재시도 대기
                    await asyncio.sleep(
                        2 ** (attempt + 1)
                    )

                    continue

                raise

        raise RuntimeError("뉴스 요약에 실패했습니다.")

    # --------------------------------------
    # 프로그램 종료
    # --------------------------------------

    async def close(self):

        if not self.running or self.closing:
            return

        # 새로운 요청 차단
        self.closing = True

        # 기존 요청을 모두 처리할 때까지 대기
        await self.queue.join()

        # 작업자 종료 신호 전달
        await self.queue.put(None)

        await self.worker_task

        # API 클라이언트 자원 정리
        await self.aio_client.aclose()
        self.client.close()

        self.running = False


# ==========================================
# 4. 공통 요약 관리자 생성
# ==========================================

_summarizer = NewsSummarizer()


# ==========================================
# 5. 다른 모듈에서 사용할 함수
# ==========================================

async def summarize_news(news_text: str) -> str:

    return await _summarizer.summarize(news_text)


# ==========================================
# 6. 프로그램 종료용 함수
# ==========================================

async def close_summarizer():

    await _summarizer.close()
