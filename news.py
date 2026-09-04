import streamlit as st
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from newspaper import Article

# --- 페이지 설정 ---
st.set_page_config(page_title="기사 제목-본문 유사도 측정기", page_icon="📰", layout="centered")

st.title("📰 기사 제목 - 본문 유사도 측정기")
st.write("뉴스 URL을 입력하면 AI가 제목과 본문의 연관성(유사도)을 측정합니다.")

# --- AI 모델 로딩 (최초 1회만 실행되도록 캐싱) ---
@st.cache_resource
def load_model():
    model_name = "BAAI/bge-reranker-v2-m3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

with st.spinner("AI 모델을 로딩 중입니다... (최초 실행 시 시간이 걸릴 수 있습니다)"):
    tokenizer, model = load_model()

# --- 기사 수집 함수 ---
def bring_article(url):
    article_obj = Article(url, language='ko')
    article_obj.download()
    article_obj.parse()

    title = article_obj.title
    article = article_obj.text
    return title, article

# --- 유사도 계산 함수 ---
def similarity_check(article, title):
    inputs = tokenizer(
        article,
        title,
        padding=True,
        truncation=True,
        return_tensors="pt",
        max_length=512,
    )

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits.squeeze(-1)
        score = torch.sigmoid(logits).item()

    return round(score, 4)

# --- UI 입력 및 실행 ---
url = st.text_input("기사 URL을 입력해 주세요:", placeholder="https://news.naver.com/...")

if st.button("유사도 측정하기", type="primary", use_container_width=True):
    if not url.strip():
        st.warning("URL을 입력해 주세요!")
    else:
        with st.spinner("기사 본문을 불러오고 유사도를 계산하는 중입니다..."):
            try:
                title, article = bring_article(url)

                if not article.strip():
                    st.error("기사 본문을 가져올 수 없습니다. URL을 다시 확인해 주세요.")
                else:
                    similarity = similarity_check(article, title)
                    percentage = round(similarity * 100, 2)

                    st.markdown("---")
                    st.subheader("📌 기사 제목")
                    st.info(title)

                    # 점수 출력
                    st.metric(label="제목-본문 유사도 점수", value=f"{percentage}%", delta=f"Score: {similarity}")

                    # 점수에 따른 상태 메시지
                    if percentage >= 70:
                        st.success("✅ 제목과 본문의 연관성이 매우 높습니다.")
                    elif percentage >= 40:
                        st.warning("⚠️ 제목과 본문의 연관성이 보통 수준입니다.")
                    else:
                        st.error("🚨 낚시성 기사일 확률이 높습니다! (제목과 본문 불일치)")

                    # 본문 확인 접기/열기
                    with st.expander("📄 기사 본문 전체 보기"):
                        st.write(article)

            except Exception as e:
                st.error(f"기사를 처리하는 중 오류가 발생했습니다: {e}")
