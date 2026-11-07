"""Synthesizes the film's score (ambient pad, ignition chimes, soft effects) into a stereo WAV. Needs numpy only.

  python film/score.py film/score.wav

All sound is generated here from sine waves and filtered noise: no samples, no third-party audio.
Cue times match LIT / scene times in film.html.
"""
import sys
import wave

import numpy as np

SR, DUR = 44100, 50.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)


def env(t0, t1, a=1.0, r=1.0):
    """Smooth envelope that is 0 outside [t0, t1], fades in over a seconds and out over r seconds."""
    x = np.clip((T - t0) / max(a, 1e-3), 0, 1) * np.clip((t1 - T) / max(r, 1e-3), 0, 1)
    return x * x * (3 - 2 * x)


def hz(note):                       # note name -> frequency, e.g. "A3"
    names = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    n = names[note[0]] + 12 * (int(note[-1]) + 1) + (1 if "#" in note else 0)
    return 440.0 * 2 ** ((n - 69) / 12)


def lowpass(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    out = np.empty_like(x)
    y = 0.0
    for i in range(len(x)):         # one-pole; fine for short effect buffers
        y = (1 - a) * x[i] + a * y
        out[i] = y
    return out


def smooth(x, k):                   # moving-average low-pass for long buffers (fast)
    k = max(1, int(k))
    c = np.cumsum(np.insert(x, 0, 0.0))
    y = (c[k:] - c[:-k]) / k
    return np.concatenate([np.full(k - 1, y[0]), y])


L = np.zeros(N)
R = np.zeros(N)


def add(sig, t, pan=0.0, gain=1.0):
    """Mix a short signal into the stereo bus starting at t seconds."""
    i = int(t * SR)
    j = min(N, i + len(sig))
    if i >= N:
        return
    seg = sig[: j - i] * gain
    L[i:j] += seg * (1 - max(0, pan))
    R[i:j] += seg * (1 + min(0, pan))


# ---- pad: one chord per scene, cross-faded -------------------------------------------------
CHORDS = [  # (start, end, notes)
    (0.0, 7.0, ["A2", "E3", "A3", "C4"]),            # 1  darkness: Am
    (6.0, 14.0, ["F2", "C3", "F3", "A3"]),           # 2  F
    (13.0, 22.0, ["C3", "G3", "E4", "C4"]),          # 3  C
    (21.0, 30.0, ["G2", "D3", "G3", "B3"]),          # 4  G
    (29.0, 37.0, ["A2", "E3", "A3", "C4"]),          # 5  Am
    (36.0, 44.0, ["F2", "C3", "F3", "A3"]),          # 6  F
    (43.0, 50.0, ["C3", "G3", "E4", "B4", "D5"]),    # 7  Cmaj9: resolution
]
pad = np.zeros(N)
for a, b, notes in CHORDS:
    e = env(a, b, a=2.2, r=2.2)
    for k, n in enumerate(notes):
        f = hz(n)
        for det in (-0.12, 0.0, 0.12):              # slight detune for warmth
            ph = rng.uniform(0, 6.28)
            s = np.sin(2 * np.pi * (f + det * (k + 1)) * T + ph) + .35 * np.sin(2 * np.pi * 2 * f * T + ph) + .12 * np.sin(2 * np.pi * 3 * f * T)
            pad += e * s * (0.5 if k == 0 else 0.32) / 3
lfo = 0.85 + 0.15 * np.sin(2 * np.pi * 0.11 * T)
pad = smooth(pad, 14) * lfo * env(0, DUR, a=3.0, r=5.0)
L += pad * 0.55
R += np.roll(pad, int(0.012 * SR)) * 0.55           # tiny stereo offset

# ---- slow pulse (soft sub, 50 bpm) that appears with the wire and stops before the finale ----
beat = np.zeros(N)
for t0 in np.arange(6.0, 43.0, 1.2):
    tt = np.clip(T - t0, 0, None)
    beat += (T >= t0) * np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 5.0) * 0.5
beat *= env(6.0, 43.5, a=3.0, r=2.0)
L += beat * 0.45
R += beat * 0.45


