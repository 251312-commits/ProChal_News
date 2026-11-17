"""Cold-start checks: importing app/view modules must not call remote Sheets APIs.

These checks deliberately avoid real Streamlit secrets and Google API requests.
"""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DeferredStartupTests(unittest.TestCase):
    def test_imports_do_not_execute_network_or_google_secrets(self):
        paths = (
            "news.py", "games/game1/game1.py", "games/game5.py",
            "games/shared/news_flow.py", "views/login.py", "views/main.py",
            "views/ranking.py", "modules/news_summarizer.py",
        )
        for path in paths:
            with self.subTest(path=path):
                tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
                assignments = [
                    node.value for node in tree.body if isinstance(node, (ast.Assign, ast.AnnAssign))
                ]
                for value in assignments:
                    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                        self.assertNotIn(value.func.id, {"init_gspread", "init_news_sheet"})
                    self.assertFalse(
                        isinstance(value, ast.Subscript)
                        and isinstance(value.value, ast.Attribute)
                        and value.value.attr == "secrets",
                        "Secrets should be accessed only when required",
                    )

    def test_worksheet_proxies_delay_resolution_and_forward_attributes(self):
        source = (ROOT / "modules/db_handler.py").read_text(encoding="utf-8")
        module = ast.parse(source)
        nodes = [
            node for node in module.body
            if isinstance(node, (ast.ClassDef, ast.FunctionDef))
            and node.name in ("_DeferredWorksheet", "deferred_user_sheet", "deferred_news_sheet")
        ]
        namespace = {"__name__": "deferred_worksheet_test"}
        class Worksheet:
            col_count = 9
            def get_all_records(self):
                return [{"id": 123}]
        worksheet = Worksheet()
        call_count = {"users": 0, "news": 0}
        def init_gspread():
            call_count["users"] += 1
            return worksheet
        def init_news_sheet():
            call_count["news"] += 1
            return worksheet
        namespace.update(init_gspread=init_gspread, init_news_sheet=init_news_sheet)
        code = compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / "modules/db_handler.py"), "exec")
        exec(code, namespace)
        users = namespace["deferred_user_sheet"]()
        news = namespace["deferred_news_sheet"]()
        self.assertEqual(call_count, {"users": 0, "news": 0})
        self.assertEqual(users.get_all_records(), [{"id": 123}])
        self.assertEqual(news.col_count, 9)
        self.assertEqual(call_count, {"users": 1, "news": 1})


if __name__ == "__main__":
    unittest.main()
