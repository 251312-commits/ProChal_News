import streamlit.components.v1 as components

# 정의된 함수: init_seamless_bgm

def init_seamless_bgm(intro_url: str, loop_url: str):
    components.html(
        f"""
        <script>
        (function() {{
            var pWin = window.parent;
            
            // 이미 메인 진입 후 음악이 켜져있다면 중복 실행 방지 (페이지 이동 시 음악 유지)
            if (pWin.__bgm_playing) return;

            var introAudio = new Audio('{intro_url}');
            var loopAudio = new Audio('{loop_url}');
            
            introAudio.volume = 0.3;
            loopAudio.volume = 0.3;
            loopAudio.loop = true;

            pWin.__bgm_intro = introAudio;
            pWin.__bgm_loop = loopAudio;

            // 인트로 종료 시 루프 음원으로 자동 전환
            introAudio.addEventListener('ended', function() {{
                loopAudio.play().catch(function(e) {{ console.log("Loop play error:", e); }});
            }});

            // 로그인 버튼 클릭 직후 메인으로 넘어왔으므로 즉시 재생 시도
            introAudio.play().then(function() {{
                pWin.__bgm_playing = true;
            }}).catch(function(error) {{
                // 브라우저 세션 상태에 따라 차단될 경우 첫 터치/클릭 시 재생
                var playOnTouch = function() {{
                    introAudio.play().then(function() {{
                        pWin.__bgm_playing = true;
                    }});
                    pWin.document.removeEventListener('click', playOnTouch);
                    pWin.document.removeEventListener('touchstart', playOnTouch);
                }};
                pWin.document.addEventListener('click', playOnTouch);
                pWin.document.addEventListener('touchstart', playOnTouch);
            }});
        }})();
        </script>
        """,
        height=0,
        width=0
    )

def stop_bgm():
    """로그인 화면으로 돌아갈 경우 BGM 끄기"""
    components.html(
        """
        <script>
        (function() {
            var pWin = window.parent;
            if (pWin.__bgm_intro) { pWin.__bgm_intro.pause(); pWin.__bgm_intro.currentTime = 0; }
            if (pWin.__bgm_loop) { pWin.__bgm_loop.pause(); pWin.__bgm_loop.currentTime = 0; }
            pWin.__bgm_playing = false;
        })();
        </script>
        """,
        height=0,
        width=0
    )
