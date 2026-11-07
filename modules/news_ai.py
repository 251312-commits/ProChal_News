import streamlit as st
from newspaper import Article
import random
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


@st.cache_resource
def load_ai_model():
    # Import heavyweight inference libraries only when a score is requested.
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(RERANKER_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(RERANKER_NAME)
    model.eval()
    return tokenizer, model


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
    article_obj = Article(url, language='ko')
    article_obj.download()
    article_obj.parse()
    domain = urlparse(url).netloc
    title = get_clean_title(article_obj, domain)
    clean_article = clean_common_text(article_obj.text)
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
    """Return the game score and the intermediate values from the same model call."""
    tokenizer, model = load_ai_model()
    import torch

    inputs = tokenizer(summary_text, title, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits.squeeze(-1)
        normalized = torch.sigmoid(logits).item()
    hundredths = score_hundredths(normalized)
    return {
        "model_name": RERANKER_NAME,
        "score": hundredths / 100,
        "score_hundredths": hundredths,
        "token_count": int(inputs["attention_mask"].sum().item()),
        "logit": logits.item(),
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
