# Lantern concept film (about 50 s, 1920x1080, 30 fps)

A typographic concept film, drawn in HTML/CSS/JS. Every visual is a pure function of time (`window.setT(t)` in `film.html`), so frames are deterministic. It is **not** a recording of a live run and shows no real people or data.

Rebuild (needs Node, `npm i playwright`, ffmpeg and a static server on port 8123 serving the repo root):

```bash
python3 -m http.server 8123 &                       # from the repo root
mkdir -p /tmp/frames && node film/render.js /tmp/frames
# score: ambient pad, lantern chimes and soft effects, synthesized from sine waves and noise (needs numpy)
python3 film/score.py /tmp/score.wav
ffmpeg -framerate 30 -i /tmp/frames/f%04d.png -i /tmp/score.wav -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -shortest -movflags +faststart film/lantern-film.mp4
```

`frames-check/` holds one frame per scene extracted from the final MP4. Audio is synthesized in `score.py` (pad chords per scene, chimes on each lantern ignition, soft effects on the stamp, chart flip and handoff); mean level about -22 dB, peaks about -3 dB. No samples or third-party audio.
