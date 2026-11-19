# ProChal News

Streamlit 기반 뉴스 미니게임 프로젝트. 게임 1~5는 뉴스 기사와 AI 요약·일치율 분석을 사용한다.

## 실행

```bash
python -m pip install -r requirements.txt
streamlit run news.py
```

Python 3.11을 CI 테스트 환경으로 사용한다. 실행 시 비공개 Streamlit secrets,
Google Sheets와 Apps Script 거래 서버, Gemini API 설정이 필요하다.
설정 방법은 [거래 서버 배포 문서](docs/transaction-ledger.md)와
[배지 배포 문서](docs/badge-awards-deployment.md)를 참고한다.
`.streamlit/secrets.toml`, API 키, 비밀번호, 거래 토큰은 저장소에 추가하지 않는다.

## 코드/파일 위치

| 경로 | 소유하는 기능 |
| --- | --- |
| `news.py` | Streamlit 앱 진입점, 페이지 라우팅, 오디오 및 알림 초기화 |
| `games/game1/` | 게임 1 규칙, 예측·결과용 독립 HTML/CSS/JS 화면 |
| `games/game2.py`, `game3.py`, `game4.py`, `game5.py` | 나머지 게임별 규칙과 상태 |
| `games/game4_ui/` | 게임 4의 구간 선택 컴포넌트, 결과·튜토리얼 CSS |
| `games/shared/` | 공통 베팅, 연속 룰렛, 기사 읽기, 뉴스 흐름, 분석 로딩과 결과 |
| `views/` | 로그인, 메인 화면, 랭킹, 배지와 은행 |
| `views/bank/` | 대출·상환 등의 은행 화면 |
| `modules/` | 기사 수집/전처리, AI, 시트 접근, 거래, 배지와 공통 계정 로직 |
| `apps_script/` | Google Apps Script 거래 게이트웨이와 배지 서버 로직 |
| `assets/` | 정적 이미지/영상 리소스(기능별 하위 폴더 포함) |
| `sounds/` | 음원, Streamlit 상위 창의 오디오 제어 코드 |
| `tests/` | Python 회귀 테스트 및 Node 기반 브라우저 로직 테스트 |
| `docs/` | 화면 구조, 거래 원장, 장애 복구, 배포 설명 |
| `.github/workflows/` | 자동 테스트 및 관련 작업 |

## 구조 원칙

- 공유 화면/로직은 `games/shared/`에서 구현하고, 게임별 승패 규칙과 진행 상태는 각 게임 파일에서 관리한다.
- 공통 룰렛/기사 읽기 기능은 게임 1~4가 사용하며, 게임 5는 여러 기사를 비교하는 고유 UI를 유지한다.
- 프런트엔드 컴포넌트의 HTML·CSS·JS는 가능한 한 같은 디렉터리에 두고, Streamlit 모듈에서 `Path(__file__)`를 기준으로 참조한다.
- `assets/`의 위치는 게임별 임의 이동보다 안정적인 참조를 우선한다.
- 코인·대출·이자·연승의 쓰기는 `modules/transactions.py`와 배포된 `apps_script/` 게이트웨이를 사용한다. 구글 시트에 직접 계정 잔액을 갱신하지 않는다.
- `news.py`는 앱 진입점이므로 프로젝트 루트에 둔다. 이미 외부에서 참조하는 Python 모듈을 단순한 폴더 대칭성 때문에 옮기지 않는다.

## 테스트

```bash
python -m unittest discover -s tests -v
node --test tests/test_transaction_gateway.cjs tests/test_game1_result_parent_audio.cjs tests/test_loading_feedback.cjs tests/test_similarity_video_audio.cjs tests/test_game4_reveal_animation.cjs
```

전체 GitHub Actions 테스트 정의는 [`.github/workflows/tests.yml`](.github/workflows/tests.yml)에 있다.
변경 뒤에는 해당 워크플로와 실제 모바일 화면을 모두 확인한다.

## 배포 관련 주의

GitHub의 `apps_script/Code.gs`, `apps_script/Badges.gs` 수정은 **배포된 Apps Script 웹 앱에 자동 반영되지 않는다**.
서버 규칙 변경 시 Google Apps Script의 새 버전 배포가 필요하다.
상세 절차는 [거래 원장 문서](docs/transaction-ledger.md)에 있다.
