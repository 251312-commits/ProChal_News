import unittest

from modules.db_handler import (
    LAST_ARTICLE_COLUMN,
    LAST_ARTICLE_HEADER,
    NEWS_HEADERS,
    article_url_hash,
    ensure_news_schema,
    normalize_article_url,
    register_user_article,
    save_last_article_url,
)


class FakeWorksheet:
    def __init__(self, headers, records=None, first_column=None):
        self.headers = list(headers)
        self.records = list(records or [])
        self.first_column = list(first_column or ["학번"])
        self.col_count = len(self.headers)
        self.updates = []
        self.appends = []
        self.added_cols = 0

    def row_values(self, row):
        self.assert_row(row)
        return list(self.headers)

    def assert_row(self, row):
        if row != 1:
            raise AssertionError(row)

    def add_cols(self, amount):
        self.added_cols += amount
        self.col_count += amount

    def update_cell(self, row, column, value):
        self.updates.append((row, column, value))
        if row == 1:
            while len(self.headers) < column:
                self.headers.append("")
            self.headers[column - 1] = value

    def get_all_records(self):
        return list(self.records)

    def append_row(self, values, value_input_option=None):
        self.appends.append((list(values), value_input_option))
        self.records.append(dict(zip(NEWS_HEADERS, values)))

    def col_values(self, column):
        if column != 1:
            raise AssertionError(column)
        return list(self.first_column)


class NewsPoolMetadataTests(unittest.TestCase):
    def test_normalizes_tracking_variants_to_one_article(self):
        first = "https://WWW.YNA.CO.KR/view/AKR1?utm_source=x&foo=2#top"
        second = "https://www.yna.co.kr/view/AKR1?foo=2"
        self.assertEqual(normalize_article_url(first), second)
        self.assertEqual(article_url_hash(first), article_url_hash(second))

    def test_existing_three_column_news_sheet_becomes_metadata_pool(self):
        ws = FakeWorksheet(["URL", "Count", "Title"])
        ensure_news_schema(ws)
        self.assertEqual(ws.headers, list(NEWS_HEADERS))
        self.assertEqual(ws.added_cols, len(NEWS_HEADERS) - 3)
        self.assertEqual([u[1] for u in ws.updates], list(range(4, len(NEWS_HEADERS) + 1)))

    def test_user_article_is_added_once_with_submitter_metadata(self):
        existing = {
            "URL": "https://www.yna.co.kr/view/OLD",
            "Count": 2,
            "Title": "기본 기사",
        }
        ws = FakeWorksheet(list(NEWS_HEADERS), records=[existing])
        row, created = register_user_article(
            ws,
            url="https://www.ytn.co.kr/_ln/0103_1?utm_medium=social",
            title="사용자 기사",
            submitter_id="11011",
            submitter_name="테스터",
        )
        self.assertTrue(created)
        self.assertEqual(row, 3)
        values, mode = ws.appends[0]
        self.assertEqual(values[3:6], ["11011", "테스터", "user"])
        self.assertIs(values[7], True)
        self.assertEqual(mode, "RAW")

        row2, created2 = register_user_article(
            ws,
            url="https://www.ytn.co.kr/_ln/0103_1",
            title="중복 기사",
            submitter_id="22022",
            submitter_name="다른사람",
        )
        self.assertFalse(created2)
        self.assertEqual(row2, 3)
        self.assertEqual(len(ws.appends), 1)

    def test_last_article_uses_users_i_without_touching_loan_columns(self):
        headers = ["학번", "아이디", "코인", "연승", "추천인", "비밀번호", "대출금", "대출원금"]
        ws = FakeWorksheet(headers, first_column=["학번", "11011", "22022"])
        saved = save_last_article_url(ws, "11011", "https://www.yna.co.kr/view/AKR1#top")
        self.assertTrue(saved)
        self.assertIn((1, LAST_ARTICLE_COLUMN, LAST_ARTICLE_HEADER), ws.updates)
        self.assertIn((2, LAST_ARTICLE_COLUMN, "https://www.yna.co.kr/view/AKR1"), ws.updates)
        self.assertEqual(headers[6:8], ["대출금", "대출원금"])


if __name__ == "__main__":
    unittest.main()
