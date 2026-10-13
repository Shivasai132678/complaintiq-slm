"""Voice-over for the ComplaintIQ motion film.

1. Each line is split at its <break> pauses and read by a free Microsoft neural voice
   (edge-tts, en-US-AndrewNeural). The pauses are inserted as silence, so the timing
   stays exact against the scene cuts.
2. Light polish (warmth, gentle compression) and every line is placed on the film timeline.
3. The music bed (music.py) is ducked under the voice and everything is mastered to
   public/mix.wav, which the Remotion composition plays.

Needs internet for edge-tts (the narration text is sent to Microsoft's speech service)
and ffmpeg on PATH to decode its MP3 output.

Run music.py first, then: .venv/bin/python artifacts/video/motion-source/audio/vo.py
"""

import asyncio
import re
import subprocess
import sys
import wave
from pathlib import Path

import edge_tts
import numpy as np
from scipy.signal import butter, resample_poly, sosfilt

HERE = Path(__file__).resolve().parent
PUBLIC = HERE.parent / "public"
WORK = HERE / "vo_lines"
WORK.mkdir(exist_ok=True)
SR = 48000
VOICE = "en-US-AndrewNeural"
RATES = ["-5%", "+0%", "+8%", "+15%"]  # natural pace first; a line speeds up only if it would overrun its scene
BREAK = re.compile(r'<break time="(\d+)ms"/>')
TAG = re.compile(r"<[^>]+>")

# (start second, latest end second, body). <break> marks a pause. Starts follow the scene timeline.
LINES = [
    (1.7, 4.9, "Meet ComplaintIQ."),
    (5.3, 10.9, 'Every complaint is a customer\'s story.<break time="200ms"/> Most are still sorted by hand.'),
    (11.4, 25.8,
     'Here\'s how it works.<break time="250ms"/> A scope gate checks each complaint first.<break time="200ms"/> '
     'Supported cases go to a fine-tuned Qwen 3 model,<break time="80ms"/> right here on the G P U.<break time="220ms"/> '
     'Rules set priority and routing,<break time="100ms"/> and the case is ready for review.'),
    (26.6, 38.8,
     'Pick an example,<break time="100ms"/> or paste your own.<break time="400ms"/> One click,<break time="150ms"/> and the complaint is saved to a durable local queue,<break time="150ms"/> '
     'then classified<break time="150ms"/> in about a third of a second.'),
    (39.5, 47.8,
     'The model predicts.<break time="200ms"/> Rules you can read decide priority and routing.<break time="300ms"/> '
     'And anything off topic goes straight to a person.'),
    (48.6, 58.8,
     'People make the final call.<break time="300ms"/> Confirm or correct,<break time="120ms"/> move the case forward,<break time="150ms"/> '
     'and every change is kept in its history.'),
    (59.5, 66.8,
     'Drop in a C S V,<break time="120ms"/> and every row is saved as it\'s processed.<break time="250ms"/> The overview shows what needs you,<break time="100ms"/> at a glance.'),
    (67.6, 76.8,
     'Qwen 3, 4 B,<break time="120ms"/> fine-tuned with Q LoRA on real C F P B complaints,<break time="150ms"/> '
     'in under two hours on one graphics card.'),
    (77.5, 82.8, 'And everything stays on this computer.<break time="200ms"/> No cloud.<break time="150ms"/> No external A P I.'),
    (83.6, 90.8,
     'On held-out complaints,<break time="120ms"/> it names the right product nearly ninety-one percent of the time,<break time="120ms"/> in about two hundred milliseconds.'),
    (91.3, 95.6, 'ComplaintIQ.<break time="250ms"/> Private, accountable complaint triage.'),
]


def pieces(body: str) -> list[tuple[str, float]]:
    """Split a line into (text to speak, silence after it in seconds) at each <break>."""
    parts = BREAK.split(body)
    out = []
    for i in range(0, len(parts), 2):
        text = " ".join(TAG.sub("", parts[i]).split())
        pause = int(parts[i + 1]) / 1000 if i + 1 < len(parts) else 0.0
        out.append((text, pause))
    return out


async def speak(text: str, path: Path, rate: str) -> None:
    await edge_tts.Communicate(text, VOICE, rate=rate).save(str(path))


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        sr, ch, n = w.getframerate(), w.getnchannels(), w.getnframes()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float64) / 32768
    x = x.reshape(-1, ch).mean(1)
    if sr != SR:
        g = np.gcd(sr, SR)
        x = resample_poly(x, SR // g, sr // g)
    return x


def mp3_to_samples(mp3: Path) -> np.ndarray:
    wav = mp3.with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", str(SR), str(wav)],
        check=True,
    )
    return read_wav(wav)


