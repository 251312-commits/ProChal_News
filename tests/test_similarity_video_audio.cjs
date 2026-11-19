"use strict";
const {test} = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const script = fs.readFileSync(
  path.join(__dirname, "..", "games/shared/similarity_video_controls.js"), "utf8");

class FakeVideo {
  constructor() {
    this.src = "";
    this.volume = 1;
    this.muted = false;
    this.paused = true;
    this.playCalls = 0;
    this.preload = "";
    this.loop = false;
    this.events = {};
    this.names = new Set();
    this.classList = {
      add: name => this.names.add(name),
      remove: name => this.names.delete(name),
      contains: name => this.names.has(name),
    };
  }
  load() { this.paused = true; }
  pause() { this.paused = true; }
  play() {
    this.playCalls++;
    if (this.disallowUnmuted && !this.muted) {
      return Promise.reject(new Error("NotAllowedError"));
    }
    this.paused = false;
    return Promise.resolve();
  }
  addEventListener(type, callback) { (this.events[type] ||= []).push(callback); }
  removeEventListener(type, callback) {
    this.events[type] = (this.events[type] || []).filter(fn => fn !== callback);
  }
  fire(type) { (this.events[type] || []).forEach(fn => fn()); }
}
function makeEnvironment() {
  const videos = [new FakeVideo(), new FakeVideo()];
  const clips = [
    {src:"https://example.invalid/Video1.mp4",aspect:"4 / 3"},
    {src:"https://example.invalid/Video2.mp4",aspect:"4 / 3"},
    {src:"https://example.invalid/Video3.mp4",aspect:"16 / 9"},
  ];
  videos[0].src = clips[0].src;
  videos[0].classList.add("is-active");
  let frame = {
    isConnected:true,
    dataset:{playlist:JSON.stringify(clips)},
    aspect:"4 / 3",
    style:{setProperty(_key,value) {frame.aspect = value;}},
    querySelectorAll() {return videos;}
  };
  let pref = {volume:0.09,muted:false};
  let subscriber;
  const holds = [], releases = [];
  const soundtrack = {
    getPreferences() {return pref;},
    subscribe(fn) {subscriber = fn; fn(pref); return () => {subscriber=null;};},
    hold(reason) {holds.push(reason);},
    release(reason) {releases.push(reason);},
  };
  const observers = [];
  const events = {};
  const doc = {
    body:{},
    querySelector(selector) {
      assert.equal(selector, "#pc-sim-load .pc-sim-video-frame");
      return frame?.isConnected ? frame : null;
    },
    addEventListener(type,fn) {(events[type] ||= []).push(fn);},
    removeEventListener(type,fn) {
      events[type] = (events[type] || []).filter(x=>x!==fn);
    }
  };
  const host = {
    document:doc,
    __newsSoundtrack:soundtrack,
    MutationObserver:class {
      constructor(cb) {this.cb=cb; observers.push(this);}
      observe() {}
      disconnect() {}
    },
    addEventListener() {}
  };
  const iframe = {setAttribute() {},style:{cssText:""}};
  vm.runInNewContext(script,{window:{parent:host,frameElement:iframe},Promise});
  return {
    videos, clips, holds, releases, host, soundtrack,
    changePreferences(next) {pref=next; subscriber?.(next);},
    unmount() {frame.isConnected=false; observers[0].cb();},
    gesture() {(events.pointerdown || []).forEach(fn=>fn());},
  };
}
const flush = () => new Promise(resolve => setImmediate(resolve));

test("BGM pauses while clips play in sequence and resumes only on unmount", async () => {
  const h = makeEnvironment();
  assert.deepEqual(h.holds,["similarity-interstitial"]);
  assert.equal(h.videos[0].playCalls,1);
  assert.equal(h.videos[0].src,h.clips[0].src);
  assert.equal(h.videos[0].volume,0.09);
  assert.equal(h.videos[0].muted,false);
  assert.equal(h.videos[1].src,h.clips[1].src);
  assert.deepEqual(h.releases,[]);
  h.videos[0].fire("ended");
  assert.equal(h.videos[1].src,h.clips[1].src);
  assert.equal(h.videos[1].playCalls,1);
  assert.equal(h.videos[1].classList.contains("is-active"),true);
  assert.equal(h.videos[0].src,h.clips[2].src);
  h.videos[1].fire("ended");
  assert.equal(h.videos[0].playCalls,2);
  assert.equal(h.videos[0].src,h.clips[2].src);
  assert.equal(h.videos[0].classList.contains("is-active"),true);
  assert.equal(h.host.__newsSimilarityPlayer.sync instanceof Function,true);
  h.unmount();
  assert.deepEqual(h.releases,["similarity-interstitial"]);
  assert.ok(h.videos.every(video=>video.paused));
  await flush();
});

test("Main audio bar controls video volume and mute with no independent toggle", () => {
  const h = makeEnvironment();
  h.changePreferences({volume:0.25,muted:false});
  assert.equal(h.videos[0].volume,0.25);
  assert.equal(h.videos[0].muted,false);
  h.changePreferences({volume:0,muted:true});
  assert.equal(h.videos[0].volume,0);
  assert.equal(h.videos[0].muted,true);
  h.videos[0].fire("ended");
  assert.equal(h.videos[1].muted,true);
  h.unmount();
});

test("Blocked audible autoplay falls back to muted play and a real gesture unlocks audio", async () => {
  // Construct before the playback happens using a patched video prototype.
  const original = FakeVideo.prototype.play;
  FakeVideo.prototype.play = function () {
    this.playCalls++;
    if (!this.muted) return Promise.reject(new Error("NotAllowedError"));
    this.paused=false;
    return Promise.resolve();
  };
  try {
    const h = makeEnvironment();
    await flush();
    assert.equal(h.videos[0].muted,true);
    assert.equal(h.videos[0].paused,false);
    assert.equal(h.videos[0].playCalls,2);
    h.gesture();
    assert.equal(h.videos[0].muted,false);
    h.unmount();
  } finally {
    FakeVideo.prototype.play = original;
  }
});
