#!/usr/bin/env bash
# Mix narration (voice/seg1..7.mp3) over the synthesized score, score ducked under the voice, then mux into the film.
# usage: film/mix.sh score.wav   (run from the repo root after film/voice.py and film/score.py)
set -euo pipefail
cd "$(dirname "$0")"
SCORE="$1"
STARTS_MS=(2600 8000 15400 24600 31600 38400 45600)
ARGS=(); FC=""; MIX=""
for i in 1 2 3 4 5 6 7; do
  ms="${STARTS_MS[$((i-1))]}"
  ARGS+=(-i "voice/seg$i.mp3")
  FC+="[$((i-1)):a]aresample=44100,aformat=channel_layouts=stereo,adelay=${ms}|${ms}[v$i];"
  MIX+="[v$i]"
done
FC+="${MIX}amix=inputs=7:normalize=0,apad=whole_dur=50,atrim=0:50,loudnorm=I=-16:TP=-2:LRA=7[voice];"
FC+="[7:a]volume=0.85[score];[voice]asplit=2[vm][vsc];[score][vsc]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=500[ducked];"
FC+="[vm][ducked]amix=inputs=2:normalize=0,alimiter=limit=0.89[out]"
ffmpeg -y -loglevel error "${ARGS[@]}" -i "$SCORE" -filter_complex "$FC" -map "[out]" -t 50 /tmp/lantern-mix.wav
ffmpeg -y -loglevel error -i lantern-film.mp4 -i /tmp/lantern-mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 160k -t 50 -movflags +faststart /tmp/lantern-film-vo.mp4
mv /tmp/lantern-film-vo.mp4 lantern-film.mp4