def render_line(index: int, body: str, rate: str) -> np.ndarray:
    chunks = []
    for k, (text, pause) in enumerate(pieces(body)):
        if text:
            mp3 = WORK / f"l{index:02d}_{k}.mp3"
            asyncio.run(speak(text, mp3, rate))
            chunks.append(mp3_to_samples(mp3))
        chunks.append(np.zeros(int(pause * SR)))
    return np.concatenate(chunks)


def fit_line(index: int, start: float, end: float, body: str) -> tuple[np.ndarray, str]:
    """Render at the most natural rate that finishes inside the scene budget (0.35 s grace)."""
    for rate in RATES:
        x = polish(trim(render_line(index, body, rate)))
        if start + len(x) / SR <= end + 0.35:
            return x, rate
    return x, rate  # still too long at the fastest rate: reported as OVER below


def sos(kind, f, order=2):
    return butter(order, f, kind, fs=SR, output="sos")


def shelf_low(x, f0, gain_db):
    a_ = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * f0 / SR
    al = np.sin(w0) / 2 * np.sqrt(2)
    c = np.cos(w0)
    sa = 2 * np.sqrt(a_) * al
    b = np.array([a_ * ((a_ + 1) - (a_ - 1) * c + sa), 2 * a_ * ((a_ - 1) - (a_ + 1) * c), a_ * ((a_ + 1) - (a_ - 1) * c - sa)])
    a = np.array([(a_ + 1) + (a_ - 1) * c + sa, -2 * ((a_ - 1) + (a_ + 1) * c), (a_ + 1) + (a_ - 1) * c - sa])
    return sosfilt(np.concatenate([b / a[0], a / a[0]])[None, :], x)


def compress(x, thresh_db=-18, ratio=2.5, att=0.004, rel=0.12):
    env = np.abs(x)
    ka, kr = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    out = np.empty_like(env)
    e = 0.0
    for i, v in enumerate(env):  # simple peak follower
        e = ka * e + (1 - ka) * v if v > e else kr * e + (1 - kr) * v
        out[i] = e
    db = 20 * np.log10(out + 1e-9)
    gain_db = np.minimum(0, (thresh_db - db) * (1 - 1 / ratio))
    return x * 10 ** (gain_db / 20)


def polish(x: np.ndarray) -> np.ndarray:
    x = sosfilt(sos("high", 80), x)  # rumble out
    x = shelf_low(x, 180, 1.5)  # a little warmth
    x = compress(x / (np.max(np.abs(x)) + 1e-9))
    return x / (np.max(np.abs(x)) + 1e-9) * 0.9


def trim(x: np.ndarray) -> np.ndarray:
    idx = np.nonzero(np.abs(x) > 0.01)[0]
    return x[max(0, idx[0] - 600) : idx[-1] + 2400]


music_path = PUBLIC / "music.wav"
with wave.open(str(music_path)) as w:
    music = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64).reshape(-1, 2) / 32768
N = len(music)
vo = np.zeros(N)
ok = True
for i, (start, end, body) in enumerate(LINES):
    x, rate = fit_line(i, start, end, body)
    dur = len(x) / SR
    fits = start + dur <= end + 0.35
    ok &= fits
    print(f"line {i:02d} rate {rate:>4}  start {start:5.1f}s  dur {dur:4.1f}s  ends {start + dur:5.1f}s  budget {end:5.1f}s  {'ok' if fits else 'OVER'}")
    a = int(start * SR)
    vo[a : a + len(x)] += x[: N - a]

# duck music under the voice (smoothed envelope, -9 dB)
env = np.abs(vo)
env = sosfilt(sos("low", 4), env)
env = np.clip(env / (np.max(env) + 1e-9) * 6, 0, 1)
duck = 1 - 0.65 * env
mix = music * duck[:, None] * 0.4 + vo[:, None] * 0.8  # music sits well under the voice
peak = np.max(np.abs(mix))
mix = np.tanh(mix / peak * 1.1) / np.tanh(1.1) * 0.9
with wave.open(str(PUBLIC / "mix.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype(np.int16).tobytes())
print("wrote", PUBLIC / "mix.wav")
sys.exit(0 if ok else 1)
