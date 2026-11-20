# 게임 화면 구조

## 설계 원칙

- 공통 화면은 games/shared/에 둔다. 베팅, 뉴스 후보 선정, 룰렛, 기사 읽기, AI 분석 로딩에 각각 하나의 구현을 유지한다.
- 게임별 규칙과 정산은 games/game1/game1.py 및 games/game2.py ~ game5.py가 소유한다.
- 게임 1에만 필요한 소수점 두 자리 예측 화면과 튜토리얼은 games/game1/game1.py에 합쳤다.
- games/common.py는 제거하고 공통 기능을 games.shared의 각 모듈에서 직접 가져온다.
- 공통 HTML/CSS/JS 프론트엔드는 games/shared/news_slot/, games/shared/article_reader/에 모아 두며, assets/ 이미지 폴더는 프로젝트 루트에 유지한다.

## 재사용 API

| 공통 화면 | 모듈 및 함수 | 설정 |
|---|---|---|
| 베팅 | games.shared.betting.render_betting_ui | payout_multiplier(순수익 배율), state_key, min_bet |
| 코인 부족 모달 | games.shared.betting.check_user_coins_or_pop_bank | min_required |
| 뉴스 흐름 | games.shared.news_flow.get_game_news_selection | game_id, win_multiplier |
| 룰렛 | games.shared.roulette.render_news_slot | game_id, continuous_reel, allow_back, allow_direct_url |
| 기사 읽기 | games.shared.article_reader.render_article_reader | game_id, reward |
| 유사도 분석 로딩 | games.shared.loading.similarity_analysis_loading | with 문으로 사용 |

## 게임별 소유 영역

- game1: 공통 베팅·룰렛·기사 읽기·로딩 + 전용 숫자 예측·튜토리얼
- game2: 공통 베팅·룰렛·기사 읽기·로딩 + 전용 HIGH/LOW 예측
- game3: 공통 베팅·룰렛·기사 읽기·로딩 + 전용 홀짝 선택·50% 패배 손실
- game4: 공통 베팅·뉴스 선택·로딩 + 전용 구간 예측
- game5: 공통 베팅·로딩 + 전용 범위 선택

game1~4는 공통 룰렛에서 연속 회전 및 지원 언론사 기사 URL 직접 입력을 사용한다. game3은 뒤로가기를 숨겨 전용 진행 상태를 유지한다. game5는 별도 다중 기사 선택 UI를 유지한다.
각 화면은 게임별 상태 키를 사용하고, iframe에서 온 이벤트의 round_id를 검사한다. 대출금은 랭킹 점수에서 제외한다.

## 테스트
프로젝트 루트에서 python -m unittest discover -s tests -v 실행.

## 공통 모듈 추가 통합
- `games/common.py` 대신 `games.shared.betting`, `games.shared.news_flow` 등의 소유 모듈에서 UI 함수를 직접 가져온다.
- `games/betting_math.py`와 베팅 UI는 `games/shared/betting.py`에 통합했다.
- `games/result_reveal.py`, `games/score_stage.py`는 `games/shared/result.py`로 통합했다.
- 게임 5 튜토리얼은 게임 전용 파일 `games/game5.py`에 포함한다.

## game1 전용 리소스
- `games/game1/game1.py`: 게임 1 진행, 예측 UI 진입, 튜토리얼
- `games/game1/game1_tutorial.css`: 튜토리얼 스타일
- `games/game1/prediction_screen/`: 예측 화면 HTML·CSS·JavaScript
- 예측 화면 이미지는 기존 프로젝트 루트 `assets/` 폴더를 계속 사용한다.


## Game 4 전용 UI 파일 위치 (2026-11)

- `games/game4.py`: 게임 규칙, 점수 계산, 정산, 화면 이벤트 처리. 기존 import 경로를 유지한다.
- `games/game4_ui/picker/index.html`: 세 구간 선택과 결과 착지 애니메이션의 전용 HTML/CSS.
- `games/game4_ui/picker/picker.js`: 선택·공개 이벤트와 `round_id` 확인을 위한 브라우저 코드.
- `games/game4_ui/tutorial.css`: 게임 4 튜토리얼의 Streamlit 스타일.
- `games/game4_ui/result.css`: 게임 4 최종 결과 화면 스타일(이전 `game4_picker.css`).
- `assets/game4_guide/`: 튜토리얼 SVG 원본. 공용 이미지 폴더 구조를 유지한다.

게임 4의 `result.css`는 최종 결과 화면 전용이다. 사용되지 않던 Streamlit 기반
선택 화면 스타일은 제거했고 선택 및 점수 이동 애니메이션은 `picker/`에 유지한다.

## 단일 AI 분석 및 구형 UI 정리

- 게임 1~4는 `games/shared/round_analysis.py`로 사용자·라운드·기사 제목/본문을 식별해 요약과 일치율을 각각 한 번만 수행한다. 정산 오류 후 재시도나 Streamlit 재실행 시 저장된 결과를 재사용하며, 점수 산출 오류가 발생해도 성공한 요약은 보존한다.
- 게임 4는 추가로 `game_4_score`, `game_4_summary`, `game_4_score_details`에 결과를 유지해 선택·공개 애니메이션을 실행한다.
- `games/shared/news_flow.py`의 이전 Streamlit 룰렛/기사 창은 제거했다. 게임 1~4는 공통 HTML/JS 룰렛과 읽기 화면만 사용한다.
- 게임 1의 과거 전체 점수 결과 화면과 게임 3의 구형 점수 반환 형식 처리 및 중복 기사 상태를 제거했다.
