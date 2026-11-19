"""Regression contract for mode-neutral shared game screen copy."""

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class SharedCopyTests(unittest.TestCase):
    def test_betting_copy_describes_the_shared_flow(self):
        betting = read("games/shared/betting.py")
        self.assertIn('<h2 class="cb-heading">베팅 금액 선택</h2>', betting)
        self.assertIn("금액을 정하고 다음 단계로 진행하세요", betting)
        self.assertNotIn("베팅하면 뉴스가 공개됩니다", betting)
        # The small title still identifies the currently selected game.
        self.assertIn("{safe_title}", betting)
        game1 = read("games/game1/game1.py")
        self.assertNotIn('title="title"', game1)

    def test_roulette_copy_is_not_game_specific(self):
        html = read("games/shared/news_slot/index.html")
        js = read("games/shared/news_slot/slot.js")
        self.assertIn("<h1>기사 선택</h1>", html)
        self.assertIn("레버를 당겨 기사 후보를 확인하세요.", js)
        self.assertIn("이번 라운드에서 읽을 기사를 선택하세요.", js)

    def test_reader_copy_does_not_assume_similarity_prediction(self):
        html = read("games/shared/article_reader/index.html")
        js = read("games/shared/article_reader/reader.js")
        self.assertIn("<span>다음 단계까지</span>", html)
        self.assertIn("기사를 읽고 다음 단계로 진행하세요.", html)
        self.assertIn('args.guidance || "기사를 읽고 다음 단계로 진행하세요."', js)
        self.assertIn('args.return_label || "다음 단계로"', js)
        self.assertIn('label: action === "predict" ? "다음 단계 준비 중…"', js)
        self.assertNotIn("유사도 예측하러 가기", html + js)
        self.assertNotIn("예측 화면 자동 이동까지", html + js)


if __name__ == "__main__":
    unittest.main()
