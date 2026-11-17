"use strict";

// A zero-height Streamlit component attaches one native click listener.
// Inline scripts are ignored by st.markdown, so keep controls separate.
(() => {
  let doc;
  try {
    doc = window.parent.document;
  } catch (_) {
    return;  // Cross-origin preview; video still works with native controls.
  }

  const frame = window.frameElement;
  if (frame) {
    frame.setAttribute("aria-hidden", "true");
    frame.style.cssText += ";position:absolute!important;width:0!important;height:0!important;border:0!important;pointer-events:none!important;";
  }

  function toggleSound(event) {
    const target = event.target;
    if (!target || typeof target.closest !== "function") return;
    const button = target.closest("#pc-sim-load .pc-sim-sound-toggle");
    if (!button) return;

    const video = doc.querySelector("#pc-sim-load .pc-sim-video");
    if (!video) return;

    const turnOn = video.muted;
    video.muted = !turnOn;
    button.textContent = turnOn ? "소리 끄기" : "소리 켜기";
    button.setAttribute("aria-pressed", String(turnOn));

    // The click is a real user gesture, which allows audio on iOS Safari.
    if (video.paused) {
      const attempt = video.play();
      if (attempt && typeof attempt.catch === "function") {
        attempt.catch(() => {
          video.muted = true;
          button.textContent = "재생 메뉴에서 소리 켜기";
          button.setAttribute("aria-pressed", "false");
        });
      }
    }
  }

  doc.addEventListener("click", toggleSound);
  window.addEventListener("pagehide", () => {
    doc.removeEventListener("click", toggleSound);
  }, {once: true});
})();
