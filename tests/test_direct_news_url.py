import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch

from modules.news_preprocessing import SUPPORTED_NEWS_SITES, supported_news_site


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class SupportedNewsUrlTests(unittest.TestCase):
    def test_supported_newsroom_domains_and_subdomains(self):
        cases = {
            "https://www.yna.co.kr/view/AKR123": "연합뉴스",
            "https://www.yonhapnewstv.co.kr/news/AKR123": "연합뉴스TV",
            "https://mobile.newsis.com/view/NISX123": "뉴시스",
            "https://www.news1.kr/articles/123": "뉴스1",
            "https://news.kbs.co.kr/news/pc/view/view.do?ncd=1": "KBS",
            "https://imnews.imbc.com/news/2026/society/article/1.html": "MBC",
            "https://news.sbs.co.kr/news/endPage.do?news_id=1": "SBS",
            "https://www.ytn.co.kr/_ln/0103_1": "YTN",
            "https://www.hani.co.kr/arti/society/society_general/1.html": "한겨레",
        }
        self.assertEqual(list(SUPPORTED_NEWS_SITES), list(cases.values()))
        for url, label in cases.items():
            with self.subTest(url=url):
                self.assertEqual(supported_news_site(url), label)

    def test_rejects_lookalike_and_non_http_urls(self):
        for url in (
            "https://yna.co.kr.evil.example/story",
            "javascript:alert(1)",
            "ftp://www.ytn.co.kr/story",
            "https://example.com/story",
            "not a url",
            "",
        ):
            with self.subTest(url=url):
                self.assertIsNone(supported_news_site(url))


class DirectGameOneUrlTests(unittest.TestCase):
    def setUp(self):
        self.st, self.ai, self.ui, self.db = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        self.db.LAST_ARTICLE_HEADER = "마지막기사URL"
        self.db.normalize_article_url.side_effect = lambda url: str(url or "").strip()
        self.db.register_user_article.return_value = (4, True)
        self.db.save_last_article_url.return_value = True
        self.st.session_state = Session(
            game_1_bet=1000,
            current_user="11011",
            current_user_data={"학번": "11011", "아이디": "테스터", "코인": 3000},
            candidates_game_1=[{"title": "후보", "url": "url-1", "count": 0, "row_idx": 2}],
        )
        self.component = self.st.components.v1.declare_component.return_value
        self.component.return_value = None
        modules = patch.dict(sys.modules, {
            "streamlit": self.st,
            "streamlit.components": self.st.components,
            "streamlit.components.v1": self.st.components.v1,
            "modules.news_ai": self.ai,
            "modules.db_handler": self.db,
            "modules.ui_components": self.ui,
        })
        modules.start()
        self.addCleanup(modules.stop)
        self.render = run_module("games.shared.roulette")["render_news_slot"]

    def _round(self):
        candidates = self.st.session_state["candidates_game_1"]
        self.render(candidates)
        args = self.component.call_args.kwargs
        self.assertIn("연합뉴스", args["supported_sources"])
        return args["round_id"], candidates

    def test_invalid_domain_returns_popup_error_without_loading_article(self):
        round_id, candidates = self._round()
        self.component.return_value = {
            "action": "direct_url",
            "round_id": round_id,
            "request_id": "bad-1",
            "url": "https://example.com/story",
        }
        self.render(candidates)
        self.assertIn("올바르지 않은 URL", self.st.session_state["game_1_direct_url_error"])
        self.assertIn("candidates_game_1", self.st.session_state)
        self.ai.bring_article.assert_not_called()
        self.st.rerun.assert_called_once()

    def test_rejects_last_read_article_before_fetching_or_registering(self):
        round_id, candidates = self._round()
        canonical = "https://www.yna.co.kr/view/AKR123"
        submitted = canonical + "?utm_source=share"
        self.st.session_state.current_user_data["마지막기사URL"] = canonical
        self.db.normalize_article_url.side_effect = (
            lambda url: canonical if str(url or "").startswith(canonical) else str(url or "").strip()
        )
        self.component.return_value = {
            "action": "direct_url",
            "round_id": round_id,
            "request_id": "repeat-1",
            "url": submitted,
        }

        self.render(candidates)

        self.assertEqual(
            self.st.session_state["game_1_direct_url_error"],
            "직전 턴에 읽은 기사입니다. 다른 기사를 입력해 주세요.",
        )
        self.assertIn("candidates_game_1", self.st.session_state)
        self.assertNotIn("selected_news_game_1", self.st.session_state)
        self.ai.bring_article.assert_not_called()
        self.db.register_user_article.assert_not_called()
        self.db.save_last_article_url.assert_not_called()
        self.st.rerun.assert_called_once()

    def test_valid_direct_article_becomes_current_article_without_sheet_count(self):
        round_id, candidates = self._round()
        url = "https://www.yna.co.kr/view/AKR123"
        self.ai.bring_article.return_value = (
            "직접 입력 기사",
            "직접 입력한 기사 본문입니다. 본문 추출 성공 여부를 판정하기에 충분한 길이의 테스트 문장입니다.",
            "https://img.yna.co.kr/test.jpg",
        )
        self.component.return_value = {
            "action": "direct_url",
            "round_id": round_id,
            "request_id": "good-1",
            "url": url,
        }
        self.render(candidates)
        chosen = self.st.session_state["selected_news_game_1"]
        self.assertEqual(chosen["url"], url)
        self.assertEqual(chosen["newsroom"], "연합뉴스")
        self.assertEqual(chosen["image_url"], "https://img.yna.co.kr/test.jpg")
        self.assertNotIn("candidates_game_1", self.st.session_state)
        self.ai.bring_article.assert_called_once_with(url, include_image=True)
        self.db.register_user_article.assert_called_once_with(
            self.db.init_news_sheet.return_value,
            url=url,
            title="직접 입력 기사",
            submitter_id="11011",
            submitter_name="테스터",
        )
        self.db.save_last_article_url.assert_called_once_with(
            self.db.init_gspread.return_value, "11011", url
        )
        self.assertEqual(self.st.session_state.current_user_data["마지막기사URL"], url)
        self.st.rerun.assert_called_once()


if __name__ == "__main__":
    unittest.main()
