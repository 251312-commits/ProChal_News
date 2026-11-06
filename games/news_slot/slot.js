"use strict";

const scene = document.querySelector(".scene");
const lever = scene.querySelector(".lever");
const reels = scene.querySelector(".window");
const hint = scene.querySelector(".hint");
const confirmBtn = scene.querySelector(".confirm");
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)");
let roundId, titles = [], selected = -1, drag = null, continuousReel = false;
let timers = [], audio, hostOrigin = "*";

function send(type, payload) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...payload}, hostOrigin);
}

function finish(action, index) {
  if (!roundId || scene.dataset.phase === "sent") return;
  scene.dataset.phase = "sent";
  confirmBtn.disabled = lever.disabled = true;
  for (const button of scene.querySelectorAll(".row, nav button")) button.disabled = true;
  stopTimers();
  if (audio) { audio.close().catch(() => {}); audio = null; }
  const value = {action, round_id: roundId};
  if (action === "choose") value.index = index;
  send("streamlit:setComponentValue", {value, dataType: "json"});
}

function stopTimers() {
  timers.forEach(clearTimeout);
  timers = [];
}

function paper(label, pending = false) {
  const panel = document.createElement("span");
  panel.className = "paper";
  const title = document.createElement("span");
  title.className = pending ? "headline pending" : "headline";
  title.textContent = label;
  panel.append(title);
  return panel;
}

function reset(id, options) {
  stopTimers();
  if (audio) { audio.close().catch(() => {}); audio = null; }
  roundId = id;
  titles = options;
  selected = -1;
  drag = null;
  scene.dataset.phase = "idle";
  lever.classList.remove("dragging");
  lever.style.removeProperty("--tilt");
  lever.disabled = !titles.length;
  confirmBtn.disabled = true;
  for (const button of scene.querySelectorAll("nav button")) button.disabled = false;
  hint.textContent = titles.length ? "레버를 아래로 당겨 뉴스를 뽑으세요." : "선택할 뉴스가 없습니다.";
  reels.replaceChildren();
  for (let i = 0; i < 3; i++) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "row";
    button.disabled = true;
    button.setAttribute("aria-label", "공개 전");
    button.setAttribute("aria-pressed", "false");
    const tape = document.createElement("span");
    tape.className = "tape";
    tape.setAttribute("aria-hidden", "true");
    tape.append(paper("• • •", true));
    button.append(tape);
    button.addEventListener("click", () => {
      if (scene.dataset.phase !== "ready" || i >= titles.length) return;
      selected = i;
      for (const [j, row] of Array.from(reels.children).entries()) {
        row.setAttribute("aria-pressed", String(j === i));
      }
      confirmBtn.disabled = false;
      hint.textContent = titles[i];
      hint.scrollTop = 0;
    });
    reels.append(button);
  }
}

function sound(durations) {
  try {
    const prefs = JSON.parse(sessionStorage.getItem("news-bgm-preferences-v1") || "{}");
    const volume = Math.min(1, Math.max(0, Number(prefs.volume ?? .3)));
    if (prefs.muted || !volume || reduceMotion.matches) return;
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return;
    audio = new Audio();
    audio.resume().catch(() => {});
    function note(seconds, frequency, type, amplitude, duration) {
      const start = audio.currentTime + seconds;
      const osc = audio.createOscillator(), gain = audio.createGain();
      osc.type = type;
      osc.frequency.value = frequency;
      gain.gain.setValueAtTime(volume * amplitude, start);
      gain.gain.exponentialRampToValueAtTime(.0001, start + duration);
      osc.connect(gain).connect(audio.destination);
      osc.start(start);
      osc.stop(start + duration);
    }
    const end = durations[durations.length - 1] / 1000;
    for (let t = 0; t < end; t += .095) note(t, 330, "triangle", .11, .045);
    durations.forEach((ms, i) => note(ms / 1000, 480 + 100 * i, "triangle", .2, .1));
    [523, 659, 784].forEach((freq, i) => note(end + .08 * i, freq, "sine", .17, .13));
  } catch (_) { /* Audio is optional when the browser blocks playback. */ }
}

function revealRow(row, i) {
  row.firstElementChild.replaceChildren(paper(titles[i] || "—"));
  row.setAttribute("aria-label", titles[i] || "등록된 후보 없음");
}

function enableChoices(rows) {
  scene.dataset.phase = "ready";
  rows.forEach((row, i) => { row.disabled = i >= titles.length; });
  hint.textContent = titles.length === 3 ? "세 개의 뉴스 중 하나를 선택하세요." : "읽을 뉴스를 선택하세요.";
}

