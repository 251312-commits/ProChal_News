import streamlit as st
import random
import math
import logging
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from modules.news_preprocessing import (
    clean_common_text,
    is_ad_or_ui_line,
    remove_duplicate_and_ui_lines,
)
from modules.news_summarizer import summarize_news
from modules.score_math import score_hundredths

# ==========================================
# 1. 효율성 극대화: AI 모델 캐싱 (최초 1회만 로드)
# ==========================================
RERANKER_NAME = "BAAI/bge-reranker-v2-m3"
# Pinned INT8 export of the same reranker. Its on-disk weights are ~571 MB,
# versus 2.27 GB for the float32 PyTorch original.
RERANKER_ONNX_REPO = "onnx-community/bge-reranker-v2-m3-ONNX"
RERANKER_ONNX_REVISION = "6f5ff65298512715a1e669753bc754d2bc8f367b"
RERANKER_ONNX_FILE = "onnx/model_int8.onnx"
_LOG = logging.getLogger(__name__)


@st.cache_resource(show_spinner="유사도 모델 준비 중…")
def load_ai_model():
    """Download and initialize the CPU-efficient reranker once per process."""
    # Heavy inference libraries and remote model downloads are deferred until
    # the first score request, so login and ordinary navigation remain light.
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer
    import onnxruntime as ort

    try:
        model_path = hf_hub_download(
            repo_id=RERANKER_ONNX_REPO,
            filename=RERANKER_ONNX_FILE,
            revision=RERANKER_ONNX_REVISION,
        )
        tokenizer_path = hf_hub_download(
            repo_id=RERANKER_ONNX_REPO,
            filename="tokenizer.json",
            revision=RERANKER_ONNX_REVISION,
        )
        tokenizer = Tokenizer.from_file(tokenizer_path)
        tokenizer.enable_truncation(max_length=512, strategy="longest_first")

        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        options.enable_mem_pattern = False
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
        session = ort.InferenceSession(
            model_path, sess_options=options, providers=["CPUExecutionProvider"],
        )
        _LOG.info("ONNX INT8 reranker ready: %s", RERANKER_ONNX_REVISION[:10])
        return tokenizer, session
    except Exception as exc:
        _LOG.exception("Reranker could not be initialized")
        raise RuntimeError(
            "유사도 모델을 불러오지 못했습니다. 서버 로그에서 모델 다운로드와 메모리를 확인하세요."
        ) from exc


def _onnx_inputs(encoding, session, np):
    """Prepare one encoded pair, respecting a static ONNX batch if required."""
    inputs = session.get_inputs()
    if not inputs:
        raise RuntimeError("유사도 모델의 입력 정보가 없습니다.")
    declared_batch = inputs[0].shape[0]
    batch_size = (
        declared_batch if isinstance(declared_batch, int) and declared_batch > 0 else 1
    )
    ids = list(encoding.ids)
    mask = list(encoding.attention_mask)
    types = list(encoding.type_ids)
    declared_length = inputs[0].shape[1] if len(inputs[0].shape) >= 2 else None
    if isinstance(declared_length, int) and declared_length > 0:
        if len(ids) > declared_length:
            raise RuntimeError("유사도 모델의 입력 길이를 초과했습니다.")
        n_pad = declared_length - len(ids)
        ids += [1] * n_pad  # XLM-R <pad>
        mask += [0] * n_pad
        types += [0] * n_pad

    data = {
        "input_ids": ids, "attention_mask": mask, "token_type_ids": types,
    }
    feed = {}
    for field in inputs:
        if field.name not in data:
            raise RuntimeError(f"지원하지 않는 유사도 모델 입력: {field.name}")
        feed[field.name] = np.asarray([data[field.name]] * batch_size, dtype=np.int64)
    return feed


