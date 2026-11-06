import unittest

from modules.news_preprocessing import clean_common_text


class NewsPreprocessingTests(unittest.TestCase):
    def test_removes_noise_between_paragraphs_without_truncating_the_article(self):
        first = "시가 오늘부터 도서관 개관 시간을 연장한다."
        last = "주말에도 저녁 아홉 시까지 이용할 수 있다."
        noise = [
            "기사 공유하기",
            "이미지 확대",
            "[사진=연합뉴스]",
            "사진 제공: 연합뉴스",
            "[자료사진]",
            "▶ 관련기사: 지난해 도서관 이용 현황",
            "[추천 기사] 새 도서관의 모습",
            "▷ 이메일 : editor@example.com",
            "▷ 전화 : 02-000-0000",
            "AD - 뉴스레터를 구독하세요",
            "북마크 공유 댓글 글자크기 프린트 제보",
            "홍길동 기자 reporter@example.com",
            "ⓒ 연합뉴스. 무단 전재 및 재배포 금지.",
        ]
        for line in noise:
            with self.subTest(line=line):
                self.assertEqual(clean_common_text(f"{first}\n{line}\n{last}"), f"{first}\n\n{last}")

    def test_preserves_subheadings_and_reporting_about_filtered_terms(self):
        lines = [
            "광고 시장 전망",
            "AD(아토피 피부염)는 유아에게도 생긴다.",
            "© 표시는 저작권자를 나타낸다.",
            "독자는 열람 서비스(무료 제공)를 이용할 수 있다.",
            "그는 ‘[사진=연합뉴스]’라는 표기가 필요하다고 말했다.",
            "【기획】 지역 언론의 미래",
            "[사진 산업] 소규모 스튜디오의 실험",
            "새 앱에서는 사진 확대 기능을 쓸 수 있다.",
            "법원은 무단 전재 여부를 가릴 예정이다.",
            "새 약관의 핵심은 무단 전재 및 재배포 금지.",
            "홍길동 기자는 “관련기사와 광고도 조사했다”고 말했다.",
            "피해 신고는 help@example.org로 접수한다.",
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(clean_common_text(line), line)

    def test_removes_an_inline_photo_credit_without_dropping_the_caption_text(self):
        caption = "지역 주민들이 개관식에 참석했다."
        for suffix in [
            "[사진=연합뉴스]",
            "(사진=시청) 무단전재 및 재배포 금지 *재판매 및 DB 금지",
            "© 뉴스1. 무단 전재 및 재배포, AI학습 이용 금지. [사진=시청]",
        ]:
            with self.subTest(suffix=suffix):
                self.assertEqual(clean_common_text(f"{caption} {suffix}"), caption)

    def test_yonhap_wire_article(self):
        lead = "▲ 새 계획 = 시가 어린이도서관을 세운다."
        detail = "▲ 운영 시간 = 문을 여는 시간은 주민 의견을 듣고 정한다."
        raw = "\n".join([
            "송고 2025년09월09일 18시33분",
            f"(서울=연합뉴스) 김가람 기자 = {lead}",
            "[KBS 제공. 재판매 및 DB 금지]",
            detail,
            "제보는 카카오톡 okjebo <저작권자(c) 연합뉴스, 무단 전재-재배포, "
            "AI 학습 및 활용 금지> 2025/09/09 18:33 송고",
        ])
        self.assertEqual(clean_common_text(raw), f"{lead}\n\n{detail}")

    def test_corner_bracket_byline_and_invisible_spaces(self):
        raw = "【서울=뉴시스】김가람 기자 = 첫\u00a0보도다.\r\n\ufeff이미지\u200b 확대"
        self.assertEqual(clean_common_text(raw), "첫 보도다.")

    def test_newsis_wire_article(self):
        lead = "도서관이 신간 신청을 받는다."
        detail = "등록 마감은 2024년 10월 9일 오후 두 시다."
        raw = "\n".join([
            "등록 2024.10.09 01:50:00 수정 2024.10.09 14:14:30",
            f"[서울=뉴시스]김가람 인턴 기자 = {lead}",
            detail,
            "◎공감언론 뉴시스 reporter@example.com",
        ])
        self.assertEqual(clean_common_text(raw), f"{lead}\n\n{detail}")

    def test_preserves_paragraph_order_and_is_idempotent(self):
        lead = "운영 시간이 늘어난다."
        detail = "시범 운영은 다음 달까지 이어진다."
        cleaned = clean_common_text(f"  {lead}  \r\n광고\r\n{lead}\r\n\r\n{detail}\r\n")
        self.assertEqual(cleaned, f"{lead}\n\n{detail}")
        self.assertEqual(clean_common_text(cleaned), cleaned)

    def test_noise_only_input_is_empty(self):
        for text in ("", "\n   \n", "[광고]\n이미지 확대"):
            with self.subTest(text=text):
                self.assertEqual(clean_common_text(text), "")


if __name__ == "__main__":
    unittest.main()
