import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from newspaper import Article
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import streamlit as st

UI_WORDS = {'광고', '본문', '전체재생', '동영상 고정', '동영상 고정 취소', '이미지 확대', '사진 확대', '기사본문'}

@st.cache_resource
def load_ai_model():
    """AI 모델을 지연 로딩(Lazy Loading) 및 캐싱합니다."""
    model_name = "BAAI/bge-reranker-v2-m3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

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

def is_ad_or_ui_line(line: str) -> bool:
    s = line.strip()
    if not s or s in UI_WORDS or s in {'[광고]', '(광고)', 'AD', 'Advertisement'}:
        return True
    if re.match(r'^(광고|AD)\s*[:\-\|\[\(]', s) or s.endswith('(광고)'):
        return True
    if '광고' in s and len(s) <= 20 and not re.search(r'[다요함음]\s*[\.\!\?]?$', s):
        return True
    return False

def remove_duplicate_and_ui_lines(text: str) -> str:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned_lines = [line for line in lines if not is_ad_or_ui_line(line)]
    return '\n\n'.join(list(dict.fromkeys(cleaned_lines)))

def clean_common_text(text: str) -> str:
    text = re.sub(r'【[^】]*】', '', text)
    text = re.sub(r'(사진|이미지)\s*확대[^\n]*', '', text)
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z2-9]{2,}', '', text)
    text = re.sub(r'\[[^\]]*(제공|DB|재판매|캡처|사진)[^\]]*\]', '', text)
    text = re.sub(r'무단\s*전재[^\n]*', '', text)
    return remove_duplicate_and_ui_lines(text)

def bring_article(url: str):
    article_obj = Article(url, language='ko')
    article_obj.download()
    article_obj.parse()
    domain = urlparse(url).netloc
    title = get_clean_title(article_obj, domain)
    clean_article = clean_common_text(article_obj.text)
    return title, clean_article

def summary(article):
    return article if article else "요약본 예시 문장입니다."

def similarity_check(summary_text, title):
    tokenizer, model = load_ai_model()
    inputs = tokenizer(summary_text, title, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits.squeeze(-1)
        score = torch.sigmoid(logits).item()
    return int(round(score * 100))
