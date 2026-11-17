"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ROOT = path.resolve(__dirname, "..");
const parentSource = fs.readFileSync(path.join(ROOT, "sounds/game1_result_audio.js"), "utf8");
const frontendSource = fs.readFileSync(path.join(ROOT, "games/game1/result_screen/result.js"), "utf8");
const base = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/sounds/";
const channel = "prochal:game1-result-audio-v1";
const round = "a".repeat(32);
const settle = () => new Promise(resolve => setImmediate(resolve));

class Audio {
  constructor(src) {
    this.src = src;
    this.volume = 0.09;
    this.muted = false;
    this.loop = false;
    this.currentTime = 0;
    this.ended = false;
    this.fail = false;
    this.playCalls = 0;
    this.listeners = {};
  }
  play() {
    this.playCalls++;
    return this.fail ? Promise.reject(new Error("NotAllowedError")) : Promise.resolve();
  }
  pause() { this.paused = true; }
  load() { this.currentTime = 0; }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  removeEventListener(type, fn) {
    this.listeners[type] = (this.listeners[type] || []).filter(f => f !== fn);
  }
  fire(type) { for (const cb of [...(this.listeners[type] || [])]) cb(); }
}
function parent() {
  const calls = [], messages = {}, documentEvents = {}, frames = new Map();
  const iframe = { postMessage(msg, origin) { calls.push({msg, origin}); } };
  const doc = {
    querySelector(selector) {
      return selector === ".st-key-game1-result-reveal-screen iframe"
        ? {contentWindow: iframe} : null;
    },
    addEventListener(type, fn) { (documentEvents[type] ||= []).push(fn); },
    hidden: false
  };
  const intro = new Audio(base + "intro.mp3"), loop = new Audio(base + "loop.mp3");
  intro.currentTime = 19.5;
  const player = {
    intro, loop, activeElement: intro, volume: 0.3, muted: false,
    playing: true, pending: false, stopped: false
  };
  let seq = 0;
  const host = {
    document: doc, __newsBgmPlayer: player, __newsResultActive: false,
    addEventListener(type, fn) { (messages[type] ||= []).push(fn); },
    requestAnimationFrame(fn) { frames.set(++seq, fn); return seq; },
    cancelAnimationFrame(id) { frames.delete(id); }
  };
  vm.runInNewContext(parentSource, {window: host, Promise});
  function send(action, extra={}, sender=iframe) {
    for (const fn of messages.message || []) fn({
      source: sender, origin: "https://game.example",
      data: {channel, round_id: round, action, ...extra}
    });
  }
  function last(type) {
    return calls.findLast(x => x.msg.type === type)?.msg;
  }
  function clock(seconds) {
    intro.currentTime = seconds;
    const callbacks = [...frames.values()];
    frames.clear();
    for (const callback of callbacks) callback(80);
  }
  return {send, last, clock, intro, loop, player, host, iframe, calls, doc};
}
function element() {
  const attrs = {}, listeners = {}, classes = new Set();
  return {
    hidden: false, textContent: "", className: "", offsetWidth: 90,
    attrs, style: {setProperty() {}}, parentElement: {setAttribute() {}},
    classList: {
      add(...names) { names.forEach(n => classes.add(n)); },
      remove(...names) { names.forEach(n => classes.delete(n)); },
      toggle(name, flag) { (flag ? classes.add(name) : classes.delete(name)); },
      contains(name) { return classes.has(name); }
    },
    setAttribute(k,v) { attrs[k] = String(v); },
    getAttribute(k) { return attrs[k]; },
    focus() {},
    addEventListener(type,fn) { (listeners[type] ||= []).push(fn); },
    click() { for (const fn of listeners.click || []) fn({target:this}); }
  };
}
function frontend({blockedLocal=false, guess=4, units=8704}={}) {
  const nodes={}, arrays={}, docListeners={}, windowListeners={}, calls=[];
  const frames = new Map();
  let seq = 0, now = 1000;
  const get = selector => nodes[selector] ||= element();
  const getAll = selector => arrays[selector] ||= [element(), element()];
  const screen = get(".reveal");
  screen.hidden = true;
  screen.querySelector = get;
  screen.querySelectorAll = getAll;
  get(".analysis").hidden = true;
  const doc = {
    querySelector: get, querySelectorAll: getAll,
    body: {style: {setProperty() {}}},
    hidden: false,
    addEventListener(type,fn) { (docListeners[type] ||= []).push(fn); }
  };
  const parent = {
    __newsBgmPlayer: {volume:.3, muted:false, intro:{pause(){}}, loop:{pause(){}}},
    postMessage(message) { calls.push(message); }
  };
  const win = {
    parent, innerHeight:760,
    addEventListener(type,fn) { (windowListeners[type] ||= []).push(fn); }
  };
  const tracks = [];
  class LocalAudio extends Audio {
    constructor(url) { super(url); this.fail = blockedLocal; tracks.push(this); }
  }
  const raf = fn => {frames.set(++seq, fn);return seq;};
  const cancel = id => frames.delete(id);
  vm.runInNewContext(frontendSource, {
    window:win, document:doc, Audio:LocalAudio,
    requestAnimationFrame:raf, cancelAnimationFrame:cancel,
    performance:{now:()=>now}, Promise
  });
  const predicted = String(guess).padStart(2,"0");
  const actual = String(units % 100).padStart(2,"0");
  const matches = [0,1].map(i=>predicted[i]===actual[i]);
  const args = {
    round_id:round,title:"기사 제목",summary:"AI 요약문",
    guess,units,matches,win:matches.every(Boolean),reward:5000,coins:8500,
    track:{url:base+"result1.mp3",drop1:9.7,drop2:13.2,end:48.5},
    fail_url:base+"fail.mp3",art:{},model:{name:"BGE",logit:1,normalized:.73,tokens:30},
    reveal_order:[0,1]
  };
  function dispatch(data) {
    for (const fn of windowListeners.message || [])
      fn({data,source:parent,origin:"https://game.example"});
  }
  function start() {dispatch({type:"streamlit:render",args});}
  function audio(type,extra={}) {dispatch({channel,round_id:round,type,...extra});}
  function advance(newNow) {
    now=newNow;
    const callbacks=[...frames.values()];
    frames.clear();
    for (const callback of callbacks) callback(now);
  }
  return {start,audio,advance,get,getAll,calls,tracks,args};
}
test("Result bridge takes over the *already used* parent BGM media", async () => {
  const h=parent();
  h.send("start", {track_url:base+"result1.mp3", fail_url:base+"fail.mp3"});
  await settle();
  assert.equal(h.intro.src, base+"result1.mp3");
  assert.equal(h.player.resultBorrowed,h.intro);
  assert.equal(h.intro.playCalls,1);
  assert.equal(h.last("playing").seconds,0);
  h.clock(9.7);
  assert.equal(h.last("time").seconds,9.7);
  h.send("mute",{muted:true});
  assert.equal(h.intro.muted,true);
  h.send("fail");
  await settle();
  assert.equal(h.intro.src,base+"fail.mp3");
  assert.ok(h.last("fail-playing"));
  h.send("stop");
  assert.equal(h.intro.src,base+"intro.mp3");
  assert.equal(h.player.resultBorrowed,null);
  assert.equal(h.intro.volume,0.09);
  assert.equal(h.intro.muted,false);
});
test("Untrusted iframes or unexpected audio URLs cannot take over BGM", () => {
  const h=parent();
  h.send("start", {track_url:base+"result1.mp3",fail_url:base+"fail.mp3"}, {});
  h.send("start", {track_url:"https://evil.example/track.mp3",fail_url:base+"fail.mp3"});
  assert.equal(h.intro.playCalls,0);
  assert.equal(h.intro.src,base+"intro.mp3");
});
test("Blocked parent autoplay reports the error and restores the BGM", async () => {
  const h=parent();
  h.intro.fail=true;
  h.send("start",{track_url:base+"result2.mp3",fail_url:base+"fail.mp3"});
  await settle();
  assert.equal(h.last("blocked").reason,"autoplay");
  assert.equal(h.intro.src,base+"intro.mp3");
  assert.equal(h.player.resultBorrowed,null);
});
test("Winning result starts automatically, follows parent clock and keeps result gated", () => {
  const h=frontend();
  h.start();
  assert.ok(h.calls.find(c=>c.action==="start"));
  assert.equal(h.get(".wallet").hidden,true);
  h.audio("loading",{muted:false});
  h.audio("playing",{seconds:0,muted:false});
  h.audio("time",{seconds:9.7});
  h.advance(1200);
  assert.equal(h.getAll(".actual-digit")[0].textContent,"0");
  assert.equal(h.get(".outcome").hidden,true);
  h.audio("time",{seconds:13.2});
  h.advance(1300);
  assert.equal(h.getAll(".actual-digit")[1].textContent,"4");
  assert.equal(h.get(".outcome").hidden,false);
  assert.equal(h.get(".wallet").hidden,false);
  assert.equal(h.get(".unblock-audio").hidden,true);
  h.start();
  assert.equal(h.calls.filter(c=>c.action==="start").length,1);
});
test("When both autoplay paths are blocked, a real fallback button can play", async () => {
  const h=frontend({blockedLocal:true});
  h.start();
  h.audio("blocked");
  await settle();
  assert.equal(h.get(".unblock-audio").hidden,false);
  h.tracks[0].fail=false;
  h.get(".unblock-audio").click();
  await settle();
  assert.equal(h.get(".unblock-audio").hidden,true);
  assert.equal(h.tracks[0].playCalls,2);
});
test("Loss cuts borrowed song before first drop and can retry blocked stinger", () => {
  const h=frontend({guess:33,units:8704});
  h.start();
  h.audio("playing",{seconds:0});
  h.audio("time",{seconds:9.58});
  h.advance(1200);
  assert.equal(h.get(".outcome").hidden,false);
  assert.ok(h.calls.find(c=>c.action==="fail"));
  h.audio("fail-blocked");
  assert.equal(h.get(".retry-fail").hidden,false);
});
test("Bootstrap installs controller once and never pauses a borrowed media on rerun", () => {
  const bgm=fs.readFileSync(path.join(ROOT,"sounds/bgm.py"),"utf8");
  assert.match(bgm,/game1_result_audio\.js/);
  assert.match(bgm,/if \(!host\.__newsGame1ResultPlayer\)/);
  assert.match(bgm,/isBorrowed\(player\.intro\)/);
  assert.match(bgm,/isBorrowed\(player\.loop\)/);
});