# ==========================================
# 2. 제공해주신 기사 전처리 함수들
# ==========================================
def get_clean_title(article_obj, domain: str) -> str:
    title = article_obj.title.strip()
    if 'kbs.co.kr' in domain or title in ['KBS', 'KBS 뉴스', 'KBS뉴스', 'KBS 기사', '']:
        og_title = article_obj.meta_data.get('og', {}).get('title')
        if og_title:
            title = og_title
        elif article_obj.html:
            soup = BeautifulSoup(article_obj.html, 'html.parser')
            og_meta = soup.find('meta', property='og:title')
            if og_meta and og_meta.get('content'):
                title = og_meta['content']
            else:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text()

    suffixes = [' | KBS 뉴스', ' | KBS', ' - KBS뉴스', ' - KBS', ' | 연합뉴스', ' | 한겨레', ' - MBC뉴스']
    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
    return title

def _article_image_url(article_obj, url: str) -> str:
    metadata = article_obj.meta_data
    og = metadata.get('og') if isinstance(metadata, dict) else None
    image = og.get('image') if isinstance(og, dict) else None
    # newspaper3k nests the original URL under 'identifier' when og:image has subproperties.
    if isinstance(image, dict):
        candidates = (image.get('secure_url'), image.get('identifier'), image.get('url'))
    else:
        candidates = (image,)
    for candidate in (*candidates, article_obj.top_image):
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        try:
            image_url = urljoin(url, candidate.strip())
            parsed = urlparse(image_url)
            if parsed.scheme in ('http', 'https') and parsed.hostname:
                return image_url
        except ValueError:
            continue
    return ''


def bring_article(url: str, *, include_image=False):
    from newspaper import Article

    article_obj = Article(url, language='ko')
    article_obj.download()
    article_obj.parse()
    domain = urlparse(url).netloc
    title = get_clean_title(article_obj, domain)
    clean_article = clean_common_text(article_obj.text)
    # A blank/blocked publisher page must not be accepted as a playable article.
    if not str(title or "").strip() or len("".join(str(clean_article or "").split())) < 40:
        raise ValueError("기사 제목 또는 본문을 정상적으로 추출하지 못했습니다.")
    if include_image:
        return title, clean_article, _article_image_url(article_obj, url)
    return title, clean_article
    
async def summary(article):
    try:
        summary = await summarize_news(article)
        return summary

    except Exception as e:
        print(f"뉴스 이벤트 실행 실패: {e}")
        return None

def similarity_check(summary_text, title):
    """Score the title and summary using the cached ONNX INT8 reranker."""
    import numpy as np

    tokenizer, session = load_ai_model()
    encoding = tokenizer.encode(summary_text, title, add_special_tokens=True)
    feed = _onnx_inputs(encoding, session, np)
    output = session.run(None, feed)[0]
    logit = float(np.asarray(output).reshape(-1)[0])
    if not math.isfinite(logit):
        raise RuntimeError("유사도 모델에서 유효하지 않은 결과를 반환했습니다.")

    # Numerically stable sigmoid; the same 0-100 conversion as the original.
    if logit >= 0:
        normalized = 1 / (1 + math.exp(-logit))
    else:
        ex = math.exp(logit)
        normalized = ex / (1 + ex)
    hundredths = score_hundredths(normalized)
    return {
        "model_name": RERANKER_NAME + " (ONNX INT8)",
        "score": hundredths / 100,
        "score_hundredths": hundredths,
        "token_count": int(sum(encoding.attention_mask)),
        "logit": logit,
        "normalized": normalized,
    }


# ==========================================
# 선택 횟수 기반 최저 뉴스 3개 무작위 추출 알고리즘
# ==========================================
def pick_lowest_count_news(news_list, limit=3):
    if limit < 1:
        return []
    if len(news_list) <= limit:
        return news_list

    sorted_counts = sorted(list(set(item['count'] for item in news_list)))
    
    selected = []
    for count_val in sorted_counts:
        tier_items = [item for item in news_list if item['count'] == count_val]
        needed = limit - len(selected)
        
        if len(tier_items) <= needed:
            selected.extend(tier_items)
        else:
            selected.extend(random.sample(tier_items, needed))
            
        if len(selected) == limit:
            break
            
    return selected


def pick_3_lowest_count_news(news_list):
    return pick_lowest_count_news(news_list, 3)


def pick_5_lowest_count_news(news_list):
    return pick_lowest_count_news(news_list, 5)
