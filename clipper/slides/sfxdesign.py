"""Bruitages « anime » de Domain War, fabriqués à partir de vrais enregistrements libres de droits
(Kenney, CC0 : clipper/assets/sfx/) : superposition, hauteur, son inversé, réverbération, sub-basses.

`build(fam)` rend un tableau mono float32 (44,1 kHz). Résultat mis en cache pour la durée du processus.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

from . import fusion

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "sfx"
R = fusion.RATE


def _np():
    import numpy as np
    return np


@lru_cache(maxsize=64)
def _raw(name: str):
    p = ASSETS / f"{name}.ogg"
    np = _np()
    if not p.exists():
        return np.zeros(int(0.05 * R), dtype=np.float32)
    return fusion.load_sound(p)


def load(name: str):
    return _raw(name).copy()


def pitch(x, semis: float):
    np = _np()
    if not semis:
        return x
    ratio = 2 ** (semis / 12)
    n = int(len(x) / ratio)
    return np.interp(np.arange(n) * ratio, np.arange(len(x)), x).astype(np.float32)


def rev(x):
    return x[::-1].copy()


def lowpass(x, hz):
    return fusion._lowpass(x, hz)


def highpass(x, hz):
    return (x - fusion._lowpass(x, hz)).astype(x.dtype)


def reverb(x, seconds: float = 1.5, wet: float = 0.4, tone: float = 5000):
    """Réverbération par convolution avec une queue de bruit qui décroît (salle immense)."""
    np = _np()
    n = int(seconds * R)
    rng = np.random.default_rng(3)
    ir = rng.normal(0, 1, n).astype(np.float32) * np.exp(-np.arange(n) / R * (6.9 / seconds))
    ir = lowpass(ir, tone)
    ir /= float(np.sqrt((ir ** 2).sum())) or 1
    m = len(x) + n
    size = 1 << (m - 1).bit_length()
    tail = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:m].astype(np.float32)
    out = np.zeros(m, dtype=np.float32)
    out[:len(x)] += x * (1 - wet * 0.5)
    peak = float(np.max(np.abs(tail))) or 1
    out += tail / peak * float(np.max(np.abs(x)) or 1) * wet
    return out


def sub(seconds: float = 1.2, f0: float = 90, f1: float = 32, gain: float = 1.0):
    """Sub-basse qui descend (le « BOUM » qu'on sent)."""
    np = _np()
    t = np.arange(int(seconds * R)) / R
    f = f1 + (f0 - f1) * np.exp(-t * 5)
    x = np.sin(2 * np.pi * np.cumsum(f) / R) * np.exp(-t * (3.5 / seconds)) * np.minimum(1, t / 0.005)
    return (x * gain).astype(np.float32)


def whoosh(seconds: float = 0.6, f0: float = 3000, f1: float = 300, rise: bool = False):
    """Souffle filtré qui descend (chute) ou monte (charge)."""
    np = _np()
    n = int(seconds * R)
    rng = np.random.default_rng(11)
    noise = rng.normal(0, 1, n).astype(np.float32)
    out = np.zeros(n, dtype=np.float32)
    chunks = 24
    for i in range(chunks):
        a, b = i * n // chunks, (i + 1) * n // chunks
        k = i / (chunks - 1)
        f = f0 + (f1 - f0) * k
        seg = lowpass(noise[max(0, a - 512): b], f)[-(b - a):]
        out[a:b] = seg
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** (1.5 if not rise else 0.7)
    if rise:
        env = np.linspace(0, 1, n) ** 2
    return (out * env).astype(np.float32)


def mix(parts: list[tuple[float, object, float]]):
    """[(décalage en s, son, gain)] → un seul son."""
    np = _np()
    end = max(int(o * R) + len(x) for o, x, _ in parts)
    out = np.zeros(end, dtype=np.float32)
    for o, x, g in parts:
        i = int(o * R)
        out[i:i + len(x)] += x * g
    return out


def tame(x, hz: float = 5000, cut: float = 0.55):
    """Adoucit les aigus (plateau −7 dB environ au-dessus de `hz`) : plus de sons qui « cassent les oreilles »."""
    return (x - cut * highpass(x, hz)).astype(x.dtype)


def master(x, gain: float = 1.0):
    np = _np()
    x = tame(np.asarray(x, dtype=np.float32))
    x = np.tanh(x * 1.4 * gain) / math.tanh(1.4)
    peak = float(np.max(np.abs(x))) or 1
    return (x / peak * 0.95).astype(np.float32)


@lru_cache(maxsize=32)
def _build(fam: str):
    np = _np()
    if fam in ("domain", "giant"):
        riser = rev(reverb(pitch(load("force_field_000"), -5), 1.2, 0.8))[-int(0.9 * R):]
        boom = mix([(0, pitch(load("low_frequency_explosion_000"), -3), 1.0),
                    (0, pitch(load("explosion_crunch_004"), -5), 0.6),
                    (0, sub(1.6, 110, 30), 1.0),
                    (0.02, pitch(load("impact_bell_heavy_001"), -12), 0.5)])
        x = mix([(0, riser, 0.6), (0.85 if fam == "domain" else 0.5, reverb(boom, 2.5, 0.5, 3000), 1.0)])
        if fam == "giant":
            x = mix([(0, pitch(load("powerUp7"), -10), 0.6), (0, x, 1.0)])
    elif fam == "shrine":                                   # gong grave + avalanche d'entailles
        boom = mix([(0, pitch(load("low_frequency_explosion_000"), -4), 1.0),
                    (0, pitch(load("impact_bell_heavy_000"), -14), 0.7), (0, sub(1.4, 100, 28), 0.9)])
        parts = [(0, reverb(boom, 2.2, 0.5, 2500), 1.0)]
        for i in range(10):
            shing = highpass(pitch(load(("impact_metal_light_000", "impact_metal_light_001")[i % 2]), 3 + (i % 3)), 1500)
            parts.append((0.18 + i * 0.085, reverb(mix([(0, shing, 1.0), (0, whoosh(0.12, 6000, 2500), 0.5)]), 0.5, 0.3), 0.55))
        x = mix(parts)
    elif fam in ("bomb", "meteor"):
        big = fam == "meteor"
        fall = whoosh(0.8 if big else 0.5, 2500, 250)
        boom = mix([(0, pitch(load("explosion_crunch_003"), -4 if big else -2), 1.0),
                    (0, pitch(load("low_frequency_explosion_001"), -5 if big else -2), 0.9),
                    (0, sub(1.6 if big else 1.1, 95, 30), 1.0)])
        x = mix([(0, fall, 0.5), (0.8 if big else 0.5, reverb(boom, 2.0 if big else 1.3, 0.45), 1.0)])
    elif fam in ("beam", "mega_beam"):
        big = fam == "mega_beam"
        charge = mix([(0, pitch(load("force_field_001"), 3), 0.6), (0, whoosh(0.4, 400, 4000, rise=True), 0.4)])[: int(0.4 * R)]
        fire = load("thruster_fire_000")[: int((1.6 if big else 0.9) * R)]
        fire *= np.linspace(1, 0, len(fire)) ** 1.5
        blast = mix([(0, lowpass(pitch(load("laser_large_002"), -7 if big else -4), 3500), 1.0), (0, lowpass(fire, 2000), 0.7),
                     (0, sub(1.0, 80, 40), 0.6 if big else 0.3)])
        x = mix([(0, charge, 0.7), (0.35, reverb(blast, 1.6 if big else 1.0, 0.35), 1.0)])
        if big:
            x = mix([(0, x, 1.0), (1.4, reverb(pitch(load("low_frequency_explosion_001"), -4), 1.5, 0.4), 0.8)])
    elif fam == "shots":
        parts = []
        lasers = ("laser_small_000", "laser_small_002", "laser_small_004")
        for i in range(5):
            parts.append((i * 0.05, pitch(load(lasers[i % 3]), -3), 0.5))
            parts.append((0.3 + i * 0.05, pitch(load("impact_punch_heavy_000"), -2 + i % 2), 0.6))
        x = reverb(mix(parts), 0.8, 0.25)
    elif fam == "timestop":                                  # « ZA WARUDO » : cloche inversée, gong, tic-tac
        bell = pitch(load("impact_bell_heavy_000"), -5)
        swell = rev(reverb(bell, 1.8, 0.9))[-int(1.0 * R):]
        parts = [(0, swell, 0.7), (0.95, reverb(mix([(0, bell, 1.0), (0, sub(1.5, 70, 35), 0.6)]), 2.5, 0.55), 1.0)]
        for i in range(4):
            parts.append((1.4 + i * 0.35, pitch(load("impact_generic_light_000"), 6), 0.35))
        x = mix(parts)
    elif fam == "teleport":
        x = reverb(mix([(0, pitch(load("phaseJump1"), -2), 0.7), (0.12, pitch(load("impact_punch_heavy_000"), -3), 1.0),
                        (0.12, load("impact_plate_heavy_000"), 0.4), (0.12, sub(0.6, 120, 50), 0.6)]), 0.9, 0.3)
    elif fam == "transform":                                 # montée en puissance (aura) + explosion d'énergie
        riser = rev(reverb(pitch(load("force_field_000"), -2), 1.5, 0.8))[-int(1.1 * R):]
        aura = mix([(0, pitch(load("powerUp7"), -8), 0.6), (0, whoosh(1.0, 300, 5000, rise=True), 0.5)])
        boom = mix([(0, pitch(load("low_frequency_explosion_000"), -2), 1.0), (0, sub(1.8, 120, 30), 1.0),
                    (0, pitch(load("impact_bell_heavy_001"), -9), 0.4)])
        x = mix([(0, riser, 0.6), (0.1, aura, 0.7), (1.1, reverb(boom, 2.2, 0.5, 3500), 1.0)])
    elif fam == "clash":                                     # 2 rayons qui se poussent : grondement grave
        n = int(3.6 * R)
        t = np.arange(n) / R
        hum = pitch(load("force_field_000"), -12)
        drone = np.tile(hum, n // len(hum) + 1)[:n]
        fire = load("thruster_fire_000")
        roar = lowpass(np.tile(fire, n // len(fire) + 1)[:n], 900)          # souffle grave, sans sifflement
        wob = 0.65 + 0.35 * np.sin(2 * np.pi * (5 + 4 * t / 3.6) * t)      # « wom wom » qui accélère
        rise = np.minimum(1, t / 0.4) * (0.6 + 0.4 * t / 3.6)
        base = (lowpass(drone, 1400) * 0.8 + roar * 0.9 + sub(3.6, 60, 48) * 0.7) * wob * rise
        parts = [(0, base.astype(np.float32), 1.0), (0, lowpass(pitch(load("laser_large_002"), -9), 1800), 0.6)]
        for i in range(6):                                  # chocs sourds dans le duel
            parts.append((0.5 + i * 0.5, lowpass(pitch(load("impact_punch_heavy_000"), -7), 1500), 0.4))
        parts.append((3.55, reverb(mix([(0, pitch(load("low_frequency_explosion_001"), -5), 1.0),
                                        (0, pitch(load("explosion_crunch_003"), -5), 0.5),
                                        (0, sub(1.8, 90, 28), 1.0)]), 2.2, 0.45, 2500), 1.0))
        x = mix(parts)
    elif fam == "vanish":                                    # disparition + coup derrière
        x = reverb(mix([(0, pitch(load("phaseJump1"), 4), 0.5), (0.08, pitch(load("impact_punch_heavy_004"), -2), 0.9),
                        (0.08, sub(0.4, 140, 60), 0.5)]), 0.6, 0.25)
    elif fam == "powerup":                                   # forme intermédiaire : souffle qui monte + petit boum
        x = mix([(0, whoosh(0.45, 400, 4000, rise=True), 0.6), (0, pitch(load("powerUp7"), -4), 0.5),
                 (0.4, reverb(mix([(0, pitch(load("low_frequency_explosion_001"), -1), 0.8),
                                   (0, sub(0.7, 130, 50), 0.7)]), 1.2, 0.35), 0.9)])
    elif fam == "hit":                                       # perso touché : coup sourd + claquement
        x = reverb(mix([(0, pitch(load("impact_punch_heavy_004"), -4), 1.0), (0, sub(0.35, 150, 55), 0.8),
                        (0.01, lowpass(load("impact_plate_heavy_000"), 3000), 0.3)]), 0.5, 0.25, 3000)
    elif fam == "miss":                                      # esquive : petit souffle
        x = whoosh(0.22, 5000, 1500) * 0.6
    elif fam == "summon":                                    # gong très grave + souffle de créature
        x = mix([(0, rev(reverb(pitch(load("low_frequency_explosion_000"), -6), 1.0, 0.7))[-int(0.7 * R):], 0.5),
                 (0.65, reverb(mix([(0, pitch(load("impact_bell_heavy_001"), -15), 1.0),
                                    (0, pitch(load("slime_000"), -9), 0.5), (0, sub(2.0, 60, 28), 0.9)]), 3.0, 0.5), 1.0)])
    elif fam == "clones":
        x = reverb(mix([(i * 0.11, pitch(load("phaseJump3"), (-2, 0, 2, 4)[i]), 0.6) for i in range(4)]
                       + [(i * 0.11 + 0.05, load("impact_soft_medium_000"), 0.4) for i in range(4)]), 0.8, 0.3)
    elif fam == "regen":
        x = reverb(pitch(load("impact_glass_light_000"), 2), 0.9, 0.5) * 0.5
    elif fam == "tick":
        x = pitch(load("impact_soft_medium_000"), 3)[: int(0.09 * R)]
    elif fam == "ko":
        x = reverb(mix([(0, pitch(load("impact_punch_heavy_004"), -3), 1.0), (0, load("explosion_crunch_000"), 0.6),
                        (0, sub(0.8, 110, 40), 0.8)]), 1.0, 0.3)
    elif fam == "win":
        x = reverb(mix([(0, pitch(load("impact_bell_heavy_002"), -2), 1.0), (0, sub(1.2, 80, 40), 0.5),
                        (0.0, pitch(load("impact_bell_heavy_001"), -7), 0.5)]), 2.5, 0.5)
    else:
        x = whoosh(0.6)
    return master(np.asarray(x, dtype=np.float32))


def build(fam: str):
    return _build(fam).copy()
