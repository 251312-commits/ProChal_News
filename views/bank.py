"""Royal-purple parchment bank screen for the Streamlit game."""

from textwrap import dedent
from pathlib import Path

import streamlit as st

from modules.db_handler import init_gspread
from modules.ui_components import change_page, load_local_image_as_base64

MAX_LOAN = 10_000
INTEREST_RATE = 0.20
UNIT = 1_000


def _sync_balances(user_data, coins: int, loan: int) -> None:
    """Write both balances together before updating the displayed session."""
    worksheet = init_gspread()
    student_id = str(user_data.get("학번", "")).strip()
    if not student_id:
        raise ValueError("학번을 찾을 수 없습니다.")

    cell = worksheet.find(student_id)
    if cell is None:
        raise LookupError("구글 시트에서 사용자 행을 찾을 수 없습니다.")

    # Existing schema: column C = coins; column D = loan balance.
    worksheet.update(
        range_name=f"C{cell.row}:D{cell.row}",
        values=[[coins, loan]],
    )


def _apply_transaction(user_data, coins: int, loan: int) -> bool:
    try:
        _sync_balances(user_data, coins, loan)
    except Exception as exc:
        st.error(f"거래를 저장하지 못했습니다. 다시 시도하세요. ({exc})")
        return False

    st.session_state.current_user_data["코인"] = coins
    st.session_state.current_user_data["대출금"] = loan
    return True


