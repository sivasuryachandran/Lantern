# Lantern concept film (about 50 s, 1920x1080, 30 fps)

A typographic concept film, drawn in HTML/CSS/JS. Every visual is a pure function of time (`window.setT(t)` in `film.html`), so frames are deterministic. It is **not** a recording of a live run and shows no real people or data.

Rebuild (needs Node, `npm i playwright`, ffmpeg and a static server on port 8123 serving the repo root):

```bash
python3 -m http.server 8123 &                       # from the repo root
mkdir -p /tmp/frames && node film/render.js /tmp/frames
# quiet ambient pad, generated in code (sine layers); drop the audio input for a silent cut
ffmpeg -f lavfi -i "sine=f=110:d=50" -f lavfi -i "sine=f=164.81:d=50" -f lavfi -i "sine=f=220:d=50" -f lavfi -i "sine=f=329.63:d=50" \
  -filter_complex "[0]volume=1.0[a];[1]volume=.55,tremolo=f=.2:d=.5[b];[2]volume=.35,tremolo=f=.13:d=.6[c];[3]volume=.12,tremolo=f=.31:d=.7[d];[a][b][c][d]amix=inputs=4:normalize=0,lowpass=f=700,volume=.12,afade=t=in:d=4,afade=t=out:st=44:d=6,aformat=channel_layouts=stereo" /tmp/pad.wav
ffmpeg -framerate 30 -i /tmp/frames/f%04d.png -i /tmp/pad.wav -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p -c:a aac -shortest -movflags +faststart film/lantern-film.mp4
```

`frames-check/` holds one frame per scene extracted from the final MP4. Audio is synthesized sine layers (no third-party audio).
