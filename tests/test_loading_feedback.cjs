"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const SCRIPT = fs.readFileSync(
  path.join(__dirname, "../modules/loading_feedback.js"), "utf8"
);
const KEY = "__pcOperationLoadingV1";

function harness(enabled = true) {
  let now = 0;
  let timerSeq = 0;
  let notifyChange = () => {};
  const timers = new Map();
  const elements = new Map();
  const listeners = new Map();

  class Element {
    constructor(tag) {
      this.tag = tag;
      this.attributes = {};
      this.innerText = "";
      this.textContent = "";
      this.disabled = false;
    }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    getAttribute(key) { return this.attributes[key] || null; }
    closest(selector) {
      return this.tag === "button" &&
        (selector === "button" || selector.includes("stButton"))
        ? this : null;
    }
    addEventListener() {}
    querySelector(selector) {
      this.children = this.children || new Map();
      if (!this.children.has(selector)) this.children.set(selector, new Element("span"));
      return this.children.get(selector);
    }
    remove() { elements.delete(this.id); }
  }

  const document = {
    body: {appendChild(element) { elements.set(element.id, element); }},
    head: {appendChild(element) { elements.set(element.id, element); }},
    createElement(tag) { return new Element(tag); },
    getElementById(id) { return elements.get(id) || null; },
    querySelectorAll() { return []; },
    addEventListener(type, handler) { listeners.set(type, handler); },
  };
  const host = {
    document, Element,
    MutationObserver: class {
      constructor(fn) { notifyChange = fn; }
      observe() {}
    },
    setTimeout(fn, delay) {
      const id = ++timerSeq;
      timers.set(id, {when: now + delay, fn});
      return id;
    },
    clearTimeout(id) { timers.delete(id); },
    addEventListener() {},
  };
  vm.runInNewContext(SCRIPT, {
    window: {parent: host, frameElement: null},
    pcRunToken: "first",
    pcEnabled: enabled,
  });

  return {
    host,
    visible: () => elements.has("pc-operation-loading"),
    click(label = "베팅하기") {
      const button = new Element("button");
      button.innerText = label;
      button.textContent = label;
      const event = {
        target: button,
        prevented: false,
        stopped: false,
        preventDefault() { this.prevented = true; },
        stopImmediatePropagation() { this.stopped = true; },
      };
      listeners.get("click")(event);
      return event;
    },
    advance(milliseconds) {
      const end = now + milliseconds;
      while (true) {
        const next = [...timers].filter(([, timer]) => timer.when <= end)
          .sort((a, b) => a[1].when - b[1].when)[0];
        if (!next) break;
        now = next[1].when;
        timers.delete(next[0]);
        next[1].fn();
      }
      now = end;
    },
    showSimilarity() {
      elements.set("pc-sim-load", new Element("div"));
      notifyChange();
    },
  };
}

test("generic loading appears only after 200ms", () => {
  const ui = harness();
  ui.click();
  ui.advance(199);
  assert.equal(ui.visible(), false);
  ui.advance(1);
  assert.equal(ui.visible(), true);
  ui.host[KEY].complete("next-run", true);
  assert.equal(ui.visible(), false);
});

test("a fast successful rerun cancels the scheduled loading indicator", () => {
  const ui = harness();
  ui.click();
  ui.advance(100);
  ui.host[KEY].complete("next-run", true);
  ui.advance(500);
  assert.equal(ui.visible(), false);
});

test("login disables generic loading, including when toggled from a game", () => {
  const ui = harness(false);
  ui.click("로그인");
  ui.advance(500);
  assert.equal(ui.visible(), false);
  ui.host[KEY].complete("game-page", true);
  ui.click("베팅하기");
  ui.advance(200);
  assert.equal(ui.visible(), true);
  ui.host[KEY].complete("login-page", false);
  assert.equal(ui.visible(), false);
  ui.click("다음 (Next)");
  ui.advance(500);
  assert.equal(ui.visible(), false);
});

test("double click is blocked even during the hidden 200ms period", () => {
  const ui = harness();
  ui.click();
  const second = ui.click();
  assert.equal(second.prevented, true);
  assert.equal(second.stopped, true);
  ui.advance(200);
  assert.equal(ui.visible(), true);
});

test("similarity-analysis actions use the dedicated loading screen", () => {
  const ui = harness();
  ui.click("🤖 뉴스 유사도 분석 및 결과 확인");
  ui.click("⬆️ HIGH (이상: ≥ 50점)");
  ui.advance(500);
  assert.equal(ui.visible(), false);
  ui.click("베팅하기");
  ui.advance(200);
  assert.equal(ui.visible(), true);
  ui.showSimilarity();
  assert.equal(ui.visible(), false);
});
