# 게임 화면 구조

## 설계 원칙

- 공통 화면은 games/shared/에 둔다. 베팅, 뉴스 후보 선정, 룰렛, 기사 읽기, AI 분석 로딩에 각각 하나의 구현을 유지한다.
- 게임별 규칙과 정산은 games/game1.py ~ game5.py가 소유한다.
- 게임 1에만 필요한 소수점 두 자리 예측 화면과 튜토리얼은 games/game1.py에 합쳤다.
- games/common.py는 제거하고 공통 기능을 games.shared의 각 모듈에서 직접 가져온다.
- 공통 HTML/CSS/JS 프론트엔드는 games/shared/news_slot/, games/shared/article_reader/에 모아 두며, assets/ 이미지 폴더는 프로젝트 루트에 유지한다.

## 재사용 API

| 공통 화면 | 모듈 및 함수 | 설정 |
|---|---|---|
| 베팅 | games.shared.betting.render_betting_ui | payout_multiplier(순수익 배율), state_key, min_bet |
| 코인 부족 모달 | games.shared.betting.check_user_coins_or_pop_bank | min_required |
| 뉴스 흐름 | games.shared.news_flow.get_game_news_selection | game_id, win_multiplier, immersive_reader |
| 룰렛 | games.shared.roulette.render_news_slot | game_id, continuous_reel, allow_back, allow_direct_url |
| 기사 읽기 | games.shared.article_reader.render_article_reader | game_id, reward |
| 유사도 분석 로딩 | games.shared.loading.similarity_analysis_loading | with 문으로 사용 |

## 게임별 소유 영역

- game1: 공통 베팅·룰렛·기사 읽기·로딩 + 전용 숫자 예측·튜토리얼
- game2: 공통 베팅·룰렛·기사 읽기·로딩 + 전용 HIGH/LOW 예측
- game3: 공통 베팅·로딩 + 전용 홀짝 선택·50% 패배 손실·뉴스 단계
- game4: 공통 베팅·뉴스 선택·로딩 + 전용 구간 예측
- game5: 공통 베팅·로딩 + 전용 범위 선택

각 화면은 게임별 상태 키를 사용하고, iframe에서 온 이벤트의 round_id를 검사한다. 대출금은 랭킹 점수에서 제외한다.

## 테스트
프로젝트 루트에서 python -m unittest discover -s tests -v 실행.

## 공통 모듈 추가 통합
- `games/common.py` 대신 `games.shared.betting`, `games.shared.news_flow` 등의 소유 모듈에서 UI 함수를 직접 가져온다.
- `games/betting_math.py`와 베팅 UI는 `games/shared/betting.py`에 통합했다.
- `games/result_reveal.py`, `games/score_stage.py`는 `games/shared/result.py`로 통합했다.
- 게임 5 튜토리얼은 게임 전용 파일 `games/game5.py`에 포함한다.
