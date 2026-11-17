"use strict";

/* Persistent in the parent document: Streamlit reruns the Python script,
   but the overlay remains visible until the new page/fragment has rendered. */
(() => {
  const host = window.parent;
  if (host === window) return;
  const doc = host.document;
  const frame = window.frameElement;
  if (frame) {
    frame.setAttribute("aria-hidden", "true");
    frame.style.cssText += ";position:absolute!important;width:0!important;height:0!important;border:0!important;pointer-events:none!important;";
  }

  const KEY = "__pcOperationLoadingV1";
  if (host[KEY]) {
    if (host[KEY].version !== 2) {
      // Legacy listener was installed without a removable handler.
      // Reset the page once rather than keeping the immediate-click overlay.
      host[KEY].clear();
      host.location.reload();
      return;
    }
    host[KEY].complete(pcRunToken, pcEnabled);
    return;
  }

  const STYLE_ID = "pc-operation-loading-style";
  const OVERLAY_ID = "pc-operation-loading";
  const SHOW_DELAY_MS = 200;
  let enabled = Boolean(pcEnabled);
  let active = false, showTimer = null, longWaitTimer = null, lastRunToken = null;

  function ensureStyle() {
    if (doc.getElementById(STYLE_ID)) return;
    const style = doc.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      #pc-operation-loading {
        position:fixed; inset:0; z-index:2147483647; display:grid;
        place-items:center; background:rgba(5,0,13,.86); padding:20px;
        -webkit-backdrop-filter:blur(8px); backdrop-filter:blur(8px);
        color:#fff; font-family:system-ui,-apple-system,sans-serif;
      }
      body:has(#pc-sim-load) #pc-operation-loading {
        visibility:hidden!important; pointer-events:none!important;
      }
      #pc-operation-loading .pc-loading-card {
        width:min(100%,360px); padding:30px 25px 26px;
        background:linear-gradient(155deg,#210d38,#0b0618 85%);
        border:1px solid #b968ee; border-radius:16px;
        box-shadow:0 0 30px #9400d466,inset 0 0 15px #8a2be222;
        text-align:center;
      }
      #pc-operation-loading .pc-loading-symbol {
        width:62px; height:62px; margin:0 auto 16px; border-radius:50%;
        border:4px solid #ffffff26; border-top-color:#e0a5ff;
        border-right-color:#f3c967; animation:pc-operation-spin .85s linear infinite;
      }
      #pc-operation-loading .pc-loading-title {
        margin:0 0 8px; font-size:1.32rem; font-weight:800; line-height:1.4;
      }
      #pc-operation-loading .pc-loading-description {
        margin:0; color:#e3cdec; font-size:.9rem; line-height:1.6;
      }
      #pc-operation-loading .pc-loading-bar {
        height:5px; overflow:hidden; border-radius:999px;
        margin:22px 0 13px; background:#ffffff24;
      }
      #pc-operation-loading .pc-loading-bar::before {
        content:""; display:block; height:100%; width:35%; border-radius:inherit;
        background:linear-gradient(90deg,#b44cff,#f8cb67);
        animation:pc-operation-scan 1.2s ease-in-out infinite alternate;
      }
      #pc-operation-loading .pc-loading-caption {
        color:#c59dd7; font-size:.74rem; letter-spacing:.12em; font-weight:700;
      }
      #pc-operation-loading .pc-loading-long {
        margin:16px 0 0; font-size:.82rem; line-height:1.5; color:#f1c9a4;
      }
      #pc-operation-loading .pc-loading-close {
        margin-top:14px; padding:9px 18px; border:1px solid #bf8fdb;
        border-radius:8px; background:#321446; color:white; font:inherit;
        font-size:.85rem; cursor:pointer;
      }
      @keyframes pc-operation-spin { to { transform:rotate(360deg); } }
      @keyframes pc-operation-scan { to { transform:translateX(190%); } }
      @media (prefers-reduced-motion:reduce) {
        #pc-operation-loading .pc-loading-symbol,
        #pc-operation-loading .pc-loading-bar::before { animation:none; }
      }
    `;
    doc.head.appendChild(style);
  }

  function hasSimilarityLoader() {
    return Boolean(doc.getElementById("pc-sim-load"));
  }

  function clear() {
    active = false;
    if (showTimer !== null) host.clearTimeout(showTimer);
    if (longWaitTimer !== null) host.clearTimeout(longWaitTimer);
    showTimer = null;
    longWaitTimer = null;
    doc.getElementById(OVERLAY_ID)?.remove();
  }

  function show(label) {
    if (!active || !enabled || hasSimilarityLoader()) {
      clear();
      return;
    }
    ensureStyle();
    const overlay = doc.createElement("div");
    overlay.id = OVERLAY_ID;
    overlay.setAttribute("role", "status");
    overlay.setAttribute("aria-live", "polite");
    overlay.setAttribute("aria-atomic", "true");
    overlay.innerHTML = `
      <section class="pc-loading-card" aria-label="작업 진행 중">
        <div class="pc-loading-symbol" aria-hidden="true"></div>
        <h2 class="pc-loading-title"></h2>
        <p class="pc-loading-description">서버의 응답을 기다리고 있다.<br>버튼을 여러 번 누르지 마세요.</p>
        <div class="pc-loading-bar" aria-hidden="true"></div>
        <div class="pc-loading-caption">PROCESSING ···</div>
        <p class="pc-loading-long" hidden></p>
        <button class="pc-loading-close" type="button" hidden>화면으로 돌아가기</button>
      </section>`;
    overlay.querySelector(".pc-loading-title").textContent =
      String(label || "처리 중…").slice(0, 80);
    overlay.querySelector(".pc-loading-close").addEventListener("click", clear);
    doc.body.appendChild(overlay);
    longWaitTimer = host.setTimeout(() => {
      if (!active) return;
      const note = overlay.querySelector(".pc-loading-long");
      note.textContent = "응답이 지연되고 있다. 베팅·대출·배지 변경은 거래 내역을 확인한 후 다시 시도하세요.";
      note.hidden = false;
      overlay.querySelector(".pc-loading-close").hidden = false;
    }, 25000);
  }

  function start(label) {
    if (!enabled || active || hasSimilarityLoader()) return;
    // Reserve the action immediately to block double-clicks, but do not
    // show a full-screen overlay for sub-200ms Streamlit reruns.
    active = true;
    showTimer = host.setTimeout(() => {
      showTimer = null;
      show(label);
    }, SHOW_DELAY_MS);
  }

  function complete(token, nextEnabled) {
    enabled = Boolean(nextEnabled);
    if (token === lastRunToken) {
      if (!enabled) clear();
      return;
    }
    lastRunToken = token;
    clear();
  }

  function labelFor(button) {
    const label = [
      button.getAttribute("aria-label") || "",
      button.getAttribute("title") || "",
      button.innerText || button.textContent || "",
    ].join(" ").trim();
    if (/베팅|배팅/.test(label)) return "베팅 접수 중…";
    if (/장착|해제|배지/.test(label) ||
        button.closest('[class*="st-key-badge_"]')) return "배지 정보 처리 중…";
    if (/기사|뉴스|읽었으면|다음/.test(label)) return "기사 불러오는 중…";
    if (/대출|상환|은행/.test(label)) return "은행 거래 처리 중…";
    if (/로그인|가입/.test(label)) return "계정 확인 중…";
    return "요청 처리 중…";
  }

  function isSimilarityTrigger(button) {
    const label = (button.innerText || button.textContent || "").trim();
    // These actions enter the existing similarity-analysis loader. Do not
    // obscure it with the generic processing overlay.
    return /유사도\s*(분석|판정|계산)/.test(label) ||
      /\b(?:HIGH|LOW)\s*\((?:이상|미만)/.test(label);
  }

  doc.addEventListener("click", (event) => {
    if (!enabled || !(event.target instanceof host.Element)) return;
    const button = event.target.closest("button");
    if (!button || button.disabled || button.getAttribute("aria-disabled") === "true") return;
    if (!button.closest('[data-testid="stButton"], [data-testid="stFormSubmitButton"]')) return;
    if (active) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return;
    }
    if (isSimilarityTrigger(button)) return;
    start(labelFor(button));
  }, true);

  function sourceIsFrame(source, selector) {
    return Array.from(doc.querySelectorAll(selector)).some(
      (iframe) => iframe.contentWindow === source
    );
  }

  host.addEventListener("message", (event) => {
    const data = event.data;
    if (!data || typeof data !== "object") return;
    if (data.type === "pc:loading:start" && sourceIsFrame(event.source,
      '.st-key-shared-news-stage iframe, .st-key-shared-article-reader iframe,' +
      ' .st-key-game1-prediction-screen iframe, .st-key-game1-result-reveal-screen iframe'
    )) {
      if (data.mode !== "similarity") start(data.label);
    } else if (data.type === "streamlit:setComponentValue" &&
      sourceIsFrame(event.source, '.st-key-main_menu_banners iframe') &&
      Number.isInteger(data.value) && data.value >= 0) {
      start("화면 이동 중…");
    }
  });

  // Existing similarity screen wins even when Streamlit inserts its markup
  // after a generic click has already scheduled a loader.
  const similarityObserver = new host.MutationObserver(() => {
    if (active && hasSimilarityLoader()) clear();
  });
  similarityObserver.observe(doc.body, {childList:true, subtree:true});

  host.addEventListener("pagehide", clear);
  host[KEY] = {start, complete, clear, version:2};
  complete(pcRunToken, pcEnabled);
})();