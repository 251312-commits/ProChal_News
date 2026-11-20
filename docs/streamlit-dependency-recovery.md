# 2026-11-20 Streamlit Cloud 로그인 전 실행 실패

## 로그에서 확인된 직접 원인

`news.py`가 로그인 화면까지 로드되지 않은 것은 AI 추론 때문이 아니다.
Streamlit Community Cloud의 배포 로그에서 다음 순서가 확인된다.

1. Python 3.14.10 환경에서 `uv pip install` 시작.
2. `requirements.txt`의 `--extra-index-url https://download.pytorch.org/whl/cpu`로
   전체 패키지 탐색에서 PyTorch CPU 저장소가 우선됨.
3. 이 저장소의 `requests==2.28.1`이 먼저 발견되었고,
   `requests>=2.31,<3` 조건을 만족하지 못해 `uv` 의존성 해결 실패.
4. Streamlit Cloud가 표준 `pip` 설치로 넘어갔지만, 재설치 도중
   앱 재실행과 `pyarrow` 26↔24 교체가 겹쳤다. 이때
   `KeyError: modules.news_preprocessing`, `RuntimeError: module is None`,
   `KeyError: sounds.bgm` 등이 반복됨.
5. 결국 `503` 헬스체크 오류와 `Error running app` 표시.

로그에는 첫 유사도 계산이나 모델 가중치 로딩 시도가 없었다.
**메모리 부족이 이 시작 오류의 직접 원인이라는 증거는 없다.**

## 이번 수정

- `requirements.txt`에서 글로벌 PyTorch CPU 추가 저장소 지시어 제거.
- 루트 `uv.toml`의 `[pip] torch-backend = "cpu"`로 **torch에만**
  CPU 인덱스를 적용. `requests` 등 나머지 패키지는 PyPI에서 탐색.
- `pyarrow>=24,<25`로 핀하여 해당 환경에서 알려진 26.x 문제 및 반복 교체 방지.
- Python 3.14에서 실제 `uv` 의존성 해결, 패키지 설치, 앱의 로그인 진입을
  검증하는 GitHub Actions 작업 추가.

`BAAI/bge-reranker-v2-m3` 원본 모델·Torch/Transformers·유사도 점수 공식 및
게임 1~5의 계산·정산 코드는 변경하지 않았다. ONNX INT8로 모델을 교체하는
별도 PR은 병합하지 않았다.

## 배포 시 확인

1. 의존성 해결 PR의 GitHub Actions 통과 확인 및 병합.
2. Streamlit Community Cloud에서 **Manage app → Reboot** 실행.
3. 로그인 화면이 정상적으로 표시되는지 확인.
4. 유사도 분석 버튼까지 시험해 보기. **추론 시 메모리 부족 문제는
   시작 시점의 의존성 문제와 별개**로 발생할 수 있다.
5. 문제가 반복되면 **Manage app → Logs**의 새로운 traceback 확인.

Python 버전을 3.11 또는 3.12로 바꾸려는 경우, Streamlit 공식 정책상
기존 배포에서 설정만 수정할 수 없고 **앱 삭제 및 재배포**가 필요하다.
이때 기존 앱 URL, GitHub 경로, Secrets를 미리 백업해야 한다.
단순 재부팅은 Python 3.14를 바꾸지 않는다.

참고: [Streamlit Python 버전 변경](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/upgrade-python),
[uv PyTorch CPU 백엔드](https://docs.astral.sh/uv/guides/integration/pytorch/).
