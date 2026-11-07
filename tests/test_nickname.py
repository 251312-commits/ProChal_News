"""Nickname registration rules and HTML output regression tests."""

import unittest

from modules.nickname import html_nickname, is_valid_nickname, normalize_nickname


class NicknameSecurityTests(unittest.TestCase):
    def test_safe_nicknames_keep_unicode_and_spaces(self):
        for value in ("안닢", "홍 길동", "Mina_02", "Jane-Doe.", "李小龍"):
            with self.subTest(value=value):
                self.assertTrue(is_valid_nickname(value))
                self.assertEqual(normalize_nickname(" " + value + " "), value)

    def test_rejects_html_and_other_unsafe_input(self):
        for value in (
            "<script>alert(1)</script>",
            "<img src=x onerror=alert(1)>",
            "&lt;script&gt;",
            'name" onmouseover="alert(1)',
            "=HYPERLINK('url')",
            "a\nb",
            "a/b",
            "  ",
            "x" * 81,
            None,
        ):
            with self.subTest(value=value):
                self.assertFalse(is_valid_nickname(value))
                with self.assertRaises(ValueError):
                    normalize_nickname(value)

    def test_escapes_legacy_nicknames_read_from_sheet(self):
        value = '''"><img src=x onerror="alert(1)">& ' hi'''
        safe = html_nickname(value)
        self.assertNotIn("<img", safe)
        self.assertEqual(safe, "&quot;&gt;&lt;img src=x onerror=&quot;alert(1)&quot;&gt;&amp; &#x27; hi")


if __name__ == "__main__":
    unittest.main()
