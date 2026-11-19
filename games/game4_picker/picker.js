"use strict";
const scene = document.querySelector(".scene");
const buttons = Array.from(document.querySelectorAll(".segment"));
const confirmButton = document.querySelector(".confirm");
const numberFormat = new Intl.NumberFormat("ko-KR");
let roundId = null;
let selected = 1;
let sending = false;
let hostOrigin = "*";

function send(type, payload) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...payload}, hostOrigin);
}
function finish(action) {
  if (!roundId || sending) return;
  sending = true;
  confirmButton.disabled = true;
  for (const button of scene.querySelectorAll("button")) button.disabled = true;
  window.parent.postMessage({
    type: "pc:loading:start",
    label: action === "choose" ? "선택한 구간 확인 중…" : "화면 이동 중…"
  }, hostOrigin);
  const value = {action, round_id: roundId};
  if (action === "choose") value.index = selected;
  send("streamlit:setComponentValue", {value, dataType: "json"});
}
function select(index) {
  if (sending || !Number.isInteger(index) || index < 0 || index > 2) return;
  selected = index;
  buttons.forEach(button => button.setAttribute("aria-pressed", String(Number(button.dataset.index) === selected)));
}
function render(args) {
  if (!args || !Array.isArray(args.ranges) || args.ranges.length !== 3 || !args.round_id || !args.art) return;
  if (roundId !== args.round_id) {
    roundId = args.round_id; sending = false; selected = 1;
  }
  for (const b of scene.querySelectorAll("button")) b.disabled = false;
  document.body.style.setProperty("--background", 'url("' + args.art.background + '")');
  document.querySelector(".logo").src = args.art.logo;
  document.querySelector(".laurel.left").src = args.art.laurel_left;
  document.querySelector(".laurel.right").src = args.art.laurel_right;
  document.querySelector(".coins").textContent = numberFormat.format(Number(args.coins || 0));
  const top = String(args.ranges[2]).split("~")[1];
  const bottom = String(args.ranges[0]).split("~")[0] + "%";
  document.querySelector(".tick-label.top").textContent = top || "";
  document.querySelector(".tick-label.bottom").textContent = bottom;
  buttons.forEach(button => {
    const index = Number(button.dataset.index);
    button.querySelector(".segment-range").textContent = String(args.ranges[index]);
  });
  select(selected);
  scene.hidden = false;
  send("streamlit:setFrameHeight", {height: window.innerHeight || 620});
}
buttons.forEach(button => button.addEventListener("click", () => select(Number(button.dataset.index))));
confirmButton.addEventListener("click", () => finish("choose"));
document.querySelector(".back").addEventListener("click", () => finish("back"));
document.querySelector(".bank").addEventListener("click", () => finish("bank"));
window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  hostOrigin = event.origin === "null" ? "*" : event.origin;
  render(event.data.args);
});
send("streamlit:componentReady", {apiVersion: 1});
send("streamlit:setFrameHeight", {height: window.innerHeight});
