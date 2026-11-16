# 배지 시스템 기반 처리 — 20개 / 표시 기능은 후속 작업

## 이번 변경 범위

- 배지와 칭호는 한 항목이다. 장착 슬롯은 하나이며 미장착 값은 `"0"`이다.
- 메인·랭킹에는 추후 아이콘만 표시한다. 이번 변경에는 아이콘, 팝업, CSS, 후광 애니메이션이 없다.
- Common은 기본색, Rare는 청록색, Epic은 보라색이다. Legendary 4개만 각각의 색·후광·고유 효과 정보를 가진다.
- 효과는 실제 실행 코드가 아닌 허용된 식별자만 저장한다. 장착한 배지 하나의 효과만 해석한다. 보유 효과를 중첩하지 않는다.
- 코인 지급률, 대출, 이자, 랭킹 계산과 기존 Users 열은 변경하지 않는다.
- 해금은 영구 보유이며 자동 장착하지 않는다. 배지로 코인·승률을 높이지 않는다.

## 안전한 적용 순서

1. 기존 Google 스프레드시트를 백업한다. 지금 Users에 J/K열이나 배지 번호를 수동으로 만들 필요는 없다.
2. 이 PR의 Python 코드를 병합하고 앱이 갱신됐는지 확인한다. 배지 수집은 기본적으로 꺼져 있어 기존 화면은 그대로이다.
3. 기존 거래용 Apps Script 프로젝트에 최신 `apps_script/Code.gs`를 복사하고, `BadgeCatalog.gs`와 `Badges.gs`를 새 스크립트 파일로 추가한다. 세 파일을 함께 배포해야 한다.
4. 편집기에서 `installBadgeSystem()`을 한 번 실행한다. `BadgeProfiles` 탭과 헤더만 만든다. 기존 데이터가 있으면 보존하고, 이름이 같은 다른 구조의 탭이면 중단한다. `Users`와 `Transactions`는 바꾸지 않는다.
5. Apps Script 웹 앱을 **새 버전으로 배포**한다. 기존 배포 URL과 거래 토큰은 유지한다. GitHub 병합만으로 Apps Script가 배포되지는 않는다.
6. 아래 검증 절차를 복사본에서 먼저 수행한 뒤, 편집기에서 `enableBadgeCollection()`을 실행한다. 이때부터 정상 정산된 게임 1~5의 기록이 쌓인다. Streamlit Secrets에 새 항목을 추가할 필요는 없다.

`disableBadgeCollection()`은 수집만 멈춘다. 기존 보유·장착·누적 기록은 지우지 않는다. 재활성화하면 새로운 수집 구간 ID(epoch)를 만들므로, 수집하지 않은 기간을 공통/게임별 연승으로 연결하지 않는다. 이미 해금한 배지와 최고 기록은 보존한다. Script Properties를 수동 편집하는 대신 이 관리 함수를 사용한다.

이 저장소 변경만으로 실제 사용자 시트가 수정되거나, 현재 운영 Apps Script가 배포되지는 않는다. 실서비스 활성화는 위 절차가 필요하다.

## 저장 구조

`BadgeProfiles`는 계정 ID 기준으로 한 행을 사용한다. 닉네임 변경과 무관하게 같은 계정에 귀속된다.

| 열 | 값 |
|---|---|
| student_id | 기존 학번/교사 ID |
| equipped_badge | 고정 배지 ID 또는 `0` |
| unlocked_json | 배지 ID → 최초 획득 시각과 근거 라운드 ID |
| progress_json | 공통·게임별 완료/승리/연승, 방향별 승리, 근접 오차 횟수, 수집 구간 ID |
| revision | 장착·해금·진행도 갱신 버전 |
| updated_at | UTC ISO 시각 |
| schema_version | 현재 1 |

보유 목록 순서와 장착 상태를 섞지 않는다. JSON을 수동으로 편집하거나 열 이름을 변경하지 않는다. 모르는 ID, 손상된 JSON, 중복 계정 행은 자동 초기화하지 않고 오류로 처리한다. 안정적으로 운영하려면 기존 거래 원장과 마찬가지로 이 탭의 직접 편집 권한도 제한한다.

## 판정 및 중복 방지

`modules/transactions.py`의 공통 정산 경로에 연결했다. 별도 화면이나 반복 렌더링에서 횟수를 올리지 않는다. 앱이 확인한 승패·선택을 기존 인증된 거래 요청에 넣고, Apps Script에서 조건을 판정한다. 프런트엔드가 해금할 배지 ID를 제출하는 API는 없다.