def _clamp_amount(key: str, limit: int, default: int) -> int:
    """Keep slider state valid when the user's balance changes."""
    if limit < UNIT:
        return 0
    existing = st.session_state.get(key, default)
    try:
        existing = int(existing)
    except (TypeError, ValueError):
        existing = default
    existing = max(UNIT, min(limit, (existing // UNIT) * UNIT))
    st.session_state[key] = existing
    return existing


def _amount_selector(label: str, key: str, limit: int, default: int) -> int:
    """Stepped +/- controls linked to a native, mobile-friendly slider."""
    chosen = _clamp_amount(key, limit, default)
    st.markdown(f'<div class="bank-amount-label">{label}</div>', unsafe_allow_html=True)

    minus_col, amount_col, plus_col = st.columns([1, 4.2, 1], gap="small")
    with minus_col:
        if st.button("−", key=f"{key}_minus", use_container_width=True,
                     disabled=chosen <= UNIT):
            chosen = max(UNIT, chosen - UNIT)
            st.session_state[key] = chosen
    with plus_col:
        if st.button("+", key=f"{key}_plus", use_container_width=True,
                     disabled=chosen >= limit):
            chosen = min(limit, chosen + UNIT)
            st.session_state[key] = chosen
    with amount_col:
        st.markdown(
            f'<div class="bank-amount-value">{st.session_state[key]:,} C</div>',
            unsafe_allow_html=True,
        )

    value = st.slider(
        label,
        min_value=UNIT,
        max_value=limit,
        step=UNIT,
        key=key,
        label_visibility="collapsed",
    )
    st.markdown(
        f'<div class="bank-range-labels"><span>{UNIT:,} C</span>'
        f'<span>{limit:,} C</span></div>',
        unsafe_allow_html=True,
    )
    return value


def _summary(coins: int, loan: int, available: int) -> None:
    st.markdown(
        dedent(f"""
        <div class="bank-summary">
          <div class="bank-summary-grid">
            <div class="bank-summary-item">
              <div class="bank-summary-icon">🪙</div>
              <div class="bank-summary-label">보유 코인</div>
              <div class="bank-summary-number">{coins:,} C</div>
            </div>
            <div class="bank-summary-item">
              <div class="bank-summary-icon">♜</div>
              <div class="bank-summary-label">대출 잔액</div>
              <div class="bank-summary-number">{loan:,} C</div>
            </div>
            <div class="bank-summary-item">
              <div class="bank-summary-icon">✚</div>
              <div class="bank-summary-label">추가 대출 가능액</div>
              <div class="bank-summary-number bank-gold">{available:,} C</div>
            </div>
          </div>
          <div class="bank-summary-note">
            <span class="bank-info-symbol">ⓘ</span>
            대출 잔액에 대해 턴마다 <strong>20%</strong>의 이자가
            복리로 추가됩니다.
          </div>
        </div>
        """),
        unsafe_allow_html=True,
    )


BANK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Noto+Sans+KR:wght@400;500;600;700;800;900&display=swap');

/* Scope the new app backdrop to the bank route only. */
.stApp:has(.st-key-bank-page) {
  background:
    radial-gradient(ellipse at 52% 12%, rgba(126,32,181,.36) 0%, transparent 45%),
    radial-gradient(ellipse at 17% 72%, rgba(167,52,171,.19) 0%, transparent 47%),
    radial-gradient(ellipse at 85% 90%, rgba(86,20,144,.27) 0%, transparent 44%),
    #10061c !important;
  color: #fdf7ff;
}
.stApp:has(.st-key-bank-page) .block-container {
  max-width: 710px !important;
  padding-top: .8rem !important;
  padding-bottom: 2rem !important;
}
.st-key-bank-page {
  max-width: 610px;
  margin: 0 auto;
  font-family: 'Noto Sans KR', sans-serif;
}
.st-key-bank-page .stMarkdown p { margin: 0; }

/* Navigation and wallet */
.st-key-bank-back button {
  width: 43px !important;
  min-height: 48px !important;
  padding: 0 !important;
  font-size: 27px !important;
  color: #f5c9ff !important;
  background: transparent !important;
  box-shadow: none !important;
  border: 0 !important;
  border-radius: 50% !important;
}
.st-key-bank-back button:hover { color: #ffffff !important; }
.bank-wallet {
  display:flex;
  align-items:center;
  justify-content:flex-end;
  gap:9px;
  width:max-content;
  margin-left:auto;
  border:1px solid #c35cee;
  border-radius:35px;
  padding:5px 7px 5px 7px;
  background:linear-gradient(135deg,#370b51 0%,#160821 100%);
  box-shadow:0 0 12px #ba40da65,inset 0 0 11px #7f36a65e;
  color:#fff9f7;
  font-size:clamp(15px,3.7vw,21px);
  font-weight:800;
  white-space:nowrap;
}
.bank-wallet-coin {
  display:grid;
  place-items:center;
  width:34px;height:34px;
  border-radius:50%;
  background:radial-gradient(circle at 30% 20%,#ffeb8f,#ffae29 67%,#b96a0a);
  color:#fff4c9;
  border:3px double #ffe59a;
  box-shadow:0 2px 6px #0009;
  font-size:20px;
}
.bank-wallet-plus {
  display:grid;place-items:center;
  width:31px;height:31px;border-radius:50%;
  background:linear-gradient(145deg,#8e31d8,#4b116f);
  border:1px solid #df76ff;
  box-shadow:inset 0 0 7px #f4a5ff79;
  font-size:24px;line-height:1;
  margin-left:4px;
}

/* Neon bank architecture, headline and floating coins */
.bank-heading {
  position:relative;
  padding:4px 0 28px;
  margin-top:-3px;
  text-align:center;
  isolation:isolate;
}
.bank-heading::before,.bank-heading::after {
  content:'♛';position:absolute;z-index:-1;
  color:#d6a2ff;border-radius:50%;
  background:radial-gradient(circle at 32% 25%,#b881ff,#5c168f 55%,#e3aa64 58%,#723d92 66%,#3b1455 73%);
  border:2px solid #cc73ff;
  width:38px;height:38px;display:grid;place-items:center;
  box-shadow:0 0 20px #ad4be9;transform:rotate(-23deg);
  top:122px;left:7%;
}
.bank-heading::after {top:70px;left:auto;right:5%;transform:rotate(24deg) scale(.82);}
.bank-temple {
  width:210px;
  margin:0 auto 4px;
  height:90px;
  position:relative;
  filter:drop-shadow(0 0 13px rgba(216,84,253,.69));
}
.bank-temple svg {width:100%;height:100%;display:block;}
.bank-temple-label {
  position:absolute;top:43px;left:0;right:0;
  color:#ffd8a1;
  font:700 25px 'Cinzel', Georgia,serif;
  letter-spacing:6px;
  text-shadow:0 0 10px #f589e4;
}
.bank-heading h1 {
  font-family:'Noto Sans KR',sans-serif;
  font-size:clamp(35px,8.5vw,49px);
  font-weight:900;
  line-height:1.2;
  color:#f9e9ff !important;
  text-shadow:0 3px 13px #b74fe7,0 0 28px #9e35d0 !important;
  margin:0 !important;
}
.bank-heading-sub {
  color:#e7c9ec;
  font-size:clamp(14px,3.6vw,20px);
  font-weight:600;
  letter-spacing:-.04em;
  margin-top:6px;
}

/* Layered rose parchment, as an actual widget container */
.st-key-bank-paper {
  position:relative;
  margin-top:11px;
  padding:32px clamp(13px,4.2vw,35px) 26px;
  isolation:isolate;
  color:#392035;
  background:
    radial-gradient(ellipse at 46% 48%,rgba(255,249,239,.82),transparent 72%),
    repeating-linear-gradient(112deg,transparent 0 6px,rgba(106,32,80,.025) 7px 8px),
    linear-gradient(145deg,#e1b8c5,#f3d5d8 30%,#ebc4d1 78%,#c994b5 100%);
  border:1px solid #f6d2e9;
  border-radius:13px 15px 15px 12px;
  box-shadow:
    0 0 0 3px #55245655,
    8px 13px 0 -3px #bd91b6,
    -7px 24px 0 -5px #bb8ea8,
    0 30px 44px #08020ce0,
    inset 0 0 28px #a66a9e76;
}
.st-key-bank-paper::before {
  content:'';
  position:absolute;
  inset:13px;
  border:1px solid rgba(150,83,111,.55);
  border-radius:6px;
  pointer-events:none;
  z-index:-1;
}
.st-key-bank-paper::after {
  content:'❦';
  position:absolute;
  right:21px;bottom:15px;
  color:#b77f97a0;font-size:34px;
  pointer-events:none;
}
.bank-wax {
  position:absolute;
  z-index:2;
  top:-30px;left:calc(50% - 28px);
  width:56px;height:56px;border-radius:46% 54% 49% 51%;
  display:grid;place-items:center;
  color:#ffd7d3;font-size:30px;
  background:radial-gradient(circle at 32% 22%,#ec606d,#9a1b43 63%,#650b2d);
  border:5px double #f98f9b;
  box-shadow:0 4px 3px #421029a8,0 0 8px #a62c69,inset 0 0 9px #4d0927;
  transform:rotate(-13deg);
}
.bank-stamp {
  position:absolute;
  right:clamp(22px,6vw,54px);
  top:48px;
  color:#8b6086a6;
  width:66px;height:66px;
  border:3px double currentColor;
  border-radius:50%;
  transform:rotate(14deg);
  font:700 11px 'Cinzel',serif;
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  line-height:1.6;
  pointer-events:none;
}
.bank-stamp span {font-size:20px;}
.bank-doc-title {
  font-family:Georgia,'Noto Serif KR',serif;
  font-size:clamp(28px,7vw,39px);
  font-weight:800;
  line-height:1.15;
  text-align:center;
  color:#36232e;
  text-shadow:1px 2px 0 #ffffff8a;
  padding-top:12px;
}
.bank-doc-sub {
  color:#876477;
  font:700 11px 'Cinzel',serif;
  text-align:center;
  letter-spacing:3px;
  margin-top:4px;
  margin-bottom:21px;
}
.bank-terms {
  display:grid;grid-template-columns:1fr 1fr;
  border:1px solid #ba879a;
  border-radius:5px;
  overflow:hidden;
  color:#392b36;
  font-size:clamp(12px,3.2vw,15px);
  margin:0 7px 14px;
}
.bank-term-label, .bank-term-value {
  padding:10px 12px;
  border-bottom:1px solid #cda2b5;
  background:#ffffff16;
  display:flex;align-items:center;
  min-width:0;
}
.bank-terms > :nth-last-child(-n+2) {border-bottom:0;}
.bank-term-label {font-weight:700;gap:8px;border-right:1px solid #cda2b5;}
.bank-term-ico {color:#765471;font-size:17px;}
.bank-term-value {font-weight:900;justify-content:flex-end;white-space:nowrap;}
.bank-term-rate {color:#7e15b1;}
.bank-divider {
  display:flex;align-items:center;gap:10px;
  color:#ac8196;
  margin:5px 5px 14px;
}
.bank-divider::before,.bank-divider::after {
  content:'';height:1px;flex:1;background:linear-gradient(90deg,transparent,#b7869c);
}
.bank-divider::after {transform:rotate(180deg);}
.bank-divider span {font-size:20px;line-height:1;}

/* Compact borrow/repay navigation, nested within the paper */
.st-key-bank-paper [data-baseweb="tab-list"] {
  justify-content:center;gap:4px;
  background:#804c7450;
  padding:4px;border-radius:13px;
  margin-bottom:8px;
  border:1px solid #bd94ad;
}
.st-key-bank-paper button[data-baseweb="tab"] {
  flex:1;
  justify-content:center;
  border-radius:9px !important;
  color:#634365 !important;
  font-size:14px !important;
  font-weight:800 !important;
  min-height:37px !important;
}
.st-key-bank-paper button[data-baseweb="tab"][aria-selected="true"] {
  background:linear-gradient(125deg,#622188,#9c37d1);
  color:white !important;
  box-shadow:0 2px 9px #75349b63;
}
.st-key-bank-paper [data-baseweb="tab-highlight"] {display:none;}
.st-key-bank-paper [data-baseweb="tab-border"] {display:none;}
.st-key-bank-paper [data-testid="stTabContent"] {padding-top:5px;}
.bank-amount-label {
  text-align:center;
  color:#392936;
  font-size:clamp(19px,4.5vw,24px);
  font-weight:900;
  margin:8px 0 8px;
}
.bank-amount-value {
  height:55px;
  border-radius:11px;
  background:linear-gradient(110deg,#422249,#704275 60%,#44204c);
  box-shadow:inset 0 2px 8px #30133f74,0 2px 2px #fff9;
  display:flex;align-items:center;justify-content:center;
  color:#fff7ff;
  font-size:clamp(23px,6.7vw,37px);
  font-weight:900;
  line-height:1;
  white-space:nowrap;
  text-shadow:0 0 6px #fff4;
}
.st-key-bank-paper button[kind="secondary"] {
  border-radius:50% !important;
}
.st-key-bank-paper .st-key-bank_borrow_amount_minus button,
.st-key-bank-paper .st-key-bank_borrow_amount_plus button,
.st-key-bank-paper .st-key-bank_repay_amount_minus button,
.st-key-bank-paper .st-key-bank_repay_amount_plus button {
  height:55px !important;
  width:55px !important;
  min-height:55px !important;
  padding:0 !important;
  margin:0 auto;
  border-radius:50% !important;
  border:1.5px solid #bd65e7 !important;
  background:radial-gradient(circle at 30% 16%,#a453d0,#5c1682 64%,#351046) !important;
  color:#ffffff !important;
  box-shadow:0 4px 4px #33133c91,0 0 7px #c158de !important;
  font-size:32px !important;
  font-weight:400 !important;
}
.st-key-bank-paper button:disabled {opacity:.38 !important;}
.st-key-bank-paper [data-testid="stSlider"] {padding-top:5px;}
.st-key-bank-paper [data-testid="stSlider"] [data-baseweb="slider"] {margin:7px 6px 0;}
.st-key-bank-paper [data-testid="stSlider"] [role="slider"] {
  background:#faf4ff !important;
  border:4px solid #d066ff !important;
  box-shadow:0 0 13px #ac0bff,0 0 4px #fff !important;
  width:24px !important;height:24px !important;
}
.st-key-bank-paper [data-testid="stSlider"] [data-testid="stTickBarMin"],
.st-key-bank-paper [data-testid="stSlider"] [data-testid="stTickBarMax"] {display:none;}
.bank-range-labels {
  display:flex;justify-content:space-between;
  color:#4c3148;
  font-weight:800;
  font-size:clamp(12px,3vw,15px);
  margin:-2px 5px 15px;
}
.bank-summary {
  overflow:hidden;
  border-radius:16px;
  padding:17px 12px 13px;
  margin:13px 0 18px;
  background:linear-gradient(150deg,#372044,#190f29 67%,#421a51);
  border:1px solid #a44ad9;
  box-shadow:0 4px 12px #4d17529b,inset 0 0 13px #9c44bd49;
  color:#fbedff;
}
.bank-summary-grid {
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
}
.bank-summary-item {
  text-align:center;
  padding:0 5px 10px;
  min-width:0;
  border-right:1px solid #7c408665;
}
.bank-summary-item:last-child{border-right:0;}
.bank-summary-icon {font-size:25px;color:#e3abf2;line-height:1.1;height:32px;}
.bank-summary-label {font-size:clamp(11px,2.7vw,14px);font-weight:800;margin:3px 0 7px;}
.bank-summary-number {
  font-size:clamp(16px,4.1vw,25px);
  font-weight:900;
  color:white;
  white-space:nowrap;
}
.bank-summary-number.bank-gold {color:#ffc975;}
.bank-summary-note {
  display:flex;gap:9px;justify-content:center;align-items:center;
  border-top:1px solid #8e4a9f87;
  padding-top:13px;
  margin-top:3px;
  color:#d5b9e8;
  font-size:clamp(11px,2.9vw,14px);
  word-break:keep-all;
}
.bank-summary-note strong {color:#e08dff;}
.bank-info-symbol {color:#c870ef;font-size:18px;flex-shrink:0;}
.bank-estimate {
  color:#5d356a;
  font-size:13px;
  text-align:center;
  font-weight:700;
  margin:-7px 0 14px;
}
.bank-estimate strong {color:#78169f;}
.st-key-bank-paper .st-key-bank-borrow-submit button,
.st-key-bank-paper .st-key-bank-repay-submit button {
  min-height:66px !important;
  border-radius:45px !important;
  border:2px solid #f8bcef !important;
  background:linear-gradient(180deg,#b140e7 0%,#7f10d6 44%,#57058d 100%) !important;
  color:#fff !important;
  font-size:clamp(19px,5vw,26px) !important;
  font-weight:900 !important;
  text-shadow:0 2px 5px #37114c !important;
  box-shadow:
    0 0 12px #d33ff2,0 6px 0 #6c3269,
    inset 0 4px 9px #fff9 !important;
}
.st-key-bank-paper .st-key-bank-borrow-submit button:hover,
.st-key-bank-paper .st-key-bank-repay-submit button:hover {
  filter:brightness(1.12);
}
.bank-footnote {text-align:center;color:#d5a9e1;font-size:11px;margin-top:26px;}

@media(max-width:480px){
  .stApp:has(.st-key-bank-page) .block-container {padding-left:11px !important;padding-right:11px !important;}
  .bank-temple {width:174px;height:74px;}
  .bank-temple-label {top:35px;font-size:19px;}
  .bank-heading {padding-bottom:19px;}
  .bank-stamp {top:58px;width:48px;height:48px;font-size:9px;right:24px;}
  .bank-stamp span {font-size:14px;}
  .st-key-bank-paper {padding:31px 14px 19px;}
  .bank-terms {margin-left:2px;margin-right:2px;}
  .bank-term-label,.bank-term-value{padding:8px 7px;}
  .bank-doc-sub{margin-bottom:13px;}
  .bank-amount-value {height:50px;}
  .st-key-bank-paper .st-key-bank_borrow_amount_minus button,
  .st-key-bank-paper .st-key-bank_borrow_amount_plus button,
  .st-key-bank-paper .st-key-bank_repay_amount_minus button,
  .st-key-bank-paper .st-key-bank_repay_amount_plus button {
    width:45px !important;height:50px !important;min-height:50px !important;
  }
  .bank-summary {padding-left:7px;padding-right:7px;}
  .bank-summary-item {padding-left:2px;padding-right:2px;}
  .bank-summary-note {align-items:flex-start;}
}
@media(prefers-reduced-motion:reduce){
  .st-key-bank-page * {animation:none !important;transition:none !important;}
}
</style>
"""


BANK_TEMPLE = """
<div class="bank-heading">
  <div class="bank-temple" aria-hidden="true">
    <svg viewBox="0 0 220 92" role="presentation">
      <defs>
        <linearGradient id="roofGold" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="#f2b9ff"/>
          <stop offset=".5" stop-color="#8939bc"/>
          <stop offset="1" stop-color="#f7b5ec"/>
        </linearGradient>
      </defs>
      <path d="M9 35 L110 5 L211 35 L211 42 L110 13 L9 42 Z"
            fill="#230e36" stroke="url(#roofGold)" stroke-width="3"/>
      <path d="M17 43 H203 V51 H17 Z" fill="#3c164e"
            stroke="#e39be6" stroke-width="2"/>
      <path d="M30 53 V88 M51 53 V88 M169 53 V88 M190 53 V88"
            stroke="#7c3aa1" stroke-width="10"/>
      <path d="M30 53 V88 M51 53 V88 M169 53 V88 M190 53 V88"
            stroke="#e3a3db" stroke-width="2"/>
      <path d="M16 88 H204" stroke="#d66ff0" stroke-width="5"/>
      <path d="M100 26 L110 13 L120 26 L116 32 H104 Z"
            fill="#f5ca7b" stroke="#ffd8a0" stroke-width="2"/>
      <circle cx="110" cy="11" r="3" fill="#ffe59d"/>
    </svg>
    <div class="bank-temple-label">BANK</div>
  </div>
  <h1>은행 대출</h1>
  <div class="bank-heading-sub">지금 필요한 코인을 대출받으세요.</div>
</div>
"""


def _show_bank_legacy():
    if not st.session_state.get("current_user_data"):
        st.error("로그인 정보가 없습니다. 메인 화면으로 이동하세요.")
        if st.button("메인으로 돌아가기", key="bank-login-back"):
            change_page("main")
        return

    user_data = st.session_state.current_user_data
    current_coins = int(user_data.get("코인", 0))
    current_loan = int(user_data.get("대출금", 0))
    available_loan = max(0, MAX_LOAN - current_loan)
    max_borrow = (available_loan // UNIT) * UNIT
    max_repay = (min(current_coins, current_loan) // UNIT) * UNIT

    st.markdown(BANK_CSS, unsafe_allow_html=True)

    with st.container(key="bank-page"):
        back, spacer, wallet = st.columns([1, 1.2, 4.5], gap="small")
        with back:
            if st.button("❮", key="bank-back", help="메인 화면", use_container_width=True):
                change_page("main")
        with wallet:
            st.markdown(
                dedent(f"""
                <div class="bank-wallet" aria-label="보유 코인 {current_coins:,}">
                    <span class="bank-wallet-coin">＄</span>
                    <span>{current_coins:,} C</span>
                    <span class="bank-wallet-plus" aria-hidden="true">+</span>
                </div>
                """),
                unsafe_allow_html=True,
            )

        st.markdown(BANK_TEMPLE, unsafe_allow_html=True)

        with st.container(key="bank-paper"):
            st.markdown(
                dedent(f"""
                <div class="bank-wax" aria-hidden="true">♛</div>
                <div class="bank-stamp" aria-hidden="true"><span>♛</span>BANK</div>
                <div class="bank-doc-title">대출 신청서</div>
                <div class="bank-doc-sub">LOAN APPLICATION</div>
                <div class="bank-terms">
                    <div class="bank-term-label"><span class="bank-term-ico">♛</span> 대출 단위</div>
                    <div class="bank-term-value">{UNIT:,} C</div>
                    <div class="bank-term-label"><span class="bank-term-ico">％</span> 이자율</div>
                    <div class="bank-term-value bank-term-rate">턴당 20% (복리)</div>
                    <div class="bank-term-label"><span class="bank-term-ico">▤</span> 최대 대출 한도</div>
                    <div class="bank-term-value">{MAX_LOAN:,} C</div>
                </div>
                <div class="bank-divider"><span>❖</span></div>
                """),
                unsafe_allow_html=True,
            )

            borrow_tab, repay_tab = st.tabs(["대출 신청", "대출 상환"])

            with borrow_tab:
                if max_borrow < UNIT:
                    st.warning("현재 추가로 대출할 수 있는 금액이 없습니다.")
                else:
                    amount = _amount_selector(
                        "신청 금액", "bank_borrow_amount",
                        max_borrow, min(5_000, max_borrow),
                    )
                    _summary(current_coins, current_loan, available_loan)
                    st.markdown(
                        f'<div class="bank-estimate">신청 금액의 다음 턴 이자: '
                        f'<strong>+{int(amount * INTEREST_RATE):,} C</strong></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "🏛  대출 신청하기",
                        key="bank-borrow-submit",
                        type="primary",
                        use_container_width=True,
                    ):
                        if _apply_transaction(
                            user_data, current_coins + amount, current_loan + amount
                        ):
                            st.toast(f"{amount:,} C 대출이 완료되었습니다.")
                            st.rerun()

                if max_borrow < UNIT:
                    _summary(current_coins, current_loan, available_loan)

            with repay_tab:
                if current_loan <= 0:
                    st.success("상환할 대출금이 없습니다.")
                elif max_repay < UNIT:
                    st.warning(f"상환에는 최소 {UNIT:,} C가 필요합니다.")
                else:
                    amount = _amount_selector(
                        "상환 금액", "bank_repay_amount", max_repay, max_repay
                    )
                    _summary(current_coins, current_loan, available_loan)
                    st.markdown(
                        f'<div class="bank-estimate">상환 후 대출 잔액: '
                        f'<strong>{current_loan - amount:,} C</strong></div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "🏛  대출금 상환하기",
                        key="bank-repay-submit",
                        type="primary",
                        use_container_width=True,
                    ):
                        if _apply_transaction(
                            user_data, current_coins - amount, current_loan - amount
                        ):
                            st.toast(f"{amount:,} C 상환이 완료되었습니다.")
                            st.rerun()

                if current_loan <= 0 or max_repay < UNIT:
                    _summary(current_coins, current_loan, available_loan)

        st.markdown(
            '<div class="bank-footnote">ROYAL BANK · LOAN SERVICE</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Envelope-first bank UI.  The legacy screen remains above as a reference;
# the public entry points below reuse its tested sheet transaction functions.
# Assets are optional, so the bank remains functional before PNGs are deployed.
# ---------------------------------------------------------------------------

BANK_SCENE_CSS = """
<style>
.stApp:has(.st-key-bank-page) .block-container {
  max-width:740px !important;
  padding-top:.45rem !important;
}
.st-key-bank-page {max-width:670px !important;margin:0 auto}
.bank-scene-header {
  text-align:center;
  padding:0 0 15px;
  margin-top:-15px;
}
.bank-scene-temple {height:clamp(105px,23vw,200px);display:flex;align-items:center;justify-content:center}
.bank-scene-temple img {
  width:min(88%,425px);height:100%;object-fit:contain;
  filter:drop-shadow(0 0 16px #c351e475);
}
.bank-scene-logo-fallback {
  font:800 36px Georgia,serif;letter-spacing:8px;color:#ffcc96;
  text-shadow:0 0 22px #a631da;
}
.bank-scene-header h1 {
  color:#fff0ff !important;
  font-size:clamp(32px,7.7vw,53px) !important;
  font-weight:900 !important;
  margin:-5px 0 9px !important;
  line-height:1.15;
  text-shadow:0 0 24px #ac49d5 !important;
}
.bank-scene-header p {
  font-size:clamp(13px,3.4vw,20px);
  line-height:1.5;
  letter-spacing:-.03em;
  color:#ead5ef;
  margin:0;
}
.bank-scene-hero {
  height:clamp(248px,65vw,410px);
  position:relative;isolation:isolate;
  margin:0 auto 4px;
  max-width:620px;
}
.bank-scene-cushion {
  position:absolute;width:100%;height:auto;left:0;bottom:-6%;
  object-fit:contain;z-index:1;
  filter:drop-shadow(0 14px 18px #09010bb5);
}
.bank-scene-envelope {
  position:absolute;z-index:2;top:1%;left:5%;
  width:90%;height:auto;object-fit:contain;
  filter:drop-shadow(0 13px 14px #10041488);
  animation:bank-envelope-float 4.5s ease-in-out infinite;
}
.bank-scene-envelope-label {
  position:absolute;z-index:3;
  top:19%;left:18%;width:64%;
  text-align:center;pointer-events:none;
  color:#66352e;
  font-weight:850;
  text-shadow:0 1px 2px #ffddd1b0;
}
.bank-scene-envelope-label .crest {display:block;font-size:clamp(22px,6vw,35px);opacity:.68}
.bank-scene-envelope-label .title {display:block;font-size:clamp(23px,6vw,38px);line-height:1.25}
.bank-scene-envelope-label .eng {font:700 clamp(7px,1.4vw,11px) Georgia,serif;letter-spacing:3px}
.bank-scene-envelope-placeholder {
  position:absolute;inset:12% 5% 14%;
  border-radius:16px;background:linear-gradient(145deg,#e5abb9,#ffe0c9,#d9a1b6);
  display:grid;place-items:center;box-shadow:0 18px 35px #0009;
}
.bank-scene-envelope-placeholder span {color:#7b3d59;font-size:27px;font-weight:800}
.bank-scene-buttons {margin:5px 0 9px}
.st-key-bank-home-borrow button,
.st-key-bank-home-repay button {
  width:100% !important;
  min-height:clamp(53px,10vw,75px) !important;
  font-weight:900 !important;
  font-size:clamp(13px,3.5vw,20px) !important;
  white-space:nowrap;
  border-radius:33px !important;
}
.st-key-bank-home-borrow button {
  background:linear-gradient(180deg,#ab2cdf 0%,#7610cb 55%,#490873 100%) !important;
  border:2px solid #fd97fc !important;
  color:#fff !important;
  box-shadow:0 0 14px #dc38efae, inset 0 4px 8px #ffffff94 !important;
}
.st-key-bank-home-repay button {
  background:linear-gradient(135deg,#4c285e 0%,#25112e 100%) !important;
  border:1.5px solid #c675dd !important;
  box-shadow:0 3px 11px #a83ad45c,inset 0 0 13px #8240926c !important;
  color:#f5e7fb !important;
}
.bank-scene-benefits {
  display:grid;grid-template-columns:repeat(3,minmax(0,1fr));
  text-align:center;gap:0;margin:24px 0 8px;
  color:#f2e0fa;font-weight:800;
}
.bank-scene-benefit {min-width:0;padding:0 2px;border-right:1px solid #ad6bc289}
.bank-scene-benefit:last-child {border-right:none}
.bank-scene-benefit .ico {
  display:grid;place-items:center;
  width:42px;height:42px;margin:0 auto 9px;
  border:1px solid #cc91e6;border-radius:50%;
  background:#682e8336;color:#dfb0fa;font-size:23px;
}
.bank-scene-benefit .label {font-size:clamp(10px,2.5vw,14px);white-space:nowrap}
.st-key-bank-paper {
  margin-top:17px !important;
  padding:clamp(28px,6vw,46px) clamp(12px,4vw,33px) 42px !important;
}
.st-key-bank-paper::before,.st-key-bank-paper::after {display:none !important}
.bank-scene-paper-header {
  text-align:center;
  padding-top:27px;
  margin-bottom:16px;
  position:relative;
  z-index:1;
}
.bank-scene-paper-header h2 {
  color:#3f2938 !important;
  font-size:clamp(29px,6.5vw,41px);
  font-weight:900;
  margin:0 0 5px !important;
  text-shadow:0 1px 0 #ffffff9c !important;
}
.bank-scene-paper-header .en {
  font:700 10px Georgia,serif;letter-spacing:3px;color:#8c637a;
}
.bank-scene-paper-wax {
  pointer-events:none;
  position:absolute;left:50%;top:-24px;transform:translateX(-50%);
  width:clamp(58px,10vw,76px);height:auto;
  filter:drop-shadow(1px 4px 5px #72123f6e);
  z-index:4;
}
.bank-scene-paper-stamp {
  pointer-events:none;
  position:absolute;right:-4%;bottom:-23px;
  width:clamp(76px,17vw,128px);height:auto;
  transform:rotate(-9deg);z-index:4;
  filter:drop-shadow(0 5px 5px #35122d6e);
}
.bank-scene-paper-lower {padding-bottom:16px}
.bank-scene-paper-subtext {
  text-align:center;font-size:12px;font-weight:700;color:#674766;margin-bottom:9px;
}
.bank-scene-transition {
  position:fixed;inset:0;z-index:99999;
  display:flex;align-items:center;justify-content:center;
  pointer-events:none;overflow:hidden;
  background:#1d0827eb;
  animation:bank-transition-hide 1.45s ease forwards;
}
.bank-scene-transition img {position:absolute;max-width:min(85vw,560px);height:auto}
.bank-scene-transition .closed {
  animation:bank-closed-exit 1.45s ease both;
}
.bank-scene-transition .opened {
  opacity:0;animation:bank-open-enter 1.45s ease both;
}
.bank-scene-transition .sheet {
  width:min(75vw,490px);
  opacity:0;animation:bank-paper-exit 1.45s ease both;
}
@keyframes bank-envelope-float {
  0%,100%{transform:translateY(0)}
  50%{transform:translateY(-6px)}
}
@keyframes bank-transition-hide {
  0%,60%{opacity:1;visibility:visible}
  100%{opacity:0;visibility:hidden}
}
@keyframes bank-closed-exit {
  0%,24%{opacity:1;transform:translateY(0) scale(1)}
  40%,100%{opacity:0;transform:translateY(8px) scale(.95)}
}
@keyframes bank-open-enter {
  0%,20%{opacity:0;transform:scale(.94)}
  35%,58%{opacity:1;transform:scale(1)}
  78%,100%{opacity:0;transform:scale(1.03)}
}
@keyframes bank-paper-exit {
  0%,42%{opacity:0;transform:translateY(100px) scale(.65)}
  58%{opacity:1}
  95%,100%{opacity:0;transform:translateY(-30px) scale(1.04)}
}
@media(max-width:480px){
  .bank-scene-header {margin-top:-13px}
  .bank-scene-temple {height:115px}
  .bank-scene-header p{font-size:14px}
  .bank-scene-hero {height:clamp(225px,68vw,300px)}
  .bank-scene-envelope-label {top:19%}
  .bank-scene-benefits{margin-top:16px}
  .bank-scene-benefit .ico{width:36px;height:36px;font-size:21px}
  .st-key-bank-paper{padding:36px 12px 29px !important}
  .bank-scene-paper-header {padding-top:19px}
  .bank-scene-paper-stamp{right:-5%;bottom:-15px}
}
@media(prefers-reduced-motion:reduce){
  .bank-scene-transition {display:none !important}
  .bank-scene-envelope {animation:none !important}
}
</style>
"""


BANK_SCENE_IMAGE_CSS = """
<style>
/* Layered transparent illustrations from the supplied bank UI artwork. */
.stApp:has(.st-key-bank-page) {
  background:
    radial-gradient(ellipse at 49% 13%, rgba(152,40,200,.33) 0%, transparent 48%),
    radial-gradient(ellipse at 10% 68%, rgba(133,34,141,.26) 0%, transparent 45%),
    radial-gradient(ellipse at 85% 85%, rgba(89,16,139,.38) 0%, transparent 52%),
    #11051d !important;
}
.stApp:has(.st-key-bank-page) .block-container {
  max-width:680px !important;
  padding-bottom:1.3rem !important;
}
.bank-scene-temple img { width:min(92%,470px); }
.bank-scene-hero { height:clamp(250px,59vw,370px); }
.bank-scene-cushion {
  width:100%;left:0;bottom:-3%;
  filter:drop-shadow(0 18px 16px #13041d99);
}
.bank-scene-envelope {
  width:86%;left:7%;top:2%;
  filter:drop-shadow(0 10px 16px #19061b9c);
}
.bank-scene-envelope-label { top:16%; }
.bank-scene-envelope-label .crest { font-size:clamp(22px,5vw,31px); }
.bank-scene-envelope-label .title { font-size:clamp(21px,5.8vw,35px); }
.bank-scene-benefits { margin-top:22px; }
.st-key-bank-paper {
  overflow:visible;
  background-size:100% 100% !important;
  padding-top:39px !important;
  padding-bottom:38px !important;
}
.bank-scene-paper-stamp {right:-2%;bottom:-13px;max-width:120px;}
.bank-scene-paper-wax {top:-28px;}
.bank-scene-paper-header {padding-top:20px;}
.bank-scene-transition .closed {width:min(78vw,530px);}
.bank-scene-transition .opened {width:min(78vw,500px);}
.bank-scene-transition .sheet {width:min(74vw,410px);}
@media(max-width:480px) {
  .stApp:has(.st-key-bank-page) .block-container {
    padding-left:10px !important;padding-right:10px !important;
  }
  .bank-scene-header {padding-bottom:8px;}
  .bank-scene-temple {height:101px;}
  .bank-scene-hero {height:clamp(220px,59vw,255px);}
  .bank-scene-envelope-label {top:19%;}
  .bank-scene-envelope-label .title {font-size:clamp(20px,5.4vw,26px);}
  .bank-scene-benefits {margin-top:13px;}
  .st-key-bank-paper {padding:31px 12px 28px !important;}
  .bank-scene-paper-stamp {width:80px;right:0;bottom:-7px;}
  .bank-scene-paper-header {padding-top:12px;margin-bottom:12px;}
  .bank-terms {margin-bottom:8px;}
  .bank-summary {margin-top:10px;margin-bottom:12px;}
  .bank-summary-note {font-size:11px;}
}
@media(prefers-reduced-motion:reduce) {
  .bank-scene-envelope {animation:none !important;}
  .bank-scene-transition {display:none !important;}
}
</style>
"""

def _bank_asset(filename: str) -> str:
    """Resolve a bank illustration, preferring the smaller transparent AVIF."""
    asset_dir = Path(__file__).resolve().parents[1] / "assets" / "bank"
    stem = Path(filename).stem
    for candidate in (asset_dir / f"{stem}.avif", asset_dir / filename):
        if candidate.is_file():
            return load_local_image_as_base64(str(candidate))
    return ""


def _bank_img(filename: str, class_name: str) -> str:
    src = _bank_asset(filename)
    return f'<img class="{class_name}" src="{src}" alt="">' if src else ""


def _bank_render_styles() -> None:
    st.markdown(BANK_CSS, unsafe_allow_html=True)
    st.markdown(BANK_SCENE_CSS, unsafe_allow_html=True)
    root = Path(__file__).resolve().parents[1]
    betting_bg = root / "assets" / "bet_background.jpg"
    if betting_bg.is_file():
        background_uri = load_local_image_as_base64(str(betting_bg))
        st.markdown(
            f'<style>.stApp:has(.st-key-bank-page) {{'
            f'background-image:linear-gradient(180deg,#11051b80,#12031eab),'
            f'url("{background_uri}") !important;'
            f'background-size:cover !important;'
            f'background-position:center top !important;'
            f'background-attachment:fixed !important;'
            f'}}</style>',
            unsafe_allow_html=True,
        )

    paper_uri = _bank_asset("bank_paper.png")
    if paper_uri:
        st.markdown(
            f'<style>.st-key-bank-paper {{'
            f'background-image:url("{paper_uri}") !important;'
            f'background-size:100% 100% !important;'
            f'background-repeat:no-repeat !important;'
            f'background-color:transparent !important;'
            f'border:0 !important;border-radius:0 !important;'
            f'box-shadow:0 24px 35px #08020c66 !important;'
            f'}}</style>',
            unsafe_allow_html=True,
        )

    st.markdown(BANK_SCENE_IMAGE_CSS, unsafe_allow_html=True)


def _bank_title(view: str) -> None:
    temple = _bank_img("bank_temple.png", "bank-scene-temple-image")
    if not temple:
        temple = '<div class="bank-scene-logo-fallback">♛ BANK</div>'
    subtitle = (
        "필요한 만큼 코인을 대출받고,<br>원하는 시점에 상환하세요."
        if view == "home" else
        "지금 필요한 코인을 대출받으세요."
        if view == "loan" else
        "보유한 코인으로 대출 잔액을 상환하세요."
    )
    st.markdown(
        f'<div class="bank-scene-header">'
        f'<div class="bank-scene-temple">{temple}</div>'
        f'<h1>은행 대출</h1><p>{subtitle}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _bank_home() -> None:
    cushion = _bank_img("bank_cushion.png", "bank-scene-cushion")
    envelope = _bank_img("bank_envelope_closed.png", "bank-scene-envelope")
    if not envelope:
        envelope = (
            '<div class="bank-scene-envelope-placeholder">'
            '<span>✉ 대출 신청서</span></div>'
        )
    label = (
        '<div class="bank-scene-envelope-label">'
        '<span class="crest">♜</span>'
        '<span class="title">대출 신청서</span>'
        '<span class="eng">LOAN APPLICATION</span>'
        '</div>'
    )
    st.markdown(
        f'<div class="bank-scene-hero">{cushion}{envelope}{label}</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="bank-scene-buttons"></div>', unsafe_allow_html=True)
    borrow_col, repay_col = st.columns(2, gap="small")
    with borrow_col:
        if st.button("🪙  대출 신청하기", key="bank-home-borrow", use_container_width=True):
            st.session_state.bank_view = "loan"
            st.session_state.bank_open_transition = True
            st.rerun()
    with repay_col:
        if st.button("▣  대출 상환하기", key="bank-home-repay", use_container_width=True):
            st.session_state.bank_view = "repay"
            st.session_state.bank_open_transition = True
            st.rerun()

    st.markdown(
        '<div class="bank-scene-benefits">'
        '<div class="bank-scene-benefit"><span class="ico">%</span>'
        '<span class="label">합리적인 이자율</span></div>'
        '<div class="bank-scene-benefit"><span class="ico">▤</span>'
        '<span class="label">유연한 상환</span></div>'
        '<div class="bank-scene-benefit"><span class="ico">✓</span>'
        '<span class="label">안전한 거래</span></div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _bank_transition() -> None:
    """One-shot CSS visual on entering loan or repay, not on slider reruns."""
    if not st.session_state.pop("bank_open_transition", False):
        return
    closed = _bank_img("bank_envelope_closed.png", "closed")
    opened = _bank_img("bank_envelope_open.png", "opened")
    sheet = _bank_img("bank_paper.png", "sheet")
    if not closed or not opened or not sheet:
        return
    st.markdown(
        f'<div class="bank-scene-transition" aria-hidden="true">'
        f'{closed}{opened}{sheet}</div>',
        unsafe_allow_html=True,
    )


def _bank_paper_title(view: str) -> None:
    seal = _bank_img("bank_wax_seal.png", "bank-scene-paper-wax")
    stamp = _bank_img("bank_stamp.png", "bank-scene-paper-stamp")
    is_loan = view == "loan"
    name = "대출 신청서" if is_loan else "대출 상환서"
    en = "LOAN APPLICATION" if is_loan else "LOAN REPAYMENT"
    st.markdown(
        f'{seal}{stamp}<div class="bank-scene-paper-header">'
        f'<h2>{name}</h2><div class="en">{en}</div></div>',
        unsafe_allow_html=True,
    )


def _bank_document(view: str, coins: int, loan: int) -> None:
    available = max(0, MAX_LOAN - loan)
    max_borrow = (available // UNIT) * UNIT
    max_repay = (min(coins, loan) // UNIT) * UNIT
    is_loan = view == "loan"
    with st.container(key="bank-paper"):
        _bank_paper_title(view)
        if is_loan:
            st.markdown(
                f'<div class="bank-terms">'
                f'<div class="bank-term-label"><span class="bank-term-ico">♛</span>대출 단위</div>'
                f'<div class="bank-term-value">{UNIT:,} C</div>'
                f'<div class="bank-term-label"><span class="bank-term-ico">％</span>이자율</div>'
                f'<div class="bank-term-value bank-term-rate">턴당 20% (복리)</div>'
                f'<div class="bank-term-label"><span class="bank-term-ico">▤</span>최대 대출 한도</div>'
                f'<div class="bank-term-value">{MAX_LOAN:,} C</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="bank-terms">'
                f'<div class="bank-term-label"><span class="bank-term-ico">♛</span>상환 단위</div>'
                f'<div class="bank-term-value">{UNIT:,} C</div>'
                f'<div class="bank-term-label"><span class="bank-term-ico">▤</span>대출 잔액</div>'
                f'<div class="bank-term-value">{loan:,} C</div>'
                f'<div class="bank-term-label"><span class="bank-term-ico">◉</span>보유 코인</div>'
                f'<div class="bank-term-value">{coins:,} C</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="bank-divider"><span>❖</span></div>', unsafe_allow_html=True)

        if is_loan:
            if max_borrow >= UNIT:
                amount = _amount_selector(
                    "신청 금액", "bank_borrow_amount", max_borrow,
                    min(5_000, max_borrow),
                )
            else:
                st.warning("현재 추가로 대출할 수 있는 금액이 없습니다.")
                amount = 0
        else:
            if loan <= 0:
                st.success("상환할 대출금이 없습니다.")
                amount = 0
            elif max_repay < UNIT:
                st.warning(f"상환에는 최소 {UNIT:,} C가 필요합니다.")
                amount = 0
            else:
                amount = _amount_selector(
                    "상환 금액", "bank_repay_amount", max_repay, max_repay,
                )

        _summary(coins, loan, available)
        if amount:
            if is_loan:
                st.markdown(
                    f'<div class="bank-estimate">신청 금액의 다음 턴 이자: '
                    f'<strong>+{int(amount * INTEREST_RATE):,} C</strong></div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "🏛  대출 신청하기", key="bank-borrow-submit",
                    type="primary", use_container_width=True,
                ):
                    if _apply_transaction(
                        st.session_state.current_user_data,
                        coins + amount, loan + amount,
                    ):
                        st.toast(f"{amount:,} C 대출이 완료되었습니다.")
                        st.rerun()
            else:
                st.markdown(
                    f'<div class="bank-estimate">상환 후 대출 잔액: '
                    f'<strong>{loan - amount:,} C</strong></div>',
                    unsafe_allow_html=True,
                )
                if st.button(
                    "🏛  대출금 상환하기", key="bank-repay-submit",
                    type="primary", use_container_width=True,
                ):
                    if _apply_transaction(
                        st.session_state.current_user_data,
                        coins - amount, loan - amount,
                    ):
                        st.toast(f"{amount:,} C 상환이 완료되었습니다.")
                        st.rerun()
        st.markdown('<div class="bank-scene-paper-lower"></div>', unsafe_allow_html=True)


def _bank_draw(view: str) -> None:
    user_data = st.session_state.get("current_user_data")
    if not user_data:
        st.error("로그인 정보가 없습니다. 메인 화면으로 이동하세요.")
        if st.button("메인으로 돌아가기", key="bank-login-back"):
            change_page("main")
        return

    coins = int(user_data.get("코인", 0))
    loan = int(user_data.get("대출금", 0))
    _bank_render_styles()
    with st.container(key="bank-page"):
        back, spacer, wallet = st.columns([1, 1, 4.5], gap="small")
        with back:
            if st.button("❮", key="bank-back", help="뒤로 가기", use_container_width=True):
                if view == "home":
                    st.session_state.bank_view = "home"
                    change_page("main")
                else:
                    st.session_state.bank_view = "home"
                    st.rerun()
        with wallet:
            st.markdown(
                f'<div class="bank-wallet" aria-label="보유 코인 {coins:,}">'
                f'<span class="bank-wallet-coin">＄</span>'
                f'<span>{coins:,} C</span>'
                f'<span class="bank-wallet-plus" aria-hidden="true">+</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        _bank_title(view)
        if view == "home":
            _bank_home()
        else:
            _bank_transition()
            _bank_document(view, coins, loan)


def show_bank_loan() -> None:
    """Loan application screen (same sheet persistence as the old bank)."""
    _bank_draw("loan")


def show_bank_repay() -> None:
    """Separate loan repayment screen."""
    _bank_draw("repay")


def show_bank() -> None:
    """Bank landing screen + app-internal loan/repay navigation."""
    view = st.session_state.get("bank_view", "home")
    if view == "loan":
        show_bank_loan()
    elif view == "repay":
        show_bank_repay()
    else:
        _bank_draw("home")
