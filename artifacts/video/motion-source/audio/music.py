"""Original synthesized score for the ComplaintIQ motion film (120 BPM, 96 s).

Writes public/music.wav. Scene cuts land on beats so the hits line up with the picture.
Run: .venv\\Scripts\\python.exe artifacts\\video\\motion-source\\audio\\music.py
"""

from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000
DUR = 96.0
BPM = 120
BEAT = 60 / BPM
N = int(SR * DUR)
rng = np.random.default_rng(7)
CUTS = [5, 11, 26, 39, 48, 59, 67, 77, 83, 91]  # seconds, from the video timeline
OUT = Path(__file__).resolve().parents[1] / "public" / "music.wav"


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def env_curve(points):
    """Piecewise-linear automation over the whole film: [(sec, value), ...]."""
    t = np.arange(N) / SR
    xs, ys = zip(*points)
    return np.interp(t, xs, ys)


def place(buf, sig, at):
    i = int(at * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i]


def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (f * (1 + detune)) * t + rng.random()
    return 2 * (ph % 1) - 1


# D major: Dmaj9, Bm9, Gmaj7#11-ish, Asus -> A (one chord per bar = 2 s)
CHORDS = [
    [50, 57, 61, 64, 66],  # D A C# E F#
    [47, 54, 57, 61, 62],  # B F# A C# D
    [43, 50, 54, 57, 62],  # G D F# A D
    [45, 52, 57, 59, 64],  # A E A B E
]
BASS = [38, 35, 31, 33]
bar = 4 * BEAT


def chord_at(t):
    return int(t // bar) % 4


# ---------------------------------------------------------------- pads
pad = np.zeros(N)
nbars = int(DUR / bar) + 1
for b in range(nbars):
    n = int(bar * SR) + int(0.6 * SR)
    t = np.arange(n) / SR
    a = np.minimum(1, t / 0.5) * np.exp(-np.maximum(0, t - bar) / 0.25)
    s = np.zeros(n)
    for m in CHORDS[b % 4]:
        for d in (-0.004, 0.0, 0.0045):
            s += saw(hz(m), n, d)
    place(pad, s * a / 15, b * bar)
pad = lp(pad, 1400, 2)
pad *= env_curve([(0, 0.0), (1.2, 0.45), (5, 0.5), (11, 0.42), (67, 0.42), (69, 0.6), (77, 0.45), (91, 0.55), (96, 0.0)])

# ---------------------------------------------------------------- sub bass (8ths)
bass = np.zeros(N)
for k in range(int(DUR / (BEAT / 2))):
    t0 = k * BEAT / 2
    if t0 < 11 or 67 <= t0 < 77 or t0 >= 91:
        continue
    f = hz(BASS[chord_at(t0)])
    n = int(BEAT / 2 * SR * 0.92)
    t = np.arange(n) / SR
    a = np.minimum(1, t / 0.006) * np.exp(-t / 0.22)
    s = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)
    place(bass, s * a * (1.0 if k % 2 == 0 else 0.7), t0)
bass = lp(bass, 300) * 0.32

# ---------------------------------------------------------------- arp pluck (16ths)
arp = np.zeros(N)
for k in range(int(DUR / (BEAT / 4))):
    t0 = k * BEAT / 4
    if t0 < 5 or t0 >= 91:
        continue
    if t0 < 11 and k % 2:  # sparse in the problem scene
        continue
    ch = CHORDS[chord_at(t0)]
    pat = [0, 2, 3, 4, 2, 3, 1, 4]
    m = ch[pat[k % 8]] + 12
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    tone = np.sign(np.sin(2 * np.pi * hz(m) * t)) * 0.35 + np.sin(2 * np.pi * hz(m) * t)
    a = np.minimum(1, t / 0.002) * np.exp(-t / 0.09)
    place(arp, tone * a, t0)
arp = lp(arp, 3200)
arp *= env_curve([(0, 0), (5, 0.0), (6, 0.12), (11, 0.15), (26, 0.17), (67, 0.17), (68, 0.10), (77, 0.17), (91, 0.12), (92, 0)])

# ---------------------------------------------------------------- drums
drums = np.zeros(N)


def kick():
    n = int(0.45 * SR)
    t = np.arange(n) / SR
    f = 48 + 110 * np.exp(-t / 0.035)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t / 0.16) + 0.3 * rng.standard_normal(n) * np.exp(-t / 0.003)


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t / (0.05 if open_ else 0.012))


