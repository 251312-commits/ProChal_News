"use strict";

/* Music is the clock. No setTimeout-based music/drop synchronization.
   The already-settled server result only controls this presentation. */
const screen = document.querySelector(".reveal");
const ui = {
  title: screen.querySelector(".news-title"),
  newsArt: screen.querySelector(".news-art"),
  frame: screen.querySelector(".frame-art"),
  podium: screen.querySelector(".podium"),
  wallet: screen.querySelector(".wallet"),
  balance: screen.querySelector(".balance"),
  guess: [screen.querySelector(".guess-tens"), screen.querySelector(".guess-ones")],
  whole: screen.querySelector(".whole"),
  digits: Array.from(screen.querySelectorAll(".actual-digit")),
  progress: screen.querySelector(".progress-fill"),
  status: screen.querySelector(".status"),
  outcome: screen.querySelector(".outcome"),
  outcomeTitle: screen.querySelector(".outcome-title"),
  outcomeDescription: screen.querySelector(".outcome-description"),
  reward: screen.querySelector(".reward"),
  analysis: document.querySelector(".analysis"),
  analysisClose: document.querySelector(".analysis-close"),
  analysisTitle: document.querySelector(".analysis-title"),
  analysisModel: document.querySelector(".analysis-model-name"),
  analysisTokens: document.querySelector(".analysis-tokens"),
  summary: document.querySelector(".analysis-summary"),
  logit: document.querySelector(".analysis-logit"),
  normalized: document.querySelector(".analysis-normalized"),
  chart: document.querySelector(".sigmoid-chart"),
  chartCurve: document.querySelector(".chart-curve"),
  chartGuides: document.querySelector(".chart-guides"),
  chartPoint: document.querySelector(".chart-point"),
  chartMin: document.querySelector(".chart-min"),
  chartMax: document.querySelector(".chart-max"),
  chartUnavailable: document.querySelector(".chart-unavailable"),
  analysisScore: document.querySelector(".analysis-score"),
  analysisMeter: document.querySelector(".analysis-meter-fill"),
  analysisGuess: Array.from(document.querySelectorAll(".analysis-guess-digit")),
  analysisAnswer: Array.from(document.querySelectorAll(".analysis-answer-digit")),
  analysisVerdict: document.querySelector(".analysis-verdict"),
  start: screen.querySelector(".start"),
  skip: screen.querySelector(".skip"),
  explain: screen.querySelector(".explain"),
  afterActions: screen.querySelector(".after-actions"),
  again: screen.querySelector(".again"),
  home: screen.querySelector(".home"),
  soundSwitch: screen.querySelector(".sound-switch"),
  retryFail: screen.querySelector(".retry-fail")
};

let roundId = null;
let args = null;
let hostOrigin = "*";
let song = null;
let failSound = null;
let started = false;
let revealFinished = false;
let fullyFinished = false;
let firstRevealed = false;
let secondRevealed = false;
let revealed = [false, false];
let matchCount = 0;
let animationFrame = 0;
let lastRoll = 0;
let localMuted = false;
let locked = false;
let silentStart = null;
let silentMode = false;

function send(type, payload) {
  window.parent.postMessage({isStreamlitMessage: true, type, ...payload}, hostOrigin);
}
function sendAction(action) {
  if (!roundId || locked) return;
  locked = true;
  stopMedia();
  send("streamlit:setComponentValue", {
    value: {round_id: roundId, action: action},
    dataType: "json"
  });
}
function stopMedia() {
  cancelAnimationFrame(animationFrame);
  if (song) song.pause();
  if (failSound) failSound.pause();
}
function pauseMainBgm() {
  try {
    const host = window.parent;
    host.__newsResultActive = true;
    const player = host.__newsBgmPlayer;
    if (player) {
      player.intro.pause();
      player.loop.pause();
      player.playing = false;
      player.pending = false;
      host.__bgm_playing = false;
    }
    host.__newsScoreRoll?.cancel();
  } catch (_) { /* Parent audio bridge may be unavailable in an embedded preview. */ }
}
function soundSettings() {
  let volume = 0.32;
  let muted = false;
  try {
    const player = window.parent.__newsBgmPlayer;
    if (player) {
      volume = Math.max(0, Math.min(1, Number(player.volume)));
      muted = Boolean(player.muted) || volume === 0;
    }
  } catch (_) {}
  return {volume: volume * volume, muted: muted};
}
function applySound() {
  const settings = soundSettings();
  // The BGM control stores a squared, very quiet media gain (30% -> 0.09).
  // The failure stinger needs its own much louder mix, while retaining the
  // listener's volume preference and respecting mute/zero-volume.
  const songGain = localMuted ? 0 : settings.volume;
  const failGain = localMuted ? 0 : Math.min(1, Math.sqrt(settings.volume) * 2);
  if (song) {
    song.muted = localMuted;
    song.volume = songGain;
  }
  if (failSound) {
    failSound.muted = localMuted;
    failSound.volume = failGain;
  }
  ui.soundSwitch.textContent = localMuted ? "♫ 음악 꺼짐" : "♫ 음악 켜짐";
  ui.soundSwitch.setAttribute("aria-pressed", String(localMuted));
}

