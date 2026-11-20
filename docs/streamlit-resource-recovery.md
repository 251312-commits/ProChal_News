# Streamlit Cloud 오류 및 메모리 복구

## `Error running app`의 원인 구분

이 문구만으로 원인을 확정할 수 없다. Streamlit Community Cloud에서 앱의
**Manage app → Logs**를 열어 실제 오류를 먼저 확인한다.

- `Killed`, `OOM`, `out of memory`, `resource limits`: 메모리 부족 가능성이 높다.
- `ModuleNotFoundError`, `ImportError`, `Error installing requirements`: 패키지 설치 또는 Python 버전 문제.
- `KeyError`, `StreamlitSecretNotFoundError`: 비공개 Secrets 설정 확인.
- Google Sheets 연결 오류나 Gemini API `429`: 해당 외부 서비스와 계정/쿼터 문제.
- 로그 없이 앱 프로세스가 중단되면 먼저 **Reboot**하여 메모리를 초기화한다.

로그에는 계정 키, 비밀번호, 거래 토큰을 공개하지 않는다.

## 메모리 절감 변경

- 기존 `BAAI/bge-reranker-v2-m3` PyTorch FP32 체크포인트는 가중치 파일만 약 2.27GB이다.
  Streamlit Community Cloud의 최대 메모리(약 2.7GB) 안에서 실행하기 어렵다.
- `modules/news_ai.py`는 같은 BGE 모델의 **ONNX INT8 변환본**을 사용한다.
  Hugging Face `onnx-community/bge-reranker-v2-m3-ONNX`의
  `onnx/model_int8.onnx`는 약 571MB이다.
- 모델 리비전을 고정하여 재배포 시 예고 없는 모델 교체를 막는다.
- CPU 스레드를 2개로 제한하고, Streamlit에서 첫 유사도 분석 시에만
  모델을 다운로드·로딩한다. 그 뒤에는 `st.cache_resource`로 재사용한다.
- `torch`와 `transformers` 설치를 제거했다. 로그인에 쓰이지 않는
  `newspaper3k`와 Gemini SDK 임포트도 호출 시점으로 미뤘다.

**중요:** INT8 양자화로 기존 FP32 모델과 관련성 점수(특히 소수점 두 자리)가
미세하게 달라질 수 있다. 로짓 → sigmoid → 0~100점 변환, 게임 배율,
승패 정산 방식은 그대로지만, 모델의 수치가 완전히 동일한 것은 아니다.
게임 5 전용 파일은 수정하지 않았지만 공통 점수 엔진은 모든 게임에서 사용한다.
공정성 검토에는 동일한 기사·제목 쌍을 원본 모델과 양자화 모델로 비교하는
별도 벤치마크가 필요하다.

첫 유사도 분석은 약 571MB 모델을 외부에서 다운로드해야 하므로 네트워크
상태에 따라 느릴 수 있다. 다운로드가 실패하면 앱 전체가 무한정 멈추는 대신
명시적인 모델 오류를 반환하도록 했다.

## 검증 및 배포

1. GitHub PR의 `Unit tests`와 `production-import-smoke` 결과를 확인한다.
2. 병합 후 Streamlit Community Cloud에서 **Reboot**한다.
3. 로그인 → 기사 선택 → 기사 읽기 → 유사도 계산 → 결과 확인을 진행한다.
4. 게임 1~4뿐 아니라 게임 5도 공통 점수 엔진을 사용하므로 대표 라운드를 점검한다.
5. 여전히 `Error running app`이면 **Manage app → Logs**의 마지막 traceback과
   오류 직전 화면을 확인한다. 오류 메시지를 바탕으로 그 원인만 수정한다.

원본 fp32와 INT8 모델의 점수 비교가 필요하면 별도 벤치마크를 큰 메모리 환경에서
수행해야 한다. 자동 테스트는 모델 파일을 실제로 다운로드하거나 정확도를
실측하지 않으며, API/파일 경로/서버 임포트 및 점수 포맷을 검증한다.
