"use strict";

const scene = document.querySelector(".scene");
const pages = document.querySelector(".pages");
const bodyCopy = document.querySelector("#copy");
const keep = document.querySelector(".keep");
const timer = document.querySelector("#timer");
const timerLabel = document.querySelector("#timer-label");
const progress = document.querySelector("#progress");
const number = new Intl.NumberFormat("ko-KR");
let roundId, hostOrigin = "*", interval, deadline, sent = false;

function send(type, payload) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...payload}, hostOrigin);
}

function finish(action) {
  if (!roundId || sent) return;
  sent = true;
  clearInterval(interval);
  for (const button of scene.querySelectorAll("button")) button.disabled = true;
  send("streamlit:setComponentValue", {value: {action, round_id: roundId}, dataType: "json"});
}

function tick() {
  const seconds = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
  timer.textContent = seconds + "초";
  if (seconds === 0) finish("predict");
}

function updateProgress() {
  if (scene.hidden) return;
  const body = bodyCopy.getBoundingClientRect();
  if (!body.height) return;
  const visible = (pages.getBoundingClientRect().bottom - body.top) / body.height;
  const percent = Math.max(progress.value, Math.min(100, Math.max(0, Math.round(visible * 100))));
  progress.value = percent;
  document.querySelector("#percent").textContent = percent + "%";
}

function showArticle(args) {
  clearInterval(interval);
  roundId = args.round_id;
  sent = false;
  for (const button of scene.querySelectorAll("button")) button.disabled = false;

  for (const img of scene.querySelectorAll("[data-art]")) img.src = args.art[img.dataset.art];
  for (const key of ["background", "frame", "news-label", "balance-pill", "article-divider",
                     "guidance-panel", "reward-pill", "predict-button", "read-button", "stage-ring", "progress-track", "progress-fill"]) {
    document.body.style.setProperty("--" + key, 'url("' + args.art[key] + '")');
  }
  const title = args.title;
  const copyrightStory = /저작권|copyright/i.test(title) && /인공지능|생성형|\bai\b|AI(?=[가-힣])/i.test(title);
  document.querySelector(".illustration").hidden = !copyrightStory;
  document.querySelector(".edition").hidden = copyrightStory;
  document.querySelector("#headline").textContent = title;

  const source = document.querySelector("#source");
  source.hidden = !(args.source && /^https?:\/\//i.test(args.url));
  if (source.hidden) source.removeAttribute("href");
  else {
    source.href = args.url;
    source.textContent = args.source;
    source.setAttribute("aria-label", args.source + " 기사 원문 (새 창)");
  }
  const paragraphs = args.text.trim().split(/\n+/).filter(Boolean);
  bodyCopy.replaceChildren(...paragraphs.map(line => {
    const p = document.createElement("p");
    p.textContent = line;
    return p;
  }));
  const minutes = Math.max(1, Math.ceil(args.text.replace(/\s/g, "").length / 500));
  document.querySelector("#duration").textContent = "약 " + minutes + "분 읽기";

  const reward = document.querySelector(".reward");
  reward.hidden = !Number.isFinite(args.reward);
  document.querySelector("#reward").textContent = reward.hidden ? "" : "+" + number.format(args.reward) + " C";
  keep.querySelector("span").textContent = "계속 읽기";
  timerLabel.textContent = "예측 화면 자동 이동까지";
  scene.hidden = false;
  pages.scrollTop = 0;
  progress.value = 0;
  updateProgress();
  deadline = Date.now() + 30000;
  tick();
  interval = setInterval(tick, 250);
}

pages.addEventListener("scroll", updateProgress, {passive: true});
new ResizeObserver(updateProgress).observe(pages);
new ResizeObserver(updateProgress).observe(bodyCopy);
keep.addEventListener("click", () => {
  if (sent) return;
  clearInterval(interval);
  if (deadline === null) {
    pages.scrollBy({top: pages.clientHeight * .8, behavior: "instant"});
  } else {
    deadline = null;
    keep.querySelector("span").textContent = "이어서 읽기";
    timerLabel.textContent = "기사 읽기";
    timer.textContent = "무제한";
  }
  pages.focus({preventScroll: true});
});
document.querySelector(".predict").addEventListener("click", () => finish("predict"));
document.querySelector(".back").addEventListener("click", () => finish("back"));
document.querySelector(".bank").addEventListener("click", () => finish("bank"));

window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  const args = event.data.args;
  if (!args?.round_id || !args.art || typeof args.title !== "string" || typeof args.text !== "string") return;
  hostOrigin = event.origin === "null" ? "*" : event.origin;
  if (roundId !== args.round_id) showArticle(args);
  const coins = document.querySelector("#coins");
  coins.textContent = number.format(args.coins);
  coins.setAttribute("aria-label", "보유 코인 " + coins.textContent);
  send("streamlit:setFrameHeight", {height: window.innerHeight});
});
send("streamlit:componentReady", {apiVersion: 1});