def clap():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    s = bp(rng.standard_normal(n), 900, 4000)
    e = np.exp(-t / 0.07)
    for d in (0.0, 0.011, 0.022):
        e += 0.6 * np.exp(-np.maximum(0, t - d) / 0.006) * (t >= d)
    return s * e * 0.5


K, H, HO, CL = kick(), hat(), hat(True), clap()
for k in range(int(DUR / BEAT)):
    t0 = k * BEAT
    full = 11 <= t0 < 67 or 77 <= t0 < 91
    half = 67 <= t0 < 77
    if full or (half and k % 2 == 0):
        place(drums, K * 0.9, t0)
    if full:
        place(drums, (HO if k % 4 == 3 else H) * 0.22, t0 + BEAT / 2)
        place(drums, H * 0.08, t0 + BEAT / 4)
        place(drums, H * 0.08, t0 + 3 * BEAT / 4)
        if k % 2 == 1 and t0 >= 26:
            place(drums, CL * 0.55, t0)
    if half:
        place(drums, H * 0.12, t0 + BEAT / 2)

# ---------------------------------------------------------------- fx: whooshes, impacts, riser
fx = np.zeros(N)


def whoosh(length=0.7):
    n = int(length * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    # sweep a band upward by mixing progressively brighter filtered copies
    lo = lp(noise, 600)
    hi = hp(noise, 2500)
    x = t / length
    s = lo * (1 - x) + hi * x
    return s * (x**2.2) * np.exp(-np.maximum(0, x - 0.92) * 40) * 0.5


def impact(length=3.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = 38 + 60 * np.exp(-t / 0.08)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.7)
    air = lp(rng.standard_normal(n), 2500) * np.exp(-t / 0.35) * 0.35
    return (body + air) * 0.9


for c in CUTS:
    w = whoosh()
    place(fx, w * 0.55, c - len(w) / SR)
place(fx, impact() * 0.8, 1.0)  # logo lands
place(fx, impact() * 0.9, 91.0)  # outro
# riser into the pipeline groove
n = int(2.0 * SR)
t = np.arange(n) / SR
riser = hp(rng.standard_normal(n), 1500) * (t / 2.0) ** 3 * 0.25
place(fx, riser, 9.0)
# soft glints on metrics (evidence scene counters)
for at in (83.4, 84.0, 84.6, 85.2):
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    g = np.sin(2 * np.pi * hz(86) * t) * np.exp(-t / 0.25) * 0.08
    place(fx, g, at)

# ---------------------------------------------------------------- mix + reverb + master
dry = pad + bass + arp + drums + fx
# sidechain-style duck on kick beats while the groove plays
duck = np.ones(N)
for k in range(int(DUR / BEAT)):
    t0 = k * BEAT
    if 11 <= t0 < 67 or 77 <= t0 < 91:
        i = int(t0 * SR)
        n = int(0.25 * SR)
        d = 1 - 0.45 * np.exp(-np.arange(n) / SR / 0.08)
        duck[i : i + n] = np.minimum(duck[i : i + n], d[: len(duck[i : i + n])])
dry = bass + drums + fx + (pad + arp) * duck

ir_n = int(2.6 * SR)
ir_t = np.arange(ir_n) / SR
irL = rng.standard_normal(ir_n) * np.exp(-ir_t / 0.55)
irR = rng.standard_normal(ir_n) * np.exp(-ir_t / 0.55)
send = lp(hp(pad * 0.6 + arp * 1.2 + fx * 0.5 + drums * 0.08, 200), 6000)
wetL = fftconvolve(send, irL)[:N] * 0.012
wetR = fftconvolve(send, irR)[:N] * 0.012

# slight stereo width on arp/pad via short delay
d = int(0.012 * SR)
widen = np.concatenate([np.zeros(d), (pad + arp)[:-d]]) * 0.15
L = dry + wetL + widen
R = dry + wetR - widen * 0.6
st = np.stack([L, R], 1)
st = hp(st.T, 28).T
fade = env_curve([(0, 1), (94.0, 1), (96, 0)])
st *= fade[:, None]
peak = np.max(np.abs(st))
st = np.tanh(st / peak * 1.25) / np.tanh(1.25) * 0.89  # gentle saturation + headroom
pcm = (st * 32767).astype(np.int16)

import wave  # noqa: E402

with wave.open(str(OUT), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("wrote", OUT, f"{DUR}s")
