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
  analysis: screen.querySelector(".analysis"),
  summary: screen.querySelector(".analysis-summary"),
  logit: screen.querySelector(".analysis-logit"),
  normalized: screen.querySelector(".analysis-normalized"),
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
  playFailSound();
}
function tick() {
  if (!started || fullyFinished || !args || !song) return;
  const position = song.currentTime;
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
  const pending = song.play(); // Prioritize the soundtrack's user-gesture unlock.
  primeFailSound(); // Pre-unlock the loss stinger in that same click handler.
  if (pending && typeof pending.catch === "function") {
    pending.catch(() => {
      if (!fullyFinished) {
        ui.status.textContent = "오디오 재생이 차단되었습니다.";
        skip(); // Never leave the player waiting through a silent 48 s track.
      }
    });
  }
  animationFrame = requestAnimationFrame(tick);
}
function modelDetails(data) {
  const model = data.model || {};
  ui.summary.textContent = data.summary || "AI 요약문이 저장되지 않았습니다.";
  ui.logit.textContent = (model.logit == null ? "원점수 기록 없음" :
    "관련성 원점수 " + Number(model.logit).toFixed(4)) +
    " · " + String(model.name || "BGE reranker") +
    (model.tokens == null ? "" : " · " + Number(model.tokens) + "토큰");
  ui.normalized.textContent = model.normalized == null ?
    "최종 유사도 " + (Number(data.units) / 100).toFixed(2) + "점" :
    "σ(원점수) = " + Number(model.normalized).toFixed(6) +
    " → × 100 → " + (Number(data.units) / 100).toFixed(2) + "점";
}
function setup(data) {
  roundId = data.round_id;
  args = data;
  matchCount = (data.matches || []).filter(Boolean).length;
  started = false;
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
  ui.start.hidden = false;
  ui.skip.hidden = true;
  ui.explain.hidden = true;
  ui.explain.textContent = "AI 판단 과정 보기";
  ui.afterActions.hidden = true;
  ui.retryFail.hidden = true;
  ui.status.textContent = "결과를 공개하려면 버튼을 누르세요.";
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
  send("streamlit:setFrameHeight", {height: window.innerHeight || 700});
}
ui.start.addEventListener("click", start);
ui.skip.addEventListener("click", skip);
ui.explain.addEventListener("click", () => {
  if (!revealFinished) return;
  ui.analysis.hidden = !ui.analysis.hidden;
  ui.explain.textContent = ui.analysis.hidden ? "AI 판단 과정 보기" : "AI 판단 과정 닫기";
  if (!ui.analysis.hidden) ui.analysis.scrollIntoView({behavior: "smooth", block: "nearest"});
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
  else song.play().catch(() => {
    ui.status.textContent = "다시 재생하려면 연출 건너뛰기를 눌러주세요.";
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
