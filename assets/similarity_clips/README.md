# Similarity-analysis interstitial videos

The existing neon similarity-loading animation stays in place. Its center
newspaper comparison art receives **one randomly chosen video** when at least
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

Clips autoplay **muted** and loop during computation; native controls allow
the viewer to enable sound using a tap (mobile autoplay with sound is often
blocked). The current result flow still replaces the loader immediately
when computation completes.

Clips are served from the raw GitHub `main` asset path after merge, in the
same way as other tracked artwork. This directory is not Git LFS.
