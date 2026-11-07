import hashlib
from datetime import datetime, timezone
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import gspread
import streamlit as st
from google.oauth2.service_account import Credentials


NEWS_HEADERS = (
    "URL", "Count", "Title", "SubmittedBy", "SubmittedByName",
    "SourceType", "AddedAt", "Active", "URLHash",
)
LAST_ARTICLE_HEADER = "마지막기사URL"
LAST_ARTICLE_COLUMN = 9  # Users!I. G=대출금, H=대출원금 are reserved by the ledger.


# ==========================================
# 3. 구글 시트 연결 캐싱 (gspread)
# ==========================================
@st.cache_resource
def init_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    gc = gspread.authorize(credentials)

    sheet_url = "https://docs.google.com/spreadsheets/d/1-Kx4qK9SOV3fXF9q9jIYGefPDPQl_gkZK6iHUabKwmE/edit?usp=drivesdk"
    doc = gc.open_by_url(sheet_url)
    worksheet = doc.worksheet("Users")
    return worksheet


def save_bank_balances(*_args, **_kwargs):
    """Reject obsolete check-then-write callers.

    Direct gspread updates cannot lock out another Streamlit session.
    Bank views now use modules.transactions.bank_transaction().
    """
    raise RuntimeError("Unsafe bank write disabled; use bank_transaction()")


def _ensure_grid_columns(ws, required_columns: int) -> None:
    try:
        current = int(ws.col_count)
    except (TypeError, ValueError, AttributeError):
        current = required_columns
    if current < required_columns:
        ws.add_cols(required_columns - current)


def ensure_news_schema(ws) -> None:
    """Add metadata columns without changing the original A:C news pool."""
    _ensure_grid_columns(ws, len(NEWS_HEADERS))
    headers = list(ws.row_values(1))
    for column, expected in enumerate(NEWS_HEADERS, start=1):
        current = str(headers[column - 1]).strip() if column <= len(headers) else ""
        if current and current != expected:
            raise RuntimeError(
                f"News!{column} 열은 '{current}' 사용 중이라 '{expected}'로 덮어쓸 수 없습니다."
            )
        if not current:
            ws.update_cell(1, column, expected)


def ensure_last_article_column(users_ws) -> None:
    """Reserve Users!I for the last article URL.

    Users!G and Users!H belong to the loan ledger and must never be repurposed.
    """
    _ensure_grid_columns(users_ws, LAST_ARTICLE_COLUMN)
    headers = list(users_ws.row_values(1))
    current = (
        str(headers[LAST_ARTICLE_COLUMN - 1]).strip()
        if len(headers) >= LAST_ARTICLE_COLUMN else ""
    )
    if current and current != LAST_ARTICLE_HEADER:
        raise RuntimeError(
            f"Users!I 열은 '{current}' 사용 중이라 '{LAST_ARTICLE_HEADER}'로 덮어쓸 수 없습니다."
        )
    if not current:
        users_ws.update_cell(1, LAST_ARTICLE_COLUMN, LAST_ARTICLE_HEADER)


def _student_id(value) -> str:
    raw = str(value or "").strip()
    return raw.removesuffix(".0")


_TRACKING_QUERY_KEYS = {"fbclid", "gclid", "dclid", "igshid"}


def normalize_article_url(url: str) -> str:
    """Canonicalize a news URL for duplicate and last-seen comparisons."""
    raw = str(url or "").strip()
    try:
        parsed = urlsplit(raw)
    except ValueError:
        return raw
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return raw

    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower().rstrip(".")
    try:
        port = parsed.port
    except ValueError:
        return raw
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        host = f"{host}:{port}"

    query_pairs = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered in _TRACKING_QUERY_KEYS:
            continue
        query_pairs.append((key, value))
    query_pairs.sort()
    path = parsed.path or "/"
    return urlunsplit((scheme, host, path, urlencode(query_pairs, doseq=True), ""))


def article_url_hash(url: str) -> str:
    canonical = normalize_article_url(url)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def news_row_is_active(row: dict) -> bool:
    value = str(row.get("Active", "")).strip().casefold()
    return value not in {"false", "0", "no", "n", "off", "inactive"}


def register_user_article(
    news_ws, *, url: str, title: str, submitter_id: str, submitter_name: str = ""
):
    """Add a validated user article to the shared pool unless it already exists.

    Returns (row_index, created). Existing A:C rows remain the base pool.
    """
    ensure_news_schema(news_ws)
    canonical = normalize_article_url(url)
    digest = article_url_hash(canonical)
    records = news_ws.get_all_records()
    for idx, row in enumerate(records, start=2):
        existing_hash = str(row.get("URLHash", "")).strip()
        existing_url = normalize_article_url(row.get("URL", ""))
        if (existing_hash and existing_hash == digest) or existing_url == canonical:
            return idx, False

    news_ws.append_row(
        [
            canonical,
            0,
            str(title or "").strip(),
            _student_id(submitter_id),
            str(submitter_name or "").strip(),
            "user",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            True,
            digest,
        ],
        value_input_option="RAW",
    )
    return len(records) + 2, True


def save_last_article_url(users_ws, student_id: str, url: str) -> bool:
    """Persist the user's most recently opened article in Users!I."""
    sid = _student_id(student_id)
    if not sid:
        return False
    ensure_last_article_column(users_ws)
    for row_index, value in enumerate(users_ws.col_values(1), start=1):
        if row_index == 1:
            continue
        if _student_id(value) == sid:
            users_ws.update_cell(row_index, LAST_ARTICLE_COLUMN, normalize_article_url(url))
            return True
    return False


# ==========================================
# 뉴스 전용 구글 시트 워크시트 연결
# ==========================================
@st.cache_resource
def init_news_sheet():
    ws = init_gspread()
    doc = ws.spreadsheet
    try:
        news_ws = doc.worksheet("News")
    except gspread.WorksheetNotFound:
        news_ws = doc.add_worksheet(title="News", rows="100", cols=str(len(NEWS_HEADERS)))
        news_ws.append_row(list(NEWS_HEADERS))
        return news_ws
    ensure_news_schema(news_ws)
    return news_ws
