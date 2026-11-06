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

    def test_yonhap_tv_report_with_player_and_footer(self):
        lead = "도서관이 야간 열람을 시작했다."
        detail = "토요일에도 저녁까지 이용할 수 있다."
        player = [
            "브라우저가 video 태그를 지원하지 않습니다.",
            "죄송하지만 다른 브라우저를 사용하여 주십시오.",
            "브라우저가 오디오 태그를 지원하지 않습니다.", "닫기",
        ]
        footer = [
            "연합뉴스TV 기사문의 및 제보 : 카톡/라인 jebo23",
            "김종성(goldbell@yna.co.kr)", "당신이 담은 순간이 뉴스입니다!",
        ]
        for raw, expected in [
            ("\n".join([*player, lead, detail, *footer]), f"{lead}\n\n{detail}"),
            (" ".join([*player, lead, detail, *footer]), f"{lead} {detail}"),
            ("\n".join([player[0], " ".join(player[1:]), "", *footer]), ""),
        ]:
            with self.subTest(raw=raw):
                cleaned = clean_common_text(raw)
                self.assertEqual(cleaned, expected)
                self.assertEqual(clean_common_text(cleaned), cleaned)

    def test_yonhap_tv_tip_joined_to_reporter_byline(self):
        footer = "연합뉴스TV 기사문의 및 제보 : 카톡/라인 jebo23한채희(1ch@yna.co.kr)"
        story = "도서관이 주말에도 문을 연다."
        for raw, expected in [
            (footer, ""),
            (f"{story}\n{footer}\n다음 문단이다.", f"{story}\n\n다음 문단이다."),
            (f"{story}{footer}", story),
            ("주말 개관 안내 " + footer, "주말 개관 안내"),
            (f"{story} {footer}김가람(editor@example.org)당신이 담은 순간이 뉴스입니다!", story),
            (f"담당자는 ‘{footer}’라는 표기를 예로 들었다.", f"담당자는 ‘{footer}’라는 표기를 예로 들었다."),
            ("제보 계정은 jebo23한채희", "제보 계정은 jebo23한채희"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(clean_common_text(raw), expected)

    def test_reporter_signatures_with_parenthesized_addresses(self):
        body = "주민 신청은 다음 주에 시작한다."
        for suffix in [
            "\n김가람(reporter@example.org)",
            " 김가람(reporter@example.org)",
            "\n김가람(reporter@example.org)\n이보람(editor@example.net)",
        ]:
            with self.subTest(suffix=suffix):
                self.assertEqual(clean_common_text(body + suffix), body)

    def test_player_boundaries_when_html_elements_have_no_line_breaks(self):
        player = (
            "브라우저가 video 태그를 지원하지 않습니다.죄송하지만 다른 브라우저를 사용하여 주십시오."
            "브라우저가 오디오 태그를 지원하지 않습니다.닫기"
        )
        first, last = "자막을 공개했다.", "대본도 제공한다."
        for raw, expected in [
            (f"{first} {player} {last}", f"{first} {last}"),
            (f"입력 2026-01-26 17:42:49 {player} {last}", last),
            ("기사 읽어주기 서비스는 크롬기반의 브라우저에서만 사용하실 수 있습니다.", ""),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(clean_common_text(raw), expected)

    def test_newsroom_footers_split_or_flattened(self):
        body = "시민이 보내온 영상으로 당시 상황을 확인했다."
        footers = [
            ["연합뉴스TV 기사문의 및 제보 : 카톡/라인 jebo23", "김가람(reporter@example.org)",
             "당신이 담은 순간이 뉴스입니다!", "jebo23", "라인 앱에서 'jebo23' 친구 추가",
             "jebo23@yna.co.kr", "ⓒ연합뉴스TV, 무단 전재-재배포, AI 학습 및 활용 금지"],
            ["연합뉴스TV 제보:02-398-4409, yjebo@yna.co.kr", "(끝)"],
            ["MBC 뉴스는 24시간 여러분의 제보를 기다립니다.", "▷ 전화 02-784-4000",
             "▷ 이메일 mbcjebo@mbc.co.kr", "▷ 카카오톡 @mbc제보"],
            ["YTN 김가람 (reporter@example.org)", "※ '당신의 제보가 뉴스가 됩니다'",
             "[카카오톡] YTN 검색해 채널 추가", "[전화] 02-398-8585", "[메일] social@ytn.co.kr",
             "[저작권자(c) YTN 무단전재, 재배포 및 AI 데이터 활용 금지]"],
            ["Copyright Ⓒ SBS. All rights reserved.", "무단 전재, 재배포 및 AI학습 이용 금지"],
        ]
        for footer in footers:
            for separator in ("\n", " "):
                with self.subTest(footer=footer[0], separator=separator):
                    self.assertEqual(clean_common_text(separator.join([body, *footer])), body)

    def test_preserves_browser_reporting_quoted_slogans_and_contact_details(self):
        for line in [
            "일부 브라우저가 video 태그를 지원하지 않습니다.",
            "화면에는 “브라우저가 오디오 태그를 지원하지 않습니다.”라고 표시됐다.",
            "공모전은 ‘당신이 담은 순간이 뉴스입니다!’를 주제로 삼았다.",
            "김가람(reporter@example.org)은 주민에게 의견을 보냈다.",
            "담당자는 김가람(reporter@example.org)이다.",
            "닫기 버튼의 위치가 바뀌었다.",
            "그는 “경고가 떴다. 브라우저가 video 태그를 지원하지 않습니다. 안내는 여기까지였다.”라고 말했다.",
            "신고처는 카카오톡 @mbc제보와 이메일 help@example.org라고 설명했다.",
            "공개 질의 담당자 김가람(reporter@example.org)",
            "취재진은 [전화] 02-398-8585로 연락했다.",
        ]:
            with self.subTest(line=line):
                self.assertEqual(clean_common_text(line), line)


if __name__ == "__main__":
    unittest.main()
