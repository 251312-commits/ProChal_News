"""Persistent browser BGM with main-page-only volume and mute controls.

The audio elements live on Streamlit's parent window to survive reruns, while
the compact controls live in that window's DOM only on the main page.
"""
import json
from pathlib import Path

import streamlit.components.v1 as components

_SCORE_ROLL_JS = json.dumps(Path(__file__).with_name("score_roll.js").read_text(encoding="utf-8"))


def init_seamless_bgm(intro_url: str, loop_url: str, show_controls: bool = False, suspend_for_result: bool = False):
    intro = json.dumps(intro_url)
    loop = json.dumps(loop_url)
    visible = "true" if show_controls else "false"
    suspended = "true" if suspend_for_result else "false"
    components.html(
        f"""
        <script>
        (function () {{
          const host = window.parent;
          const doc = host.document;
          const introURL = {intro};
          const loopURL = {loop};
          const onMain = {visible};
          // A Game 1 result song owns the soundtrack until its screen closes.
          const suppressForResult = {suspended};
          host.__newsResultActive = suppressForResult;
          const jsFrame = window.frameElement;
          if (jsFrame) {{
            jsFrame.setAttribute("aria-hidden", "true");
            jsFrame.style.cssText += ";position:absolute!important;width:0!important;height:0!important;border:0!important;pointer-events:none!important;";
          }}
          const CONTROL_ID = "news-bgm-controls";
          const STYLE_ID = "news-bgm-controls-style";
          const STORAGE_KEY = "news-bgm-preferences-v1";

          const clamp = (v) => Math.max(0, Math.min(1, Number(v) || 0));

          function getPrefs() {{
            try {{
              const saved = JSON.parse(host.sessionStorage.getItem(STORAGE_KEY) || "{{}}");
              return {{
                volume: Number.isFinite(Number(saved.volume)) ? clamp(saved.volume) : 0.3,
                muted: saved.muted === true
              }};
            }} catch (_) {{
              return {{volume: 0.3, muted: false}};
            }}
          }}

          function savePrefs(player) {{
            try {{
              host.sessionStorage.setItem(STORAGE_KEY,
                JSON.stringify({{volume: player.volume, muted: player.muted}}));
            }} catch (_) {{}}
          }}

          // Audio.volume is linear in signal amplitude, while human loudness
          // perception is closer to logarithmic. Square the slider fraction
          // so 10%, 30%, and 60% sound distinctly quieter than 100%.
          function volumeGain(sliderValue) {{
            const level = clamp(sliderValue);
            return level * level;
          }}

          function updateAudio(player) {{
            const gain = player.muted ? 0 : volumeGain(player.volume);
            player.intro.volume = gain;
            player.loop.volume = gain;
            host.__newsScoreRoll?.setVolume(gain);
          }}

          function stop(player) {{
            player.intro.pause();
            player.loop.pause();
            player.intro.currentTime = 0;
            player.loop.currentTime = 0;
            player.playing = false;
            player.pending = false;
            player.stopped = true;
            host.__bgm_playing = false;
          }}

          function start(player) {{
            if (player.stopped || player.muted || player.volume <= 0 ||
                host.__newsResultActive || doc.visibilityState === "hidden") return;
            if (player.playing || player.pending) return;
            player.pending = true;
            const selected = player.intro.ended ? player.loop : player.intro;
            selected.play().then(() => {{
              player.pending = false;
              if (player.stopped || player.muted || player.volume <= 0 ||
                  host.__newsResultActive || doc.visibilityState === "hidden") {{
                selected.pause();
                player.playing = false;
                host.__bgm_playing = false;
                return;
              }}
              player.playing = true;
              host.__bgm_playing = true;
            }}).catch(() => {{
              // Autoplay is gated until a user gesture. Never restart muted music.
              player.pending = false;
              player.playing = false;
              host.__bgm_playing = false;
            }});
          }}

          function applyPrefs(player, volume, muted) {{
            player.volume = clamp(volume);
            player.muted = Boolean(muted);
            player.stopped = false;
            updateAudio(player);
            savePrefs(player);
            if (player.muted || player.volume === 0) {{
              player.intro.pause();
              player.loop.pause();
              player.pending = false;
              player.playing = false;
              host.__bgm_playing = false;
            }} else {{
              start(player);
            }}
          }}

          let player = host.__newsBgmPlayer;
          if (!player || player.introURL !== introURL || player.loopURL !== loopURL) {{
            if (player) {{
              stop(player);
              if (player.listeners) {{
                doc.removeEventListener("pointerdown", player.listeners.gesture);
                doc.removeEventListener("keydown", player.listeners.gesture);
                doc.removeEventListener("visibilitychange", player.listeners.visibility);
                host.removeEventListener("pagehide", player.listeners.teardown);
                host.removeEventListener("beforeunload", player.listeners.teardown);
              }}
            }}
            const prefs = getPrefs();
            const introAudio = new host.Audio(introURL);
            const loopAudio = new host.Audio(loopURL);
            introAudio.preload = "auto";
            loopAudio.preload = "auto";
            loopAudio.loop = true;
            player = {{
              intro: introAudio, loop: loopAudio, introURL, loopURL,
              volume: prefs.volume, muted: prefs.muted,
              playing: false, pending: false, stopped: false
            }};
            host.__newsBgmPlayer = player;
            host.__bgm_intro = introAudio;
            host.__bgm_loop = loopAudio;
            updateAudio(player);
            introAudio.addEventListener("ended", () => {{
              if (player.stopped || player.muted || player.volume === 0 ||
                  host.__newsResultActive || doc.visibilityState === "hidden") return;
              loopAudio.play().then(() => {{
                player.playing = true;
                host.__bgm_playing = true;
              }}).catch(() => {{
                player.playing = false;
                host.__bgm_playing = false;
              }});
            }});

            // Gesture handlers are attached exactly once to the persistent parent.
            const gesture = () => {{
              if (host.__newsBgmPlayer === player) start(player);
            }};
            doc.addEventListener("pointerdown", gesture, {{passive: true}});
            doc.addEventListener("keydown", gesture);
            player.listeners = {{gesture}};
            const visibility = () => {{
              if (doc.visibilityState === "hidden") {{
                player.intro.pause();
                player.loop.pause();
                player.playing = false;
                host.__bgm_playing = false;
              }} else if (!player.stopped && !host.__newsResultActive) {{
                start(player);
              }}
            }};
            doc.addEventListener("visibilitychange", visibility);
            player.listeners.visibility = visibility;
            const teardown = () => stop(player);
            host.addEventListener("pagehide", teardown);
            host.addEventListener("beforeunload", teardown);
            player.listeners.teardown = teardown;
          }}
          player.stopped = false;
          updateAudio(player);
          // Streamlit reruns update the UI, never create duplicate audio tracks.
          if (player.muted || player.volume <= 0 || host.__newsResultActive) {{
            player.intro.pause();
            player.loop.pause();
            player.playing = false;
            host.__bgm_playing = false;
          }} else {{
            start(player);
          }}

          // Install in the app document so gesture and DOM callbacks outlive this iframe.
          if (!host.__newsScoreRoll) {{
            const controller = doc.createElement("script");
            controller.textContent = {_SCORE_ROLL_JS};
            doc.head.appendChild(controller).remove();
          }}

          let style = doc.getElementById(STYLE_ID);
          if (!style) {{
            style = doc.createElement("style");
            style.id = STYLE_ID;
            style.textContent = `
              #news-bgm-controls {{
                position: fixed; top: max(12px,env(safe-area-inset-top));
                right: max(14px,env(safe-area-inset-right));
                z-index: 2147483000; color: #f6e8ff; font: 500 13px/1.2 system-ui,sans-serif;
              }}
              #news-bgm-controls * {{ box-sizing: border-box; }}
              #news-bgm-controls .news-bgm-toggle {{
                width: 39px; height: 39px; display: grid; place-items: center;
                border-radius: 50%; cursor: pointer; border: 1px solid #a77abf9c;
                background: #180b25d9; color: #f7e9ff;
                box-shadow: 0 2px 9px #08020c69; backdrop-filter: blur(10px);
              }}
              #news-bgm-controls svg {{ width: 19px; height: 19px; fill: none; stroke: currentColor;
                stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }}
              #news-bgm-controls .news-bgm-panel {{
                position: absolute; top: 46px; right: 0; width: 216px;
                padding: 13px 12px 12px; border-radius: 13px;
                border: 1px solid #a57db88a; background: #1b1026f0;
                box-shadow: 0 9px 25px #0008; backdrop-filter: blur(15px);
              }}
              #news-bgm-controls .news-bgm-panel[hidden] {{ display: none; }}
              #news-bgm-controls .news-bgm-caption {{ display:flex; justify-content:space-between;
                align-items: center; margin-bottom: 12px; font-size: 12px; }}
              #news-bgm-controls .news-bgm-slider {{ width: 100%; height: 24px; margin: 0;
                accent-color: #b86beb; cursor: pointer; }}
              #news-bgm-controls .news-bgm-mute {{ display: flex; align-items: center; gap: 8px;
                margin-top: 9px; font-size: 12px; cursor: pointer; }}
              #news-bgm-controls .news-bgm-mute input {{ accent-color: #a862e0; width: 16px;
                height: 16px; }}
              #news-bgm-controls .news-bgm-toggle:focus-visible,
              #news-bgm-controls input:focus-visible {{ outline: 2px solid #ffe99b; outline-offset: 3px; }}
              @media (max-width: 450px) {{
                #news-bgm-controls {{ top: max(8px,env(safe-area-inset-top));
                  right: max(10px,env(safe-area-inset-right)); }}
                #news-bgm-controls .news-bgm-toggle {{ width: 35px; height: 35px; }}
              }}
            `;
            doc.head.appendChild(style);
          }}

          const soundIcon = '<svg viewBox="0 0 24 24" aria-hidden="true">' +
            '<path d="M11 5 6.5 9H3v6h3.5L11 19V5Z"/>' +
            '<path d="M15 9a5 5 0 0 1 0 6M18 6a9 9 0 0 1 0 12"/></svg>';
          const mutedIcon = '<svg viewBox="0 0 24 24" aria-hidden="true">' +
            '<path d="M11 5 6.5 9H3v6h3.5L11 19V5Z"/>' +
            '<path d="m16 9 5 6m0-6-5 6"/></svg>';
          let root = doc.getElementById(CONTROL_ID);
          if (!onMain) {{
            if (root) root.remove();
            return;
          }}
          if (!root) {{
            root = doc.createElement("div");
            root.id = CONTROL_ID;
            root.innerHTML =
              '<button class="news-bgm-toggle" type="button" aria-label="음악 음량 조절" aria-expanded="false"></button>' +
              '<div class="news-bgm-panel" hidden>' +
                '<div class="news-bgm-caption"><span>배경음악</span><output class="news-bgm-value"></output></div>' +
                '<input class="news-bgm-slider" type="range" min="0" max="100" step="1" aria-label="배경음악 음량">' +
                '<label class="news-bgm-mute"><input type="checkbox"> 음악 끄기</label>' +
              '</div>';
            doc.body.appendChild(root);
            const toggle = root.querySelector(".news-bgm-toggle");
            const panel = root.querySelector(".news-bgm-panel");
            const range = root.querySelector(".news-bgm-slider");
            const mute = root.querySelector(".news-bgm-mute input");
            toggle.addEventListener("click", (event) => {{
              event.stopPropagation();
              const open = panel.hidden;
              panel.hidden = !open;
              toggle.setAttribute("aria-expanded", String(open));
            }});
            doc.addEventListener("pointerdown", (event) => {{
              if (!root.isConnected || root.contains(event.target)) return;
              panel.hidden = true;
              toggle.setAttribute("aria-expanded", "false");
            }});
            range.addEventListener("input", () => {{
              const current = host.__newsBgmPlayer;
              if (!current) return;
              // Moving the slider off zero is an explicit request to unmute.
              applyPrefs(current, Number(range.value) / 100, Number(range.value) === 0);
              refresh();
            }});
            mute.addEventListener("change", () => {{
              const current = host.__newsBgmPlayer;
              if (!current) return;
              applyPrefs(current, current.volume, mute.checked);
              refresh();
            }});
          }}
          function refresh() {{
            const current = host.__newsBgmPlayer;
            if (!current || !root.isConnected) return;
            root.querySelector(".news-bgm-toggle").innerHTML = (current.muted || current.volume === 0)
              ? mutedIcon : soundIcon;
            root.querySelector(".news-bgm-slider").value = Math.round(current.volume * 100);
            root.querySelector(".news-bgm-mute input").checked = current.muted || current.volume === 0;
            root.querySelector(".news-bgm-value").textContent =
              (current.muted || current.volume === 0) ? "꺼짐" : Math.round(current.volume * 100) + "%";
          }}
          refresh();
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


def stop_bgm():
    """Stop when returning to login; leaving the site triggers pagehide."""
    components.html(
        """
        <script>
        (function () {
          var host = window.parent;
          host.__newsScoreRoll?.cancel();
          var player = host.__newsBgmPlayer;
          if (player) {
            player.stopped = true;
            player.intro.pause();
            player.loop.pause();
            player.intro.currentTime = 0;
            player.loop.currentTime = 0;
            player.playing = false;
            player.pending = false;
          }
          if (host.__bgm_intro) host.__bgm_intro.pause();
          if (host.__bgm_loop) host.__bgm_loop.pause();
          host.__bgm_playing = false;
          var root = host.document.getElementById("news-bgm-controls");
          if (root) root.remove();
        })();
        </script>
        """,
        height=0,
        width=0,
    )
