"""Narration for the concept film via Google Cloud Text-to-Speech (Chirp 3: HD, voice Orus), the same setup as the Gasket demo.
Uses your gcloud login for a short-lived token read at run time; no API key or key file is stored or printed.

  LANTERN_TTS_PROJECT=<project with the Text-to-Speech API enabled> python film/voice.py

Writes film/voice/seg1.mp3 .. seg7.mp3 (git-ignored) and prints the duration of each next to its slot in the film."""
import base64
import json
import os
import subprocess
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "voice"
PROJECT = os.environ["LANTERN_TTS_PROJECT"]
VOICE = os.environ.get("LANTERN_TTS_VOICE", "Orus")
# (start second in the film, text): each line is the on-screen text of its scene, read aloud
LINES = [
    (2.6, "Patients hear things before the chart does."),
    (8.0, "When they disagree, someone has to own it."),
    (15.4, "An A-I teammate notices."),
    (24.6, "The concern moves to the right people, with receipts."),
    (31.6, "A clinician decides. Code makes sure only that counts."),
    (38.4, "The next shift owns what's still open."),
    (45.6, "Lantern. No concern left in the dark."),
]
SLOT_END = [7.4, 14.6, 20.8, 28.8, 36.0, 43.0, 50.0]


def synth(text, path, rate=0.95):
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


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    chars = 0
    for i, (start, text) in enumerate(LINES, 1):
        p = OUT / f"seg{i}.mp3"
        chars += synth(text, p)
        d = dur(p)
        print(f"seg{i} start {start:5.1f}s dur {d:4.1f}s ends {start + d:5.1f}s  slot ends {SLOT_END[i-1]:4.1f}s  {'ok' if start + d <= SLOT_END[i-1] else 'OVER'}")
    print("characters sent:", chars)
