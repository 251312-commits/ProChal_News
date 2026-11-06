"""Plain-text filters for Korean articles extracted by newspaper3k."""

import re


UI_WORDS = {
    "광고", "[광고]", "(광고)", "ad", "advertisement", "광고 닫기",
    "본문", "기사본문", "본문 바로가기", "기사 본문 바로가기", "전체재생",
    "동영상 고정", "동영상 고정 취소", "이미지 확대", "사진 확대",
    "이미지 크게보기", "사진 크게보기", "사진 확대보기", "이미지 확대보기", "기사 공유하기", "공유하기",
    "기사 스크랩", "기사 인쇄", "구독하기", "댓글", "댓글 보기", "댓글 쓰기",
    "글자 크기", "글자크기", "글자 크기 조절", "글자 크기 조정", "프린트",
    "url 복사", "북마크 공유 댓글 글자크기 프린트 제보",
    "제보하기", "관련기사", "관련 기사", "추천 기사", "함께 보면 좋은 기사",
    "많이 본 기사", "함께 읽기 좋은 콘텐츠", "좋아요 슬퍼요 화나요 후속요청",
}

_EMAIL = r"[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}"
_REPORTER = r"[가-힣]{2,4}\s*(?:(?:인턴|수습|선임)\s*)?(?:기자|특파원)"
_WIRE_BYLINE = (
    r"(?:\([가-힣·]+\s*=\s*[\w·]+\)|\[[가-힣·]+\s*=\s*[\w·]+\]|【[가-힣·]+\s*=\s*[\w·]+】)"
    rf"\s*{_REPORTER}\s*="
)
_SIGNATURE = re.compile(
    rf"(?:{_REPORTER}(?:\s+{_EMAIL}|\s*\({_EMAIL}\))?|(?:◎\s*공감언론\s+뉴시스\s+)?{_EMAIL})"
)

_STAMP = (
    r"(?:\d{4}[./-]\s*\d{1,2}[./-]\s*\d{1,2}\.?\s+(?:(?:오전|오후)\s*)?\d{1,2}:\d{2}(?::\d{2})?"
    r"|\d{4}년\s*\d{1,2}월\s*\d{1,2}일\s*\d{1,2}시\s*\d{1,2}분)"
)
_TIME_LABEL = r"(?:기사\s*)?(?:입력|등록|송고|수정|업데이트)"
_PUBLICATION_TIME = re.compile(rf"(?:{_TIME_LABEL}\s*[:：]?\s*{_STAMP}\s*)+")
_AD = re.compile(r"(?:(?:광고|ad)\s*[:：|]|(?:광고|ad)\s+-\s+|\[광고\]\s+|\(광고\)\s+).+", re.IGNORECASE)
_LINK_LABEL = r"(?:관련\s*기사|추천\s*기사|함께\s*읽을\s*기사)"
_RELATED_LINK = re.compile(rf"(?:[▶▷]\s*)?(?:{_LINK_LABEL}\s*[:：]|\[{_LINK_LABEL}\]).+")
_TIP = re.compile(
    rf"(?:[■▶▷]\s*제보하기|[▶▷]\s*이메일\s*[:：]\s*{_EMAIL}"
    r"|[▶▷]\s*전화\s*[:：]\s*[\d-]{8,15}|제보는 카카오톡 okjebo)"
)
_YONHAP_FOOTER = re.compile(
    rf"(?:제보는 카카오톡 okjebo\s*)?<저작권자\(c\) 연합뉴스,[^<>]*금지>(?:\s*{_STAMP}\s*송고)*",
    re.IGNORECASE,
)

_RIGHTS = (
    r"\*?(?:무단\s*(?:전재|복제)\s*(?:및|[-·,])?\s*재배포|재판매\s*및\s*DB)"
    r"(?:,\s*AI\s*학습\s*(?:및\s*활용|이용))?\s*금지\.?"
)
_COPYRIGHT = (
    r"(?:(?:저작권자\s*[:：]?\s*|copyright\s*)?(?:©|ⓒ|\(c\))\s*|저작권자\s*[:：]\s*)"
    r"(?:\d{4}\s+)?[\w.·-]+(?:\s+뉴스)?[.,]?(?:\s+all rights reserved\.?)?"
)

# Bare '제공' can also be editorial text, e.g. '(무료 제공)'.
_MEDIA = r"(?:연합뉴스|뉴시스|뉴스1|KBS|MBC|SBS|YTN)"
_PHOTO_SIGNATURE = re.compile(rf"(?:사진|영상)(?:\s*제공)?\s*[:=：]\s*(?:{_MEDIA}|{_REPORTER})", re.IGNORECASE)
_CREDIT = (
    r"(?:(?:사진|영상|이미지|자료)(?:\s*(?:제공|출처))?\s*[:=：]\s*[^\[\]()]+"
    rf"|{_MEDIA}\s+(?:자료사진|제공|캡처)"
    r"|[\w· -]+\s+제공[.,]\s*재판매\s*및\s*DB\s*금지\.?)"
)
_CREDIT_TAG = rf"(?:\[자료사진\]|\[{_CREDIT}\]|\({_CREDIT}\))"
_PREFIX = re.compile(rf"^(?:(?:{_WIRE_BYLINE}|{_CREDIT_TAG})\s*)+", re.IGNORECASE)

# A bare rights notice can end a sentence about copyright. Strip it only as a
# separate notice (line start, after punctuation, or following a marked credit).
_NOTICE = rf"(?:{_COPYRIGHT}(?:\s*{_RIGHTS})?|{_RIGHTS})(?:\s+{_RIGHTS})*"
_METADATA = re.compile(
    rf"(?:{_CREDIT_TAG}(?:\s*{_NOTICE})?|(?:^|(?<=[.!?])\s+){_NOTICE})\s*",
    re.IGNORECASE,
)


def is_ad_or_ui_line(line: str) -> bool:
    line = line.strip()
    return not line or line.casefold() in UI_WORDS or bool(
        _AD.fullmatch(line) or _RELATED_LINK.fullmatch(line) or _TIP.fullmatch(line)
    )


def _join_paragraphs(lines) -> str:
    return "\n\n".join(dict.fromkeys(line for line in lines if not is_ad_or_ui_line(line)))


def remove_duplicate_and_ui_lines(text: str) -> str:
    return _join_paragraphs(line.strip() for line in text.splitlines())


def _clean_line(raw: str) -> str:
    line = " ".join(raw.replace("\u200b", "").replace("\ufeff", "").split())
    line = _PREFIX.sub("", line)
    # Remove only a contiguous run at the end. A quoted credit inside prose stays intact.
    start, end = 0, -1
    for match in _METADATA.finditer(line):
        if match.start() != end:
            start = match.start()
        end = match.end()
    if end == len(line):
        line = line[:start].rstrip()
    if any(rule.fullmatch(line) for rule in (_SIGNATURE, _PHOTO_SIGNATURE, _PUBLICATION_TIME, _YONHAP_FOOTER)):
        return ""
    return line


def clean_common_text(text: str) -> str:
    return _join_paragraphs(_clean_line(line) for line in text.splitlines())
