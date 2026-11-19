"use strict";
const scene = document.querySelector(".scene");
const buttons = Array.from(document.querySelectorAll(".segment"));
const confirmButton = document.querySelector(".confirm");
const mystery = document.querySelector(".mystery");
const scoreValue = mystery.querySelector("strong");
const scoreUnit = mystery.querySelector(".unit");
const subtitle = document.querySelector(".subtitle");
const numberFormat = new Intl.NumberFormat("ko-KR");
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
let roundId = null;
let selected = 1;
let sending = false;
let revealing = false;
let hostOrigin = "*";
let revealTimers = [];

function send(type, payload) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...payload}, hostOrigin);
}
function schedule(fn, delay) {
  revealTimers.push(setTimeout(fn, delay));
}
function resetAnimation() {
  for (const timer of revealTimers) clearTimeout(timer);
  revealTimers = [];
  mystery.classList.remove("rolling", "score-visible", "moving", "landed");
  mystery.style.removeProperty("--landing-offset");
  mystery.removeAttribute("aria-label");
  scoreValue.textContent = "??";
  scoreUnit.hidden = false;
  subtitle.textContent = "숨겨진 일치율이 어느 구간에 있을까?";
  buttons.forEach(button => button.classList.remove("correct"));
}
function finish(action) {
  if (!roundId || sending) return;
  if (action === "choose" && revealing) return;
  if (action === "reveal_complete" && !revealing) return;
  sending = true;
  confirmButton.disabled = true;
  for (const button of scene.querySelectorAll("button")) button.disabled = true;
  window.parent.postMessage({
    type: "pc:loading:start",
    label: action === "choose" ? "선택한 구간 확인 중…" :
      action === "reveal_complete" ? "최종 결과 화면 여는 중…" : "화면 이동 중…"
  }, hostOrigin);
  const value = {action, round_id: roundId};
  if (action === "choose") value.index = selected;
  send("streamlit:setComponentValue", {value, dataType: "json"});
}
function select(index) {
  if (sending || revealing || !Number.isInteger(index) || index < 0 || index > 2) return;
  selected = index;
  buttons.forEach(button => button.setAttribute("aria-pressed", String(Number(button.dataset.index) === selected)));
}
function startReveal(payload) {
  if (revealing) return;
  const answer = Number(payload.answer_index);
  const ownChoice = Number(payload.selected_index);
  const score = String(payload.score || "");
  if (!Number.isInteger(answer) || answer < 0 || answer > 2 ||
      !Number.isInteger(ownChoice) || ownChoice < 0 || ownChoice > 2 ||
      !/^(?:\d|\d{2})\.\d{2}$/.test(score)) return;
  revealing = true;
  sending = false; // The earlier "choose" was already accepted by Python.
  selected = ownChoice;
  subtitle.textContent = "AI가 계산한 일치율을 공개합니다";
  for (const button of scene.querySelectorAll("button")) button.disabled = true;
  buttons.forEach(button => {
    button.setAttribute("aria-pressed", "false");
    button.classList.remove("correct");
  });
  const landingButton = buttons.find(button => Number(button.dataset.index) === answer);
  const instant = reduceMotion.matches;

  if (!instant) mystery.classList.add("rolling");
  schedule(() => {
    scoreValue.textContent = score;
    mystery.setAttribute("aria-label", "실제 일치율 " + score + "%");
    mystery.classList.remove("rolling");
    mystery.classList.add("score-visible");
  }, instant ? 0 : 750);

  schedule(() => {
    const source = mystery.getBoundingClientRect();
    const target = landingButton.getBoundingClientRect();
    // Move the SAME mystery box, so its center meets the correct segment's center.
    const offset = Math.round(target.top + target.height / 2 - source.top - source.height / 2);
    mystery.style.setProperty("--landing-offset", offset + "px");
    if (!instant) {
      void mystery.offsetWidth;
      mystery.classList.add("moving");
    }
  }, instant ? 0 : 1050);

  schedule(() => {
    landingButton.classList.add("correct");
    mystery.classList.add("landed");
  }, instant ? 0 : 2050);

  // Only this event navigates to the final result page.
  schedule(() => finish("reveal_complete"), instant ? 700 : 2600);
}
function render(args) {
  if (!args || !Array.isArray(args.ranges) || args.ranges.length !== 3 ||
      !args.round_id || !args.art) return;
  if (roundId !== args.round_id) {
    roundId = args.round_id;
    revealing = false;
    sending = false;
    selected = 1;
    resetAnimation();
  }

  document.body.style.setProperty("--background", 'url("' + args.art.background + '")');
  document.querySelector(".logo").src = args.art.logo;
  document.querySelector(".laurel.left").src = args.art.laurel_left;
  document.querySelector(".laurel.right").src = args.art.laurel_right;
  document.querySelector(".coins").textContent = numberFormat.format(Number(args.coins || 0));
  document.querySelector(".tick-label.top").textContent = String(args.ranges[2]).split("~")[1] || "";
  document.querySelector(".tick-label.bottom").textContent = String(args.ranges[0]).split("~")[0] + "%";
  buttons.forEach(button => {
    const index = Number(button.dataset.index);
    button.querySelector(".segment-range").textContent = String(args.ranges[index]);
  });
  scene.hidden = false;
  if (!revealing && !sending) {
    for (const button of scene.querySelectorAll("button")) button.disabled = false;
    select(selected);
  }
  if (args.reveal && !revealing) startReveal(args.reveal);
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