# ---- sounds ------------------------------------------------------------------------------
def bell(f, length=3.2):
    t = np.arange(int(SR * length)) / SR
    s = np.zeros_like(t)
    for ratio, amp, dec in ((1, 1.0, 1.6), (2.0, .45, 2.2), (2.76, .25, 3.0), (5.4, .12, 4.5)):
        s += amp * np.sin(2 * np.pi * f * ratio * t) * np.exp(-t * dec)
    s *= np.minimum(1, t / 0.004)
    return s


LIT = [9.0, 14.0, 21.8, 26.5, 33.6, 40.6]
SCALE = ["E5", "G5", "A5", "C6", "D6", "E6"]
for i, tm in enumerate(LIT):                          # a lantern lights: bell, rising through the scale
    add(bell(hz(SCALE[i])), tm, pan=(i - 2.5) / 6, gain=0.5)
for i in range(6):                                    # finale: all six ignite in turn, warmer and fuller
    add(bell(hz(SCALE[i]), 4.5), 44.2 + i * 0.4, pan=(i - 2.5) / 6, gain=0.6)
    add(bell(hz(SCALE[i]) / 2, 4.5), 44.2 + i * 0.4, pan=(i - 2.5) / 6, gain=0.3)


def whoosh(length, f_from, f_to, gain):
    n = int(SR * length)
    noise = rng.standard_normal(n)
    t = np.linspace(0, 1, n)
    out = np.zeros(n)
    for fc0 in (f_from, f_to):
        pass
    sweep = noise * 0
    # band-limited noise whose centre moves from f_from to f_to (sum of a few narrow slices)
    for k in range(10):
        fc = np.exp(np.log(f_from) * (1 - k / 9) + np.log(f_to) * (k / 9))
        slice_env = np.exp(-((t - k / 9) ** 2) / 0.012)
        sweep += smooth(noise, SR / (2 * fc)) * slice_env
    sweep *= np.sin(np.pi * t) ** 2
    return sweep / (np.max(np.abs(sweep)) + 1e-9) * gain


add(whoosh(2.4, 300, 2500, 1.0), 23.2, gain=0.20)     # light travels nurse-station -> doctor-review
add(whoosh(1.2, 400, 1800, 1.0), 33.0, gain=0.22)     # chart flip
add(whoosh(2.0, 250, 1400, 1.0), 37.6, gain=0.20)     # owner slides to the incoming nurse

tt = np.arange(int(SR * 0.5)) / SR                    # receipt stamp: soft thunk
thunk = np.sin(2 * np.pi * 85 * tt) * np.exp(-tt * 14) + 0.5 * np.sin(2 * np.pi * 170 * tt) * np.exp(-tt * 20)
add(thunk, 27.0, gain=0.8)
tt = np.arange(int(SR * 1.2)) / SR                    # refusal: two low dull tones, deliberately not alarming
for off, f in ((0.0, 196.0), (0.35, 147.0)):
    tone = np.sin(2 * np.pi * f * tt) * np.exp(-tt * 3.0) + .3 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 4.5)
    add(tone * np.minimum(1, tt / 0.01), 30.0 + off, gain=0.35)
add(bell(hz("E5"), 2.5), 10.0, pan=0.2, gain=0.18)     # the amber link between quote and chart connects

# ---- simple reverb: convolve with decaying noise ----------------------------------------
ir_n = int(SR * 2.6)
ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR * 2.4)
ir = smooth(ir, 6)


def reverb(x, wet):
    n = len(x) + len(ir)
    size = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return x + wet * y / (np.max(np.abs(y)) + 1e-9) * np.max(np.abs(x)) * 0.5


L = reverb(L, 0.55)
R = reverb(R, 0.55)

# ---- master: level so the mean sits around -20 dB, peaks under -2 dB, 1.5 s fade in, 3 s fade out ----
fade = np.clip(T / 1.5, 0, 1) * np.clip((DUR - T) / 3.0, 0, 1)
L *= fade
R *= fade
peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
rms = np.sqrt(np.mean(np.concatenate([L, R]) ** 2))
gain = min(0.79 / peak, 0.10 / rms)
L, R = np.tanh(L * gain * 1.05), np.tanh(R * gain * 1.05)
out = np.stack([L, R], axis=1)
pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
with wave.open(sys.argv[1] if len(sys.argv) > 1 else "score.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", sys.argv[1] if len(sys.argv) > 1 else "score.wav", f"gain={gain:.2f}")
