"""Voix off Kokoro (kokoro-onnx, Apache 2.0) : voix am_adam, choisie par l'utilisateur le 09/11 (« on le reconnaît »).
Modèles dans /tmp/tts (releases GitHub thewh1teagle/kokoro-onnx, Hugging Face bloqué ; jamais dans le dépôt) :
  curl -sSL -o /tmp/tts/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
  curl -sSL -o /tmp/tts/voices-v1.0.bin  https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
lines(textes) → (audio 44,1 kHz, [(début, fin) de chaque phrase]) : timings EXACTS (pas besoin de détecter les silences).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np

TTS = Path("/tmp/tts")
RATE = 44100


@lru_cache(maxsize=1)
def _k():
    from kokoro_onnx import Kokoro
    return Kokoro(str(TTS / "kokoro-v1.0.onnx"), str(TTS / "voices-v1.0.bin"))


def say(text: str, voice: str = "am_adam", speed: float = 1.05) -> np.ndarray:
    s, sr = _k().create(text, voice=voice, speed=speed, lang="en-us")
    s = np.asarray(s, np.float32)
    env = np.abs(s)
    idx = np.nonzero(env > env.max() * 0.03)[0]
    if len(idx):
        s = s[max(0, idx[0] - 200): idx[-1] + 600]
    x = np.interp(np.arange(int(len(s) * RATE / sr)) * sr / RATE, np.arange(len(s)), s).astype(np.float32)
    return x / (np.abs(x).max() + 1e-6) * 0.9


def lines(texts, gap: float = 0.38, start: float = 0.25, voice: str = "am_adam", speed: float = 1.05, at=None):
    """`at` = liste optionnelle de débuts imposés (en s) ; sinon les phrases s'enchaînent avec `gap`."""
    clips = [say(t, voice, speed) for t in texts]
    segs, t = [], start
    for i, c in enumerate(clips):
        if at and i < len(at) and at[i] is not None:
            t = max(t, at[i])
        segs.append((t, t + len(c) / RATE))
        t = segs[-1][1] + gap
    buf = np.zeros(int((segs[-1][1] + 2) * RATE), np.float32)
    for c, (a, b) in zip(clips, segs):
        i = int(a * RATE)
        buf[i:i + len(c)] += c
    return buf, segs
