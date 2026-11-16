"use strict";
// Run with: node --test tests/test_game1_result_autoplay.cjs
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.join(__dirname, "../games/game1/result_screen");
const code = fs.readFileSync(path.join(root, "result.js"), "utf8");
const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
const flush = async () => { for (let i = 0; i < 8; i++) await Promise.resolve(); };
const blocked = () => Object.assign(new Error("Autoplay denied"), {name: "NotAllowedError"});

function harness(options = {}) {
  const nodes = new Map(), groups = new Map(), frames = new Map(), audio = [], messages = [];
  let now = 0, nextFrame = 0;
  function target() {
    const handlers = new Map();
    return {
      addEventListener(type, fn) { const list = handlers.get(type) || []; list.push(fn); handlers.set(type, list); },
      emit(type, event = {}) { for (const fn of handlers.get(type) || []) fn(event); }
    };
  }
  const doc = Object.assign(target(), {hidden: false, activeElement: null});
  function node() {
    const classes = new Set();
    const result = Object.assign(target(), {
      hidden: false, textContent: "", attrs: {}, style: {setProperty() {}},
      parentElement: {setAttribute() {}},
      setAttribute(k, v) { this.attrs[k] = String(v); },
      focus() { doc.activeElement = this; },
      click() { this.emit("click", {target: this}); },
      classList: {
        add(...names) { names.forEach(n => classes.add(n)); },
        remove(...names) { names.forEach(n => classes.delete(n)); },
        toggle(n, force) { const on = force === undefined ? !classes.has(n) : force; on ? classes.add(n) : classes.delete(n); return on; }
      }
    });
    return result;
  }
  function get(selector) {
    assert.match(html, new RegExp('class="[^"\\n]*\\b' + selector.slice(1) + '\\b'), selector + " exists in HTML");
    if (!nodes.has(selector)) nodes.set(selector, node());
    return nodes.get(selector);
  }
  function all(selector) {
    get(selector);
    if (!groups.has(selector)) groups.set(selector, [node(), node()]);
    return groups.get(selector);
  }
  doc.querySelector = get; doc.querySelectorAll = all; doc.body = node();
  const screen = get(".reveal"); screen.querySelector = get; screen.querySelectorAll = all;
  screen.hidden = true; get(".analysis").hidden = true;
  const parent = {postMessage(message) { messages.push(message); }};
  parent.__newsBgmPlayer = {
    volume: options.volume ?? 0.32, muted: Boolean(options.muted),
    intro: {pause() {}}, loop: {pause() {}}
  };
  const win = Object.assign(target(), {parent, innerHeight: 667});
  class Audio {
    constructor(url) { this.url = url; this.currentTime = 0; this.playCount = 0; this.paused = true; Object.assign(this, target()); audio.push(this); }
    play() {
      this.playCount++; this.paused = false;
      if (this.url === "fail.mp3") return options.failPlay ? options.failPlay(this) : Promise.resolve();
      return options.play ? options.play(this) : Promise.resolve();
    }
    pause() { this.paused = true; }
    load() {}
  }
  vm.runInNewContext(code, {
    window: win, document: doc, Audio, console, performance: {now: () => now},
    requestAnimationFrame(fn) { const id = ++nextFrame; frames.set(id, fn); return id; },
    cancelAnimationFrame(id) { frames.delete(id); }
  }, {filename: "result.js"});
  function render(overrides = {}) {
    const data = Object.assign({round_id: "round-1", title: "기사 <제목>", summary: "AI 요약문",
      units: 8704, guess: 4, matches: [true, true], reveal_order: [0, 1], win: true,
      coins: 105000, reward: 100000, art: {}, model: {logit: 1.9, normalized: 0.87, tokens: 37},
      track: {url: "result1.mp3", drop1: 9.7, drop2: 13.2, end: 48.5}, fail_url: "fail.mp3"}, overrides);
    win.emit("message", {source: parent, origin: "https://example.test", data: {type: "streamlit:render", args: data}});
    return data;
  }
  function frame(milliseconds, position) {
    now += milliseconds;
    const current = audio.filter(a => a.url !== "fail.mp3").at(-1);
    if (position !== undefined) current.currentTime = position;
    const pending = [...frames.values()]; frames.clear(); pending.forEach(fn => fn(now));
  }
  return {get, all, render, frame, audio, frames, messages, doc, win};
}