동일 ScriptLock 안에서 라운드 중복 여부를 검사하고 **코인·기존 거래 영수증·배지 프로필을 하나의 Sheets batchUpdate**로 저장한다. 정상 정산 전에는 카운트하지 않는다. 같은 거래 번호를 다시 보내면 원래 영수증과 현재 배지 상태를 반환하며 횟수·획득·장착을 다시 적용하지 않는다. 같은 라운드에 다른 근거를 보내면 거부한다.

게임 1은 정산 전에 요약·점수 결과를 세션에 고정한다. 통신 응답이 사라져 재시도하더라도 같은 라운드를 다른 AI 점수로 다시 판정하지 않는다. 다른 계정·새 라운드에서는 재사용하지 않는다. 게임 2/3은 이미 확정한 `game_2_user_choice`, `game_3_choice`를 사용한다.

게임 1의 오차는 **소수 두 자리의 절댓값 차이**이다. 1은 0.01%p, 10은 0.10%p이다. `99↔00`은 99 차이이며 순환하지 않는다. 근접 배지는 실패한 판에만 지급한다. 0.01%p 차이는 08·09·11을 함께 해금하고, 정확한 적중은 12만 해금한다(별도의 누적/공통 조건은 동시에 달성할 수 있다).

공통 연승은 모든 게임의 **정산 완료 순서**를 따른다. 여러 탭을 사용해도 먼저 정산된 결과가 먼저 반영된다. 5/8연승의 다양성은 기존 main의 판정 규칙을 유지해 최근 5승/8승 안에 2종/3종을 포함했는지 판정한다. 더 오래된 승리는 이 다양성 계산에서 제외한다. 게임별 연승은 그 게임의 결과만 이어서 세며 다른 게임의 패배로 끊기지 않는다.

과거 기록은 자동 소급하지 않는다. 활성화 이전 완료·승리·연승과 옛 게임 1의 점수 차이를 추정해 지급하지 않는다. 기존 Users의 연승 표시와 새 업적의 수집 시작 후 연승 수는 초기에 다를 수 있다. 과거 라운드의 정산을 재전송해도 배지가 소급 발급되지 않는다.

## 다음 화면 작업에서 사용할 인터페이스

- `modules.badge_service.get_catalog()`: 20개 이름·조건·등급·아이콘 키·효과 정보를 반환한다.
- `fetch_badge_profile()`: 로그인한 계정의 최신 보유·장착·진행도를 조회한다.
- `get_badge_progress(profile)`: 잠금 상태와 각 조건의 현재/목표 값을 반환한다. 획득한 연승 배지는 나중에 패배해도 완료로 표시한다.
- `equip_badge(id, expected_revision=..., request_id=...)`: 하나를 장착한다. `0`으로 해제한다. 미보유 배지와 오래된 프로필 버전은 거부한다.
- `request_id`는 `transaction_id("badge_equip")`로 사용자 선택마다 한 번 만들고, 타임아웃 재시도에는 그대로 재사용한다. 이전 장착 요청을 다시 보내도 더 최근 장착 상태로 되돌리지 않는다.

메인·랭킹 표시 코드와 프로필 팝업은 아직 이 인터페이스를 호출하지 않는다. 공개 랭킹에는 계정 ID로 장착 ID만 연결해야 하며, 프로필 전체나 거래 인증 토큰을 브라우저에 전달하지 않는다. Legendary 연출에는 `prefers-reduced-motion`을 반영해 정적 후광으로 대체할 준비 정보를 포함했다.

## 검증

```sh
python scripts/sync_badge_catalog.py --check
python -m unittest discover -s tests -p 'test_badge*.py' -v
node --test tests/test_badges.cjs
```

Node 테스트는 실제 `.gs` 원본을 로드하고 메모리 기반 Sheets/LockService 모형으로 정산·원장·배지의 통합 경로를 실행한다. 경계 오차, 중복 요청, 실패한 일괄 쓰기, 미보유 장착, 변경 충돌, 계정 분리, 수집 재개를 포함한다. Python 테스트는 게임 선택 전달, 서버 설정 전환, 재시도, 장착 API, 게임 1의 점수 고정을 검증한다. 실제 Apps Script/시트/브라우저를 실행한 테스트를 대신하지 않는다.

