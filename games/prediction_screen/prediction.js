"use strict";

/* The same Streamlit v1 iframe protocol used by games/news_slot/slot.js.
   Arrow clicks update the DOM immediately (no Python round-trip delay), then
   synchronize both decimal digits to the existing Streamlit session keys. */
const screen = document.querySelector(".prediction");
const ui = {
  back: screen.querySelector(".back"),
  bank: screen.querySelector(".bank"),
  balance: screen.querySelector(".balance"),
  coins: screen.querySelector(".coins"),
  title: screen.querySelector(".news-title"),
  crest: screen.querySelector(".crest"),
  news: screen.querySelector(".news-art"),
  tag: screen.querySelector(".news-tag"),
  frame: screen.querySelector(".machine-art"),
  podium: screen.querySelector(".podium"),
  confirm: screen.querySelector(".confirm"),
};
const reels = Array.from(screen.querySelectorAll(".reel"));
let roundId = null;
let digits = [0, 4];
let hostOrigin = "*";
let locked = false;

function send(type, payload) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...payload}, hostOrigin);
}
function sendValue(action) {
  send("streamlit:setComponentValue", {
    value: {round_id: roundId, action, digits: digits.slice()},
    dataType: "json",
  });
}
function paintDigits() {
  for (let i = 0; i < 2; i++) {
    reels[i].querySelector("output").textContent = String(digits[i]);
  }
}
function finish(action) {
  if (!roundId || locked) return;
  locked = true;
  for (const button of screen.querySelectorAll("button")) button.disabled = true;
  sendValue(action);
}
for (const [index, reel] of reels.entries()) {
  for (const [direction, amount] of [["up", 1], ["down", -1]]) {
    reel.querySelector("." + direction).addEventListener("click", () => {
      if (locked || !roundId) return;
      digits[index] = (digits[index] + amount + 10) % 10;
      paintDigits();
      sendValue("change");
    });
  }
}
ui.back.addEventListener("click", () => finish("back"));
ui.bank.addEventListener("click", () => finish("bank"));
ui.confirm.addEventListener("click", () => {
  // Unlock on the tap itself, before Streamlit replaces the prediction iframe.
  try { window.parent.__newsScoreRoll?.unlock(); } catch (_) {}
  finish("confirm");
});

function setImage(image, uri) {
  if (typeof uri === "string" && uri && image.getAttribute("src") !== uri) {
    image.src = uri;
  }
}
window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  const args = event.data.args;
  if (!args || !args.round_id || !args.art) return;

  hostOrigin = event.origin && event.origin !== "null" ? event.origin : "*";
  const art = args.art;
  for (const [name, target] of [
    ["header", ui.crest], ["news", ui.news], ["tag", ui.tag],
    ["frame", ui.frame], ["podium", ui.podium],
  ]) setImage(target, art[name]);
  for (const reel of reels) setImage(reel.querySelector(".reel-art"), art.reel);
  if (typeof art.background === "string" && art.background) {
    document.body.style.setProperty("--background", 'url("' + art.background + '")');
  }

  // Dynamic news titles are text, never inserted as HTML markup.
  ui.title.textContent = String(args.title ?? "선택된 뉴스가 없습니다");
  const balance = Number(args.coins || 0).toLocaleString("ko-KR") + " C";
  ui.coins.textContent = balance;
  ui.balance.setAttribute("aria-label", "보유 코인 " + balance);

  if (roundId !== args.round_id) {
    roundId = args.round_id;
    const values = Array.isArray(args.digits) ? args.digits : [0, 4];
    digits = [0, 1].map(i =>
      Number.isInteger(values[i]) && values[i] >= 0 && values[i] <= 9
        ? values[i] : (i === 0 ? 0 : 4)
    );
    locked = false;
    for (const button of screen.querySelectorAll("button")) button.disabled = false;
    paintDigits();
  }
  // Do not overwrite locally changed digits on rerender of the same round:
  // rapid taps must not jump backwards when a previous server value arrives.
  screen.hidden = false;
  send("streamlit:setFrameHeight", {height: window.innerHeight || 700});
});
window.addEventListener("resize", () => {
  if (!screen.hidden) send("streamlit:setFrameHeight", {height: window.innerHeight || 700});
});
send("streamlit:componentReady", {apiVersion: 1});
