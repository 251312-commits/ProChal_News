"""Validation for new player nicknames and HTML-safe legacy display."""

from html import escape
from unicodedata import category

MAX_NICKNAME_LENGTH = 80
_NICKNAME_CHARACTERS = frozenset(" _.-")
_NICKNAME_ERROR = "닉네임은 1~80자의 문자, 숫자, 공백, _, -, .만 사용할 수 있습니다."


def normalize_nickname(value: str) -> str:
    """Reject HTML and other markup rather than silently changing the name."""
    nickname = value.strip() if isinstance(value, str) else ""
    if not 1 <= len(nickname) <= MAX_NICKNAME_LENGTH or any(
        category(char)[0] not in ("L", "N") and char not in _NICKNAME_CHARACTERS
        for char in nickname
    ):
        raise ValueError(_NICKNAME_ERROR)
    return nickname


def is_valid_nickname(value: str) -> bool:
    try:
        normalize_nickname(value)
    except ValueError:
        return False
    return True


def html_nickname(value: object) -> str:
    """Escape even existing spreadsheet names before adding them to HTML."""
    return escape(str(value), quote=True)