// On mobile, playing a second audio element after a long asynchronous
// countdown may be disallowed. Unlock it silently during the same user tap
// that starts the result track, then pause/rewind before the actual failure.
function primeFailSound() {
  if (!failSound) return;
  failSound.muted = true;
  failSound.volume = 0;
  const priming = failSound.play();
  if (!priming || typeof priming.then !== "function") return;
  priming.then(() => {
    if (fullyFinished) return; // Never interrupt the genuine loss stinger.
    failSound.pause();
    failSound.currentTime = 0;
    applySound();
  }).catch(() => {
    if (!fullyFinished) applySound();
  });
}

function playFailSound() {
  if (!failSound || localMuted) return;
  failSound.currentTime = 0;
  // Setting the winning soundtrack's volume to zero before invoking play
  // prevents a buffered tail or a resumed BGM from covering the stinger.
  const playing = failSound.play();
  if (playing && typeof playing.catch === "function") {
    playing.catch(() => {
      // A direct tap can recover on browsers which still require a gesture.
      ui.retryFail.hidden = false;
      ui.status.textContent = "패배 효과음 재생이 차단됨 · 버튼을 눌러 재생";
    });
  }
}
function matchPositions() {
  return args.matches.map(Boolean);
}
function actualDigits() {
  return String(args.units % 100).padStart(2, "0").split("");
}
function revealDigit(index) {
  if (revealed[index]) return;
  revealed[index] = true;
  const correct = matchPositions()[index];
  const digit = ui.digits[index];
  digit.textContent = actualDigits()[index];
  digit.classList.remove("spinning");
  digit.classList.add(correct ? "match" : "wrong");
  if (correct) ui.guess[index].classList.add("hit");
  if (ui.whole.textContent === "??") ui.whole.textContent = String(Math.floor(args.units / 100));
  screen.classList.remove("beat");
  void screen.offsetWidth;
  screen.classList.add("beat");
}
function rollIdleNumbers(time) {
  if (time - lastRoll < 75) return;
  lastRoll = time;
  for (let index = 0; index < 2; index++) {
    if (!revealed[index]) {
      ui.digits[index].textContent = String(Math.floor(Math.random() * 10));
      ui.digits[index].classList.add("spinning");
    }
  }
}
function publishOutcome() {
  if (revealFinished) return;
  revealFinished = true;
  for (let i = 0; i < 2; i++) revealDigit(i);
  ui.whole.textContent = String(Math.floor(args.units / 100));
  if (!args.win || fullyFinished) ui.progress.style.width = "100%";
  ui.outcome.hidden = false;
  ui.explain.hidden = false;
  ui.afterActions.hidden = false;
  ui.wallet.hidden = false;
  ui.balance.textContent = Number(args.coins).toLocaleString("ko-KR") + " C";
  const win = Boolean(args.win);
  screen.classList.toggle("jackpot", win);
  screen.classList.toggle("failed", !win);
  ui.outcomeTitle.textContent = win ? "JACKPOT! 완벽한 적중" :
    (matchCount === 1 ? "아쉽다! 한 자리 적중" : "이번엔 빗나갔습니다");
  ui.outcomeDescription.textContent = "내 예측 " + String(args.guess).padStart(2, "0")
    + " · 정답 " + actualDigits().join("") + " · "
    + (win ? "두 자리 모두 일치" : matchCount + "자리 일치");
  const signedReward = (Number(args.reward) > 0 ? "+" : "") +
    Number(args.reward).toLocaleString("ko-KR") + " C";
  ui.reward.textContent = signedReward;
  ui.status.textContent = win ? "두 자리 적중! 음악을 끝까지 즐겨보세요." :
    "음악 중단 · 결과 공개";
}
function failNow() {
  if (revealFinished) return;
  cancelAnimationFrame(animationFrame);
  // Make the track inaudible before the fail effect starts, not after it.
  if (song) {
    song.pause();
    song.muted = true;
    song.volume = 0;
  }
  pauseMainBgm();
  ui.skip.hidden = true;
  publishOutcome();
  fullyFinished = true;
  if (!silentMode) playFailSound();
}
function tick() {
  if (!started || fullyFinished || !args || !song) return;
  const position = silentMode ? Math.max(0, (performance.now() - silentStart) / 1000) : song.currentTime;
  const spec = args.track;
  ui.progress.style.width = Math.min(100, position / spec.end * 100) + "%";
  rollIdleNumbers(performance.now());
  // Stop just BEFORE the beat, so the player never hears an unearned drop.
  if (matchCount === 0 && position >= spec.drop1 - 0.12) {
    failNow();
    return;
  }
  if (!firstRevealed && position >= spec.drop1) {
    firstRevealed = true;
    revealDigit(args.reveal_order[0]);
    ui.status.textContent = "1차 드랍! 일치하는 숫자 공개";
  }
  if (matchCount === 1 && position >= spec.drop2 - 0.12) {
    failNow();
    return;
  }
  if (!secondRevealed && position >= spec.drop2) {
    secondRevealed = true;
    revealDigit(args.reveal_order[1]);
    publishOutcome();
    ui.skip.hidden = false; // Winner may choose to end the victory song early.
  }
  if (position >= spec.end - 0.05) {
    onSongEnded();
    return;
  }
  animationFrame = requestAnimationFrame(tick);
}
function onSongEnded() {
  if (!started || fullyFinished) return;
  fullyFinished = true;
  cancelAnimationFrame(animationFrame);
  if (song && !song.ended) song.pause(); // Honour the configured track ending.
  publishOutcome();
  ui.skip.hidden = true;
  if (Boolean(args.win)) ui.status.textContent = "피날레 완료 · 최종 점수 공개";
}
function skip() {
  if (!started) return;
  stopMedia();
  fullyFinished = true;
  publishOutcome();
  ui.skip.hidden = true;
  ui.status.textContent = "연출 건너뛰기 · 최종 점수 공개";
}
function initializeTrack(data) {
  if (song) song.pause();
  if (failSound) failSound.pause();
  song = new Audio(data.track.url);
  song.preload = "auto";
  song.loop = false;
  failSound = new Audio(data.fail_url);
  failSound.preload = "auto";
  failSound.load();
  song.addEventListener("ended", onSongEnded);
  song.addEventListener("error", () => {
    if (started && !fullyFinished) {
      ui.status.textContent = "음원을 불러오지 못했습니다.";
      skip();
    }
  });
}
function start() {
  if (!args || started) return;
  pauseMainBgm();
  started = true;
  ui.start.hidden = true;
  ui.skip.hidden = false;
  ui.status.textContent = "빌드업 · AI 유사도를 계산했습니다";
  // Autoplay is attempted immediately. Mobile browsers may block unprompted audio:
  // keep the original drop timing with a silent visual clock in that case.
  silentStart = performance.now();
  silentMode = false;
  let pending;
  try { pending = song.play(); }
  catch (_) { pending = Promise.reject(_); }
  if (pending && typeof pending.catch === "function") {
    pending.catch(() => {
      if (!fullyFinished && started) {
        silentMode = true;
        silentStart = performance.now();
        ui.status.textContent = "자동 재생 제한 · 무음으로 결과 공개 중";
      }
    });
  }
  animationFrame = requestAnimationFrame(tick);
}
// Reconstruct the earlier sigmoid visualization from the *stored* model output.
// The graph explains the score transformation, not the model's causal reasoning.
function sigmoid(x) {
  return x >= 0 ? 1 / (1 + Math.exp(-x)) :
    Math.exp(x) / (1 + Math.exp(x));
}
function drawScoreChart(model) {
  const raw = model.logit == null ? NaN : Number(model.logit);
  const normalized = model.normalized == null ? NaN : Number(model.normalized);
  const valid = Number.isFinite(raw) && Number.isFinite(normalized) &&
    normalized >= 0 && normalized <= 1;
  ui.chart.hidden = !valid;
  ui.chartUnavailable.hidden = valid;
  if (!valid) return;

  const limit = Math.max(4, Math.ceil(Math.abs(raw)));
  const left = 38, right = 344, top = 18, bottom = 127;
  const width = right - left, height = bottom - top;
  const points = [];
  for (let i = 0; i <= 120; i++) {
    const fraction = i / 120;
    const x = (fraction * 2 - 1) * limit;
    points.push((i ? "L" : "M") +
      (left + fraction * width).toFixed(2) + "," +
      (bottom - height * sigmoid(x)).toFixed(2));
  }
  const cx = left + ((raw + limit) / (2 * limit)) * width;
  const cy = bottom - normalized * height;
  ui.chartCurve.setAttribute("d", points.join(" "));
  ui.chartGuides.setAttribute("d",
    "M" + left + "," + cy.toFixed(2) + "H" + cx.toFixed(2) + "V" + bottom);
  ui.chartPoint.setAttribute("cx", cx.toFixed(2));
  ui.chartPoint.setAttribute("cy", cy.toFixed(2));
  ui.chartMin.textContent = "−" + limit;
  ui.chartMax.textContent = "+" + limit;
  ui.chart.setAttribute("aria-label",
    "시그모이드 곡선. 관련성 원점수 " + raw.toFixed(4) +
    ", 변환값 " + normalized.toFixed(6) + " 위치를 금색 점으로 표시");
}
function modelDetails(data) {
  const model = data.model || {};
  const wholeScore = (Number(data.units) / 100).toFixed(2);
  const guess = String(data.guess).padStart(2, "0");
  const answer = actualDigits().join("");
  ui.analysisTitle.textContent = String(data.title || "기사 제목이 저장되지 않았습니다.");
  ui.summary.textContent = String(data.summary || "AI 요약문이 저장되지 않았습니다.");
  ui.analysisModel.textContent = String(model.name || "BGE reranker");
  ui.analysisTokens.textContent = model.tokens == null ||
    !Number.isFinite(Number(model.tokens)) ? "토큰 수 기록 없음" :
    Number(model.tokens).toLocaleString("ko-KR") + "토큰";
  ui.logit.textContent = model.logit == null ||
    !Number.isFinite(Number(model.logit)) ? "기록 없음" :
    Number(model.logit).toFixed(4);
  ui.normalized.textContent = model.normalized == null ||
    !Number.isFinite(Number(model.normalized)) ? "기록 없음" :
    Number(model.normalized).toFixed(6);
  drawScoreChart(model);
  ui.analysisScore.textContent = wholeScore;
  const scorePercent = Math.min(100, Math.max(0, Number(data.units) / 100));
  ui.analysisMeter.style.width = scorePercent + "%";
  ui.analysisMeter.parentElement.setAttribute("aria-label",
    "최종 AI 유사도 " + wholeScore + "점, 100점 만점");
  for (let i = 0; i < 2; i++) {
    const correct = Boolean(data.matches[i]);
    ui.analysisGuess[i].textContent = guess[i];
    ui.analysisAnswer[i].textContent = answer[i];
    for (const node of [ui.analysisGuess[i], ui.analysisAnswer[i]]) {
      node.classList.toggle("correct", correct);
      node.classList.toggle("wrong", !correct);
    }
  }
  ui.analysisVerdict.textContent = matchCount === 2 ? "두 자리 모두 일치 · 적중" :
    matchCount === 1 ?
      (data.matches[0] ? "첫 번째 자리만 일치 · 실패" : "두 번째 자리만 일치 · 실패") :
      "두 자리 모두 불일치 · 실패";
}
function openExplanation() {
  if (!revealFinished || locked) return;
  ui.analysis.hidden = false;
  ui.explain.setAttribute("aria-expanded", "true");
  ui.analysisClose.focus({preventScroll: true});
}
function closeExplanation() {
  if (ui.analysis.hidden) return;
  ui.analysis.hidden = true;
  ui.explain.setAttribute("aria-expanded", "false");
  ui.explain.focus({preventScroll: true});
}

