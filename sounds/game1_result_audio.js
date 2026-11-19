/* Game 1 result soundtrack uses the same persistent, previously gesture-activated
 * HTMLAudioElement as the site's BGM (rather than a new iframe Audio).
 * Messages are accepted ONLY from the current Game 1 result iframe. */
(function (host) {
  "use strict";
  if (host.__newsGame1ResultPlayer) return;
  const doc = host.document;
  const CHANNEL = "prochal:game1-result-audio-v1";
  const SOUND_ROOT = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/sounds/";
  const TRACK_URL = /^https:\/\/raw\.githubusercontent\.com\/251312-commits\/ProChal_News\/main\/sounds\/result[1-5]\.mp3$/;
  let active = null;
  let clock = 0;
  let lastTick = 0;

  function send(entry, type, extra) {
    try {
      entry.frame.postMessage(Object.assign({
        channel: CHANNEL, type: type, round_id: entry.roundId
      }, extra || {}), entry.origin);
    } catch (_) { /* A closing iframe is no longer listening. */ }
  }
  function stopClock() {
    if (clock) host.cancelAnimationFrame(clock);
    clock = 0;
  }
  function timePulse(now) {
    clock = 0;
    if (!active || active.phase !== "track" || active.state !== "playing") return;
    if (now - lastTick >= 34) {
      send(active, "time", {seconds: active.media.currentTime});
      lastTick = now;
    }
    clock = host.requestAnimationFrame(timePulse);
  }
  function restore(entry) {
    if (!entry || entry.restored) return;
    entry.restored = true;
    stopClock();
    const audio = entry.media;
    audio.pause();
    audio.removeEventListener("ended", entry.ended);
    audio.removeEventListener("error", entry.error);
    // Restore the BGM source, position and settings before the next Streamlit rerun.
    audio.loop = entry.original.loop;
    audio.muted = entry.original.muted;
    audio.volume = entry.original.volume;
    audio.src = entry.original.src;
    audio.load();
    if (entry.original.position > 0 && Number.isFinite(entry.original.position)) {
      const restorePosition = () => {
        try { audio.currentTime = entry.original.position; } catch (_) {}
      };
      audio.addEventListener("loadedmetadata", restorePosition, {once: true});
      restorePosition();
    }
    if (entry.player.resultBorrowed === audio) entry.player.resultBorrowed = null;
    if (active === entry) active = null;
  }
  function error(entry) {
    if (entry !== active || entry.restored) return;
    send(entry, entry.phase === "fail" ? "fail-blocked" : "blocked",
      {reason: "file"});
    restore(entry);
  }
  function play(entry, phase) {
    entry.phase = phase;
    entry.state = "loading";
    const media = entry.media;
    let promise;
    try { promise = media.play(); }
    catch (err) { promise = Promise.reject(err); }
    Promise.resolve(promise).then(() => {
      if (active !== entry || entry.restored || entry.phase !== phase) return;
      entry.state = "playing";
      send(entry, phase === "fail" ? "fail-playing" : "playing", {
        seconds: media.currentTime, muted: media.muted
      });
      if (phase === "track") {
        stopClock();
        lastTick = 0;
        clock = host.requestAnimationFrame(timePulse);
      }
    }).catch(() => {
      if (active !== entry || entry.restored || entry.phase !== phase) return;
      send(entry, phase === "fail" ? "fail-blocked" : "blocked",
        {reason: "autoplay"});
      restore(entry);
    });
  }
  function start(event, data) {
    const origin = event.origin && event.origin !== "null" ? event.origin : "*";
    const reply = {frame: event.source, origin: origin, roundId: data.round_id};
    if (!TRACK_URL.test(String(data.track_url)) ||
        data.fail_url !== SOUND_ROOT + "fail.mp3") return;
    if (active) {
      if (active.roundId === data.round_id && active.frame === event.source) {
        send(active, active.state === "playing" ? "playing" : "loading", {
          seconds: active.media.currentTime, muted: active.media.muted
        });
        return;
      }
      restore(active);
    }
    const player = host.__newsBgmPlayer;
    if (!player || player.stopped) {
      send(reply, "unavailable");
      return;
    }
    const media = player.activeElement === player.loop ||
      player.activeElement === player.intro ? player.activeElement :
      (player.intro.ended ? player.loop : player.intro);
    const entry = {
      frame: event.source, origin: origin, roundId: data.round_id,
      player: player, media: media, phase: "track", state: "loading",
      restored: false, userMuted: Boolean(player.muted) || player.volume <= 0,
      original: {
        src: media.src, position: media.currentTime, volume: media.volume,
        muted: media.muted, loop: media.loop
      }
    };
    entry.ended = () => {
      if (active !== entry || entry.restored) return;
      if (entry.phase === "track") send(entry, "ended", {seconds: media.currentTime});
      else send(entry, "fail-ended");
      restore(entry);
    };
    entry.error = () => error(entry);
    active = entry;
    host.__newsResultActive = true;
    // Pause the other BGM element. The borrowed one keeps its browser
    // playback permission and must not be paused by BGM rerendering.
    player.intro.pause();
    player.loop.pause();
    player.pending = false;
    player.playing = false;
    host.__bgm_playing = false;
    player.resultBorrowed = media;
    media.addEventListener("ended", entry.ended);
    media.addEventListener("error", entry.error);
    media.src = data.track_url;
    media.loop = false;
    media.preload = "auto";
    media.volume = Math.min(1, Math.max(0, player.volume ** 2 * 1.7));
    media.muted = entry.userMuted;
    media.load();
    send(entry, "loading", {muted: media.muted});
    play(entry, "track");
  }
  function setPreferences(prefs) {
    if (!active || active.restored) return;
    const volume = Math.max(0, Math.min(1, Number(prefs?.volume) || 0));
    active.userMuted = Boolean(prefs?.muted) || volume <= 0;
    active.media.muted = active.userMuted;
    active.media.volume = active.phase === "fail"
      ? Math.min(1, Math.sqrt(volume) * 2)
      : Math.min(1, volume * 1.7);
    send(active, "sound", {muted: active.userMuted, volume: volume});
  }
  function message(event) {
    const data = event.data;
    if (!data || data.channel !== CHANNEL || typeof data.round_id !== "string") return;
    // Only the actual iframe within the result screen may control audio.
    const frame = doc.querySelector(".st-key-game1-result-reveal-screen iframe");
    if (!frame || event.source !== frame.contentWindow) return;
    if (data.action === "start") {
      start(event, data);
      return;
    }
    const entry = active;
    if (!entry || entry.frame !== event.source || entry.roundId !== data.round_id) return;
    if (data.action === "stop") {
      restore(entry);
    } else if (data.action === "fail" && entry.phase === "track") {
      stopClock();
      entry.media.pause();
      entry.media.src = SOUND_ROOT + "fail.mp3";
      entry.media.loop = false;
      entry.media.volume = Math.min(1, Math.max(0, entry.player.volume * 2));
      entry.media.muted = entry.userMuted;
      entry.media.load();
      play(entry, "fail");
    }
  }
  function stop() { if (active) restore(active); }
  host.addEventListener("message", message);
  host.addEventListener("pagehide", stop);
  doc.addEventListener("visibilitychange", () => {
    if (!active) return;
    if (doc.hidden) {
      active.media.pause();
      active.state = "paused";
      stopClock();
      send(active, "paused", {seconds: active.media.currentTime});
    } else if (active.phase === "track" && active.state === "paused") {
      play(active, "track");
    }
  });
  host.__newsGame1ResultPlayer = {
    isBorrowed: audio => Boolean(active && active.media === audio && !active.restored),
    setPreferences: setPreferences,
    stop: stop
  };
})(window);
