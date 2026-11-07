"""Draft narration for the 3-minute demo via Google Cloud Text-to-Speech (Chirp 3: HD, Orus), same setup as film/voice.py.
A scratch track to time the edit against; the script prefers a human voice for the final cut. Beats run at natural pace: any that would overlap the previous one start later (the report shows the drift).

  LANTERN_TTS_PROJECT=<project> [AGENT_PROVIDER=OpenCode] python3 demo-video/voice.py

Writes demo-video/out/beat01.mp3 ... (git-ignored), vo-draft.wav (one timed track) and captions.srt. """
import base64
import json
import os
import subprocess
import urllib.request
from pathlib import Path

from lines import BEATS, END

OUT = Path(__file__).resolve().parent / "out"
PROJECT = os.environ["LANTERN_TTS_PROJECT"]
VOICE = os.environ.get("LANTERN_TTS_VOICE", "Orus")


def synth(text, path, rate):
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    body = {"input": {"text": text}, "voice": {"languageCode": "en-US", "name": f"en-US-Chirp3-HD-{VOICE}"},
            "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 24000, "speakingRate": rate}}
    req = urllib.request.Request("https://texttospeech.googleapis.com/v1/text:synthesize", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token}", "x-goog-user-project": PROJECT, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        path.write_bytes(base64.b64decode(json.load(r)["audioContent"]))
    return len(text)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], text=True))


def ts(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def split(text, n):
    """Split a beat's text into caption chunks of roughly n words, at sentence ends when possible."""
    words, chunks, cur = text.split(), [], []
    for w in words:
        cur.append(w)
        if len(cur) >= n or (w.endswith((".", "?", "!", ":")) and len(cur) >= 4):
            chunks.append(" ".join(cur)); cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    chars, report, timed, prev_end = 0, [], [], 0.0
    for i, (start, text) in enumerate(BEATS, 1):
        p = OUT / f"beat{i:02d}.mp3"
        chars += synth(text, p, 1.0)                    # natural pace; the edit follows the voice, not the reverse
        d = dur(p)
        actual = max(start, prev_end + 0.4)             # a beat that would overlap the previous one is pushed later
        prev_end = actual + d
        report.append(f"beat{i:02d} script {start:6.1f}  actual {actual:6.1f}  dur {d:5.1f}  ends {prev_end:6.1f}  "
                      f"{'late by %.1fs' % (actual - start) if actual - start > 0.05 else 'on time'}")
        timed.append((actual, d, text))
    END_ACTUAL = max(END, prev_end + 3)
    print("\n".join(report), "\ncharacters sent:", chars, f"| speech ends {prev_end:.1f}s (script ends {END}s)")
    # captions: chunks spread across each beat's real duration, 2 lines max
    srt, k = [], 1
    for start, d, text in timed:
        parts = split(text, 12)
        total = sum(len(c) for c in parts)
        t = start
        for c in parts:
            span = d * len(c) / total
            srt.append(f"{k}\n{ts(t)} --> {ts(t + span)}\n{c}\n")
            t += span; k += 1
    (OUT / "captions.srt").write_text("\n".join(srt))
    # one timed track
    args, fc, mix = [], "", ""
    for i, (start, d, _) in enumerate(timed):
        ms = int(start * 1000)
        args += ["-i", str(OUT / f"beat{i+1:02d}.mp3")]
        fc += f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}];"
        mix += f"[v{i}]"
    fc += f"{mix}amix=inputs={len(timed)}:normalize=0,apad=whole_dur={END_ACTUAL},atrim=0:{END_ACTUAL},loudnorm=I=-16:TP=-1.5:LRA=7[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, "-filter_complex", fc, "-map", "[out]", str(OUT / "vo-draft.wav")], check=True)
    print("wrote", OUT / "vo-draft.wav", "and", OUT / "captions.srt")