function setup(data) {
  roundId = data.round_id;
  args = data;
  matchCount = (data.matches || []).filter(Boolean).length;
  started = false;
  silentMode = false;
  silentStart = null;
  revealFinished = false;
  fullyFinished = false;
  firstRevealed = false;
  secondRevealed = false;
  revealed = [false, false];
  lastRoll = 0;
  locked = false;
  const prefs = soundSettings();
  localMuted = prefs.muted;
  applySound();
  ui.title.textContent = String(data.title || "선택된 뉴스");
  ui.guess.forEach((node, index) => {
    node.textContent = String(data.guess).padStart(2, "0")[index];
    node.classList.remove("hit");
  });
  ui.whole.textContent = "??";
  ui.digits.forEach(node => {
    node.textContent = "?";
    node.className = "actual-digit";
  });
  ui.progress.style.width = "0%";
  ui.wallet.hidden = true; // Balance would leak the already-settled payout.
  ui.outcome.hidden = true;
  ui.analysis.hidden = true;
  ui.explain.setAttribute("aria-expanded", "false");
  ui.start.hidden = true;
  ui.skip.hidden = true;
  ui.explain.hidden = true;
  ui.explain.textContent = "판정 이유 · 그래프 보기";
  ui.afterActions.hidden = true;
  ui.retryFail.hidden = true;
  ui.status.textContent = "AI 분석 완료 · 결과를 자동 공개합니다";
  screen.classList.remove("jackpot", "failed", "beat");
  modelDetails(data);
  for (const [name, target] of [
    ["news", ui.newsArt], ["frame", ui.frame], ["podium", ui.podium]
  ]) {
    if (typeof data.art[name] === "string") target.src = data.art[name];
  }
  if (data.art.background) {
    document.body.style.setProperty("--background", 'url("' + data.art.background + '")');
  }
  initializeTrack(data);
  applySound();
  pauseMainBgm();
  screen.hidden = false;
  start();
  send("streamlit:setFrameHeight", {height: window.innerHeight || 700});
}
ui.start.addEventListener("click", start);
ui.skip.addEventListener("click", skip);
ui.explain.addEventListener("click", openExplanation);
ui.analysisClose.addEventListener("click", closeExplanation);
ui.analysis.addEventListener("click", event => {
  if (event.target === ui.analysis) closeExplanation(); // Backdrop click.
});
document.addEventListener("keydown", event => {
  if (ui.analysis.hidden) return;
  if (event.key === "Escape") {
    event.preventDefault();
    closeExplanation();
  } else if (event.key === "Tab") {
    // The close button is the only interactive element in this dialog.
    event.preventDefault();
    ui.analysisClose.focus();
  }
});
ui.retryFail.addEventListener("click", () => {
  if (!fullyFinished || args?.win || localMuted || !failSound) return;
  ui.retryFail.hidden = true;
  playFailSound();
});
ui.again.addEventListener("click", () => sendAction("again"));
ui.home.addEventListener("click", () => sendAction("home"));
ui.soundSwitch.addEventListener("click", () => {
  localMuted = !localMuted;
  applySound();
});
document.addEventListener("visibilitychange", () => {
  if (!song || !started || fullyFinished) return;
  if (document.hidden) song.pause();
  else if (!silentMode) song.play().catch(() => {
    silentMode = true;
    silentStart = performance.now();
    ui.status.textContent = "자동 재생 제한 · 무음으로 결과 공개 중";
  });
});
window.addEventListener("pagehide", stopMedia);
window.addEventListener("message", event => {
  if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
  const data = event.data.args;
  if (!data || !data.round_id || !data.track || !data.art || !Array.isArray(data.matches)) return;
  hostOrigin = event.origin && event.origin !== "null" ? event.origin : "*";
  if (roundId !== data.round_id) setup(data); // Reruns never restart an in-flight song.
});
window.addEventListener("resize", () => {
  if (!screen.hidden) send("streamlit:setFrameHeight", {height: window.innerHeight || 700});
});
send("streamlit:componentReady", {apiVersion: 1});