운영 활성화 전에 시트 복사본에서 한 판 완료, 같은 정산 재전송, 게임별 선택, 배지 장착/해제, 다른 탭의 오래된 장착 요청을 확인한다. 코인과 대출 기능도 함께 확인한다. 이 PR은 아이콘 파일을 아직 요구하지 않는다.

## 확정된 20개

원본은 `modules/badge_catalog.json`이다. 조건과 이름을 변경하면 `python scripts/sync_badge_catalog.py`를 실행해 Apps Script용 카탈로그를 다시 생성한다. ID는 변경하거나 재사용하지 않는다.

| 번호 | 게임 | 배지 이름 | 해금 업적 | 등급 | 효과 식별자 |
|---|---|---|---|---|---|
| 01 | 공통 | 신입 에이전트 | 아무 게임이나 1회 완료 | common | default / none / none |
| 02 | 공통 | 뉴스 유목민 | 게임 1~5를 각각 1회 완료 | common | default / none / none |
| 03 | 공통 | 단골 관측자 | 모든 게임을 합쳐 누적 30회 완료 | rare | cyan / none / none |
| 04 | 공통 | 연승의 신호탄 | 게임 종류와 관계없이 3연승 | rare | cyan / none / none |
| 05 | 공통 | 흐름을 타는 자 | 서로 다른 게임 2종 이상을 포함해 5연승 | epic | purple / none / none |
| 06 | 공통 | 무패의 궤도 | 서로 다른 게임 3종 이상을 포함해 8연승 | legendary | gold / gold / orbiting_stars |
| 07 | 게임 1 | 소수점 견습생 | 게임 1 누적 10회 완료 | common | default / none / none |
| 08 | 게임 1 | 근접 조우 | 정답과 0.10%p 이내 차이로 실패 | common | default / none / none |
| 09 | 게임 1 | 예민한 촉 | 정답과 0.03%p 이내 차이로 실패 | rare | cyan / none / none |
| 10 | 게임 1 | 엇나간 소수점 | 정답과 정확히 0.10%p 차이로 실패 | epic | purple / none / none |
| 11 | 게임 1 | 한 끗의 운명 | 정답과 정확히 0.01%p 차이로 실패 | epic | purple / none / none |
| 12 | 게임 1 | 소수점의 지배자 | 소수점 두 자리 정확히 1회 적중 | legendary | ice_white / blue / numeric_particles |
| 13 | 게임 2 | 방향 감각 | HIGH/LOW 예측 누적 10회 성공 | rare | cyan / none / none |
| 14 | 게임 2 | 양방향 레이더 | HIGH와 LOW 각각 누적 15회 적중 | epic | purple / none / none |
| 15 | 게임 3 | 양면의 승부사 | 홀과 짝 각각 누적 5회 적중 | rare | cyan / none / none |
| 16 | 게임 3 | 끊기지 않는 박자 | 게임 3에서 5연승 | epic | purple / none / none |
| 17 | 게임 4 | 구간 포착자 | 정답 구간 누적 5회 선택 | rare | cyan / none / none |
| 18 | 게임 4 | 경계의 지배자 | 게임 4에서 4연승 | legendary | light_purple / purple / closing_brackets |
| 19 | 게임 5 | 기사 감별사 | 정답 기사 누적 3회 선택 | rare | cyan / none / none |
| 20 | 게임 5 | 특종의 눈 | 게임 5에서 3연승 | legendary | platinum / red / scanline |

## 기존 main과의 호환성

작업 중 main에 먼저 병합된 `modules/badges.py`의 20개 ID와 공개 함수(`BADGES`, `BADGE_BY_ID`, `parse_owned`, `serialize_owned`, `equipped_badge`, `evaluate_achievements`)를 유지한다. 기존 7개 테스트도 그대로 보존한다. 정산 서버 연결은 별도 `modules/badge_service.py`에 둔다. 두 모듈의 목록은 같은 JSON에서 읽으므로 중복 정의하지 않는다.

기존 문서의 Users J/K 및 AchievementEvents는 미실행 제안이었다. 이번 구현은 이를 `BadgeProfiles`와 기존 Transactions의 detail 기록으로 구체화하며, J/K 열을 생성하거나 옮기지 않는다. 기존 순수 평가 함수는 정산 이벤트를 오프라인으로 평가하는 호환 인터페이스이며 운영 중 배지를 직접 지급하지 않는다. 운영 해금은 Apps Script의 원자적 정산 경로에서만 실행한다.
