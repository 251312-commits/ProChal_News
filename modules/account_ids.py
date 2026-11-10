"""School student ID and server-issued teacher ID patterns."""

import re

_STUDENT_ID = re.compile(r"[1-3]0[1-5][01][0-9]\Z")
_TEACHER_ID = re.compile(r"4[0-9]{4}\Z")


def is_valid_student_id(value: object) -> bool:
    """Student IDs: a=1..3, b=0, c=1..5, d=0..1, e=0..9."""
    return isinstance(value, str) and _STUDENT_ID.fullmatch(value) is not None


def is_valid_teacher_id(value: object) -> bool:
    """Teacher IDs are allocated by the gateway from 40101 upwards."""
    return isinstance(value, str) and _TEACHER_ID.fullmatch(value) is not None