function spinContinuousReel(rows) {
  rows.forEach(revealRow);
  if (reduceMotion.matches) {
    enableChoices(rows);
    return;
  }
  const strip = document.createElement("div");
  strip.className = "continuous-reel";
  strip.setAttribute("aria-hidden", "true");
  for (let i = 0; i < rows.length; i++) strip.append(paper("• • •", true));
  for (let i = 0; i < rows.length * 2; i++) strip.append(paper(titles[i % titles.length]));
  strip.style.setProperty("--travel", -(strip.childElementCount / rows.length) * 100 + "%");
  const duration = 2070;
  strip.style.setProperty("--time", duration + "ms");
  strip.append(...rows);
  function settle() {
    if (scene.dataset.phase !== "spinning" || strip.parentNode !== reels) return;
    reels.replaceChildren(...rows);
    enableChoices(rows);
  }
  strip.addEventListener("animationend", settle, {once: true});
  reels.replaceChildren(strip);
  // A browser or user stylesheet can suppress the animation event.
  timers.push(setTimeout(settle, duration + 150));
  sound([duration]);
}

function spin() {
  if (scene.dataset.phase !== "idle" || !titles.length) return;
  scene.dataset.phase = "spinning";
  lever.classList.remove("dragging");
  lever.style.setProperty("--tilt", "108deg");
  lever.disabled = true;
  hint.textContent = "뉴스를 뽑는 중…";
  const rows = Array.from(reels.children);
  timers.push(setTimeout(() => lever.style.removeProperty("--tilt"), 280));
  if (continuousReel) {
    spinContinuousReel(rows);
    return;
  }
  const durations = rows.map((_, i) => reduceMotion.matches ? 50 : 1450 + 310 * i);
  sound(durations);
  rows.forEach((row, i) => {
    const finalTitle = titles[i] || "—";
    const tape = row.firstElementChild;
    row.style.setProperty("--time", durations[i] + "ms");
    for (let j = 0; j < 6; j++) {
      tape.append(paper(titles[(i + j + 1) % titles.length]));
    }
    tape.append(paper(finalTitle));
    row.classList.add("rolling");
    timers.push(setTimeout(() => {
      row.classList.remove("rolling");
      revealRow(row, i);
      if (i === rows.length - 1) enableChoices(rows);
    }, durations[i]));
  });
}

lever.addEventListener("pointerdown", event => {
  if (scene.dataset.phase !== "idle" || !event.isPrimary || event.button !== 0 || drag) return;
  drag = {id: event.pointerId, y: event.clientY};
  lever.setPointerCapture(event.pointerId);
  lever.classList.add("dragging");
});
lever.addEventListener("pointermove", event => {
  if (!drag || event.pointerId !== drag.id) return;
  const threshold = Math.max(22, Math.min(56, lever.clientHeight * .36));
  const distance = Math.max(0, event.clientY - drag.y);
  lever.style.setProperty("--tilt", Math.min(1, distance / threshold) * 88 + "deg");
  if (distance >= threshold) {
    drag = null;
    spin();
  }
});
function release(event) {
  if (!drag || drag.id !== event.pointerId) return;
  drag = null;
  lever.classList.remove("dragging");
  lever.style.removeProperty("--tilt");
}
lever.addEventListener("pointerup", release);
lever.addEventListener("pointercancel", release);
lever.addEventListener("lostpointercapture", release);
// Keyboard and assistive technologies activate native buttons without a pointer.
lever.addEventListener("click", event => { if (event.detail === 0) spin(); });

confirmBtn.addEventListener("click", () => {
  if (scene.dataset.phase === "ready" && selected >= 0) finish("choose", selected);
});
scene.querySelector(".back").addEventListener("click", () => finish("back"));
scene.querySelector(".bank").addEventListener("click", () => finish("bank"));

window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  const args = event.data.args;
  if (!args || !Array.isArray(args.titles) || !args.art || !args.round_id) return;
  hostOrigin = event.origin === "null" ? "*" : event.origin;
  const {art} = args;
  for (const [selector, key] of [[".crown", "crown"], [".cushion", "cushion"], [".frame", "frame"], [".arm", "lever"]]) {
    const img = scene.querySelector(selector);
    if (img.getAttribute("src") !== art[key]) img.src = art[key];
  }
  document.body.style.setProperty("--backdrop", 'url("' + art.background + '")');
  document.body.style.setProperty("--paper", 'url("' + art.paper + '")');
  const coins = scene.querySelector(".coins");
  coins.textContent = Number(args.coins).toLocaleString("ko-KR");
  coins.setAttribute("aria-label", "보유 코인 " + coins.textContent);
  if (roundId !== args.round_id) {
    continuousReel = args.continuous_reel === true;
    reset(args.round_id, args.titles);
  }
  scene.hidden = false;
  send("streamlit:setFrameHeight", {height: window.innerHeight || 620});
});
send("streamlit:componentReady", {apiVersion: 1});
