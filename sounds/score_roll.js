// The context belongs to the persistent game window, not a Streamlit rerun.
((host) => {
  const Audio = host.AudioContext || host.webkitAudioContext;
  if (!Audio || host.__newsScoreRoll) return;
  const doc = host.document;
  let ctx, output, source, roll, chime;
  let lastStage = "", seenId = "", soundingId = "";

  function audible() {
    const p = host.__newsBgmPlayer;
    return p && !p.stopped && !p.muted && p.volume > 0 && !doc.hidden;
  }
  function unlock() {
    if (!audible()) return;
    try {
      if (!ctx) {
        ctx = new Audio();
        output = ctx.createGain();
        output.gain.value = host.__newsBgmPlayer.volume ** 2;
        output.connect(ctx.destination);
      }
      if (ctx.state !== "running") ctx.resume().catch(() => {});
    } catch (_) { /* Visual reveal still runs when audio is unavailable. */ }
  }
  function cancel() {
    soundingId = "";
    if (source) {
      source.stop();
      source.disconnect();
      source = null;
    }
  }
  function setVolume(gain) {
    if (output) output.gain.value = gain;
    if (!gain) cancel();
  }

  // Generate both short cues locally once. Each cue plays as one cancellable source.
  function cue(isRoll) {
    const rate = 24000;
    const buffer = ctx.createBuffer(1, rate * (isRoll ? 2.6 : 0.65), rate);
    const samples = buffer.getChannelData(0);
    if (isRoll) {
      for (let beat = 0; beat < 2.55; beat += 0.25 - 0.19 * beat / 2.6) {
        const start = Math.floor(beat * rate);
        const accent = 0.5 + 0.4 * beat / 2.6;
        for (let j = 0; j < rate * 0.11 && start + j < samples.length; j++) {
          const t = j / rate;
          const skin = Math.sin(2 * Math.PI * 139 * t) * Math.exp(-38 * t);
          const rattle = (2 * Math.random() - 1) * Math.exp(-52 * t);
          samples[start + j] += accent * Math.min(t * 800, 1) * (0.57 * skin + 0.43 * rattle);
        }
      }
    } else {
      for (let j = 0; j < samples.length; j++) {
        const t = j / rate;
        const tone = Math.sin(2 * Math.PI * 784 * t) + 0.45 * Math.sin(2 * Math.PI * 1175 * t);
        samples[j] = 0.44 * Math.min(t * 160, 1) * Math.exp(-8 * t) * tone;
      }
    }
    return buffer;
  }
  function play(buffer) {
    source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(output);
    source.start();
  }

  function syncStage() {
    const stage = doc.querySelector(".score-stage[data-reveal-phase][data-reveal-id]");
    const id = stage?.dataset.revealId;
    const phase = stage?.dataset.revealPhase;
    const key = stage ? id + "/" + phase : "";
    if (key === lastStage) return;
    lastStage = key;
    const finishing = id && id === soundingId && phase === "landed";
    cancel();
    if (!id || !audible() || ctx?.state !== "running") return;
    if (phase === "rolling" && seenId !== id) {
      seenId = soundingId = id;
      play(roll ||= cue(true));
    } else if (finishing) {
      play(chime ||= cue(false));
    }
  }
  host.__newsScoreRoll = {unlock, setVolume, cancel};
  doc.addEventListener("click", unlock, true);
  doc.addEventListener("keydown", unlock, true);
  doc.addEventListener("visibilitychange", () => { if (doc.hidden) cancel(); });
  host.addEventListener("pagehide", cancel);
  const observer = new host.MutationObserver(syncStage);
  observer.observe(doc.body, {childList: true, subtree: true, attributes: true,
    attributeFilter: ["data-reveal-id", "data-reveal-phase"]});
  syncStage();
})(window);
