"use strict";

const shell = document.querySelector(".game-shell");
const coins = shell.querySelector(".coins");
const range = shell.querySelector(".target strong");
const cards = Array.from(shell.querySelectorAll(".card"));
let roundId = null;
let sending = false;
let hostOrigin = "*";

function send(type, payload) {
  window.parent.postMessage({isStreamlitMessage:true, type, ...payload}, hostOrigin);
}

function finish(action, index) {
  if (!roundId || sending) return;
  sending = true;
  for (const button of shell.querySelectorAll("button")) button.disabled = true;
  window.parent.postMessage({
    type:"pc:loading:start",
    label: action === "read" ? "뉴스 본문을 여는 중…" : "선택 확인 중…"
  }, hostOrigin);
  send("streamlit:setComponentValue", {
    value:{round_id:roundId, action, index},
    dataType:"json"
  });
}

for (const card of cards) {
  card.querySelector(".read").addEventListener("click", () => finish("read", Number(card.dataset.index)));
  card.querySelector(".select").addEventListener("click", () => finish("select", Number(card.dataset.index)));
}
shell.querySelector(".nav-button").addEventListener("click", () => finish("back", -1));
shell.querySelector(".bank").addEventListener("click", () => finish("bank", -1));

window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  const args = event.data.args;
  if (!args || !args.round_id) return;
  hostOrigin = event.origin && event.origin !== "null" ? event.origin : "*";
  const titles = Array.isArray(args.titles) ? args.titles : [];
  cards.forEach((card, index) => {
    card.querySelector(".card-title").textContent = String(titles[index] || "뉴스 후보");
  });
  range.textContent = String(args.range_text || "");
  coins.textContent = `${Number(args.coins || 0).toLocaleString("ko-KR")} C`;
  if (roundId !== args.round_id) {
    roundId = args.round_id;
    sending = false;
    for (const button of shell.querySelectorAll("button")) button.disabled = false;
  }
  shell.hidden = false;
  send("streamlit:setFrameHeight", {height: window.innerHeight || 956});
});

window.addEventListener("resize", () => {
  send("streamlit:setFrameHeight", {height: window.innerHeight || 956});
});

send("streamlit:componentReady", {apiVersion:1});
