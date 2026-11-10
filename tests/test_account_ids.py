"""School ID format regression tests."""

import unittest

from modules.account_ids import is_valid_student_id, is_valid_teacher_id


class AccountIdTests(unittest.TestCase):
    def test_student_format(self):
        for value in ("10100", "10519", "20101", "30519"):
            with self.subTest(value=value):
                self.assertTrue(is_valid_student_id(value))
        for value in ("", "00101", "40101", "10001", "11001", "10601",
                      "10120", "1011", "101011", "1０101", None):
            with self.subTest(value=value):
                self.assertFalse(is_valid_student_id(value))

    def test_teacher_format(self):
        for value in ("40101", "40109", "40110", "49999"):
            self.assertTrue(is_valid_teacher_id(value))
        for value in ("00101", "30101", "10101", "4000", None):
            self.assertFalse(is_valid_teacher_id(value))


if __name__ == "__main__":
    unittest.main()
