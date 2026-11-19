# Similarity-analysis interstitial videos

The existing neon similarity-loading animation stays in place. Its center
newspaper comparison art receives **a rotating sequence of available videos** when at least
one of the following local assets exists:

- `Video1.mp4` — approx. 14.8 s, 4:3
- `Video2.mp4` — approx. 13.9 s, 4:3
- `Video3.mp4` — approx. 11.5 s, 16:9

Each is an H.264/AAC MP4. The compressed copies supplied alongside this
change are about 230–260 KB each (about 730 KB for all three).

**Install:** Upload the three optimized MP4 files directly into this folder on
the PR branch using GitHub's **Add file → Upload files**. A zip archive cannot
be uploaded as-is: GitHub does not automatically unpack it.

The loader selects only locally present files, so it safely falls back to its
original two-newspaper artwork until one or more MP4s are checked in.

All installed clips play in sequence, starting at a random clip. Two video elements
are used so the next clip preloads while the current one plays; videos continue
until similarity analysis finishes. The rest of the analysis screen remains
unchanged.

The parent BGM is paused while the video area is mounted and resumes from its
saved position when the analysis screen disappears. The main-page
**음악·영상** volume/mute controls govern BGM, these clips and Game 1 result
music. There is no separate video mute button. Video audio is requested by
default when the user has not muted the site. iOS Safari and similar browsers
may reject audible autoplay despite this setting: the video then continues
muted until the next actual user interaction can enable audio. A browser's
autoplay restriction cannot be bypassed reliably by JavaScript.

Clips are served from the raw GitHub `main` asset path after merge, in the
same way as other tracked artwork. This directory is not Git LFS.
