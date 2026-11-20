"""Visible game copy: concise prompts without implementation details."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PlayerFacingCopyTests(unittest.TestCase):
    def test_game1_prediction_and_score_details(self):
        picker = source("games/game1/prediction_screen/index.html")
        self.assertIn("소수점 아래 두 자리를 맞혀보세요.", picker)
        self.assertIn("입력 범위&nbsp; <strong>00 – 99</strong>", picker)
        result = source("games/game1/result_screen/index.html")
        controller = source("games/game1/result_screen/result.js")
        self.assertIn("점수 분석 보기", result)
        self.assertIn("점수 분석 보기", controller)
        self.assertNotIn("판정 이유 · 그래프 보기", result + controller)
        self.assertNotIn("배경음악 플레이어로 결과 음악 연결 중", controller)

    def test_games_two_and_three_keep_rules_without_repeating_actions(self):
        game2 = source("games/game2.py")
        self.assertIn("기준 점수 이상은 <b>HIGH</b>", game2)
        self.assertIn("미만은 <b>LOW</b>", game2)
        self.assertNotIn("소수 둘째 자리까지 표시한 유사도 점수가", game2)
        game3 = source("games/game3.py")
        self.assertIn("정답 +베팅액의 2배 · 오답 −베팅액의 절반", game3)
        self.assertIn('"🤖 유사도 분석"', game3)
        self.assertNotIn("AI가 뉴스 본문을 요약하고 뉴스 제목과", game3)
        self.assertIn('st.metric("AI 점수의 홀짝"', game3)

    def test_game4_copy_and_reveal_share_the_same_prompt(self):
        page = source("games/game4.py")
        html = source("games/game4_ui/picker/index.html")
        js = source("games/game4_ui/picker/picker.js")
        self.assertIn("정답 구간을 선택하세요.", html)
        self.assertIn('subtitle.textContent = "정답 구간을 선택하세요.";', js)
        self.assertIn('subtitle.textContent = "일치율 공개";', js)
        self.assertIn('@st.dialog("점수 분석")', page)
        self.assertNotIn("판정 근거 · 점수 그래프 보기", page)
        self.assertNotIn("AI가 계산한 일치율을 공개합니다", js)

    def test_direct_article_input_has_no_developer_terminology(self):
        html = source("games/shared/news_slot/index.html")
        self.assertIn("지원 언론사의 기사 링크만 입력할 수 있습니다.", html)
        self.assertNotIn("전처리 함수", html)
        self.assertIn("기사 링크 입력", html)

    def test_game5_shared_copy_is_explicitly_preserved(self):
        betting = source("games/shared/betting.py")
        self.assertIn('show_explanatory_copy = state_key == "game_5"', betting)
        self.assertIn("if show_explanatory_copy:", betting)
        reader = source("games/shared/article_reader.py")
        flow = source("games/shared/news_flow.py")
        self.assertIn("hide_default_guidance=False", reader)
        self.assertIn("hide_default_guidance=True", flow)

    def test_no_deployment_instructions_inside_badge_popup(self):
        badges = source("views/badges.py")
        self.assertNotIn("Apps Script를 최신 버전으로 배포", badges)
        self.assertNotIn("조건을 달성하면 컬러로 바뀐다", badges)
        self.assertIn("관리자에게 문의하세요", badges)


if __name__ == "__main__":
    unittest.main()
