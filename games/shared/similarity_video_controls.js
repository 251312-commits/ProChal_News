"use strict";

// Parent-document playlist controller. The launcher iframe can be discarded
// on a Streamlit rerun; the controller and its BGM hold remain stable.
(() => {
  let host, doc;
  try {
    host = window.parent;
    doc = host.document;
  } catch (_) {
    return;
  }
  const iframe = window.frameElement;
  if (iframe) {
    iframe.setAttribute("aria-hidden", "true");
    iframe.style.cssText += ";position:absolute!important;width:0!important;height:0!important;border:0!important;pointer-events:none!important;";
  }
  if (host.__newsSimilarityPlayer) {
    host.__newsSimilarityPlayer.sync();
    return;
  }

  const HOLD_ID = "similarity-interstitial";
  const state = {
    frame: null, videos: [], clips: [], active: 0, index: 0,
    bus: null, unsubscribe: null, needsGesture: false, generation: 0,
    endedHandlers: []
  };

  function preferences() {
    const current = state.bus?.getPreferences?.() ||
      host.__newsSoundtrack?.getPreferences?.();
    return current && typeof current === "object"
      ? {volume: Math.max(0, Math.min(1, Number(current.volume) || 0)),
         muted: Boolean(current.muted)}
      : {volume: 0.09, muted: false};
  }
  function live(video) {
    return state.frame?.isConnected && state.videos[state.active] === video;
  }
  function applySound() {
    if (!state.frame) return;
    const pref = preferences();
    state.videos.forEach((video, idx) => {
      video.volume = pref.volume;
      video.muted = pref.muted || idx !== state.active ||
        (idx === state.active && state.needsGesture);
    });
  }
  function startCurrent() {
    const video = state.videos[state.active];
    if (!video || !state.frame?.isConnected) return;
    state.needsGesture = false;
    applySound();
    const currentGeneration = state.generation;
    let result;
    try {
      result = video.play();
    } catch (error) {
      result = Promise.reject(error);
    }
    Promise.resolve(result).catch(() => {
      if (currentGeneration !== state.generation || !live(video)) return;
      // iOS Safari and some other browsers disallow autoplay with sound.
      // Continue the playlist muted, then unlock on the next genuine tap.
      if (preferences().muted) return;
      state.needsGesture = true;
      applySound();
      try { video.play()?.catch?.(() => {}); } catch (_) {}
    });
  }
  function preload(videoIndex, clipIndex) {
    const video = state.videos[videoIndex];
    if (!video || !state.clips.length) return;
    const clip = state.clips[clipIndex];
    video.muted = true;
    video.preload = "auto";
    video.src = clip.src;
    video.load();
  }
  function advance() {
    if (!state.frame?.isConnected || !state.clips.length) return;
    if (state.clips.length === 1) {
      const one = state.videos[state.active];
      one.currentTime = 0;
      startCurrent();
      return;
    }
    const next = 1 - state.active;
    const previous = state.videos[state.active];
    previous.pause();
    previous.classList.remove("is-active");
    state.active = next;
    state.index = (state.index + 1) % state.clips.length;
    state.frame.style.setProperty("--pc-video-aspect", state.clips[state.index].aspect);
    state.videos[next].classList.add("is-active");
    state.generation++;
    // The next media has already been loading in the hidden buffer.
    startCurrent();
    preload(1 - next, (state.index + 1) % state.clips.length);
  }
  function teardown() {
    if (!state.frame) return;
    state.generation++;
    state.videos.forEach((video, idx) => {
      video.pause();
      if (state.endedHandlers[idx]) video.removeEventListener("ended", state.endedHandlers[idx]);
    });
    state.unsubscribe?.();
    state.bus?.release?.(HOLD_ID);
    state.frame = null;
    state.videos = [];
    state.clips = [];
    state.bus = null;
    state.unsubscribe = null;
    state.endedHandlers = [];
    state.needsGesture = false;
  }
  function sync() {
    const frame = doc.querySelector("#pc-sim-load .pc-sim-video-frame");
    if (frame === state.frame) return;
    teardown();
    if (!frame) return;
    let clips = [];
    try { clips = JSON.parse(frame.dataset.playlist || "[]"); } catch (_) {}
    if (!Array.isArray(clips) || !clips.length) return;
    const videos = Array.from(frame.querySelectorAll(".pc-sim-video"));
    if (videos.length !== 2) return;
    state.frame = frame;
    state.clips = clips;
    state.videos = videos;
    state.active = 0;
    state.index = 0;
    state.generation++;
    state.bus = host.__newsSoundtrack || null;
    // Keep BGM silent during the entire video interstitial, without losing
    // its playback position or affecting the user's saved mute preference.
    state.bus?.hold?.(HOLD_ID);
    state.unsubscribe = state.bus?.subscribe?.(applySound) || null;
    videos.forEach((video, idx) => {
      const handler = () => { if (state.active === idx) advance(); };
      state.endedHandlers.push(handler);
      video.addEventListener("ended", handler);
    });
    if (clips.length === 1) videos[0].loop = true;
    else preload(1, 1);
    startCurrent();
  }
  function gesture() {
    if (!state.frame?.isConnected || !state.needsGesture || preferences().muted) return;
    const video = state.videos[state.active];
    state.needsGesture = false;
    applySound();
    // Do not rewind the clip; simply re-enable its audio under a user gesture.
    if (video.paused) startCurrent();
  }

  doc.addEventListener("pointerdown", gesture, true);
  doc.addEventListener("keydown", gesture, true);
  const observer = new host.MutationObserver(sync);
  observer.observe(doc.body, {childList: true, subtree: true});
  host.addEventListener("pagehide", () => {
    teardown();
    observer.disconnect();
    doc.removeEventListener("pointerdown", gesture, true);
    doc.removeEventListener("keydown", gesture, true);
    delete host.__newsSimilarityPlayer;
  }, {once: true});
  host.__newsSimilarityPlayer = {sync, stop: teardown};
  sync();
})();