function assertFinal(app, score = "87.04") {
  assert.equal(app.get(".outcome").hidden, false);
  assert.equal(app.get(".wallet").hidden, false);
  assert.equal(app.get(".explain").hidden, false);
  assert.equal(app.get(".after-actions").hidden, false);
  assert.equal(app.get(".analysis-score").textContent, score);
  assert.equal(app.messages.some(m => m.type === "streamlit:setComponentValue"), false);
}

test("render starts once without a button, and a same-round rerender never restarts", async () => {
  assert.doesNotMatch(html, /class="start primary"/);
  const app = harness(); app.render(); await flush();
  assert.equal(app.audio[0].playCount, 1);
  assert.equal(app.get(".outcome").hidden, true);
  assert.equal(app.get(".wallet").hidden, true);
  assert.equal(app.get(".explain").hidden, true);
  assert.equal(app.get(".skip").hidden, false);
  app.render(); await flush();
  assert.equal(app.audio.length, 2);
  assert.equal(app.audio[0].playCount, 1);
  assert.equal(app.frames.size, 1);
});

test("autoplay denial reveals on the silent timeline without another click", async () => {
  const app = harness({play: () => Promise.reject(blocked())});
  app.render(); await flush();
  assert.match(app.get(".status").textContent, /무음으로 결과 공개/);
  assert.equal(app.get(".outcome").hidden, true);
  app.frame(9700);
  assert.equal(app.all(".actual-digit")[0].textContent, "0");
  assert.equal(app.get(".outcome").hidden, true);
  app.frame(3500); assertFinal(app);
});

test("synchronous play errors use the silent timeline too", async () => {
  const app = harness({play: () => { throw new Error("Audio unavailable"); }});
  app.render(); await flush(); app.frame(13200); assertFinal(app);
});

test("allowed audio keeps both drops and the victory finale", async () => {
  const app = harness(); app.render(); await flush();
  app.frame(9700, 9.7);
  assert.equal(app.all(".actual-digit")[0].textContent, "0");
  assert.equal(app.get(".outcome").hidden, true);
  app.frame(3500, 13.2); assertFinal(app);
  assert.equal(app.audio[0].paused, false);
  app.frame(35300, 48.5);
  assert.equal(app.audio[0].paused, true);
  assert.equal(app.get(".skip").hidden, true);
});

test("zero matches complete silently without retrying blocked failure audio", async () => {
  const app = harness({play: () => Promise.reject(blocked())});
  app.render({units: 8752, matches: [false, false], win: false, reward: -1000});
  await flush(); app.frame(9581); assertFinal(app, "87.52");
  assert.equal(app.audio[1].playCount, 0);
  assert.equal(app.get(".retry-fail").hidden, true);
});

test("one match reveals its original position and fails before the second drop", async () => {
  const app = harness(); app.render({units: 8724, matches: [false, true], reveal_order: [1, 0], win: false});
  await flush(); app.frame(9700, 9.7);
  assert.equal(app.all(".actual-digit")[1].textContent, "4");
  assert.equal(app.get(".outcome").hidden, true);
  app.frame(3381, 13.081); assertFinal(app, "87.24");
  assert.equal(app.audio[0].paused, true);
  assert.equal(app.audio[1].playCount, 1);
});

test("skip and the explanation modal still work after automatic start", async () => {
  const app = harness({play: () => Promise.reject(blocked())});
  app.render(); await flush(); app.get(".skip").click(); assertFinal(app);
  app.get(".explain").click(); assert.equal(app.get(".analysis").hidden, false);
  app.get(".analysis-close").click(); assert.equal(app.get(".analysis").hidden, true);
});

test("explicit mute and zero volume remain respected", async () => {
  for (const setting of [{muted: true}, {volume: 0}]) {
    const app = harness(setting); app.render(); await flush();
    assert.equal(app.audio[0].muted, true);
    assert.equal(app.audio[0].volume, 0);
    app.frame(13200, 13.2); assertFinal(app);
  }
});
