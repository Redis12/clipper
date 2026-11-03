"""Générateur d'effets d'anime image par image (procédural, numpy) : éclairs qui crépitent, sphères d'énergie
qui tourbillonnent, explosions, impacts en étoile, ondes de choc, entailles, rayons qui ondulent, auras en flammes.

Chaque effet est fabriqué une fois (en gris : intensité + alpha), puis colorisé à la couleur du camp avec un cœur
blanc « chaud ». Le Domain War les joue en boucle (24 i/s) là où il n'y a pas d'image fournie par l'utilisateur
(library/_domain/fx/), ou à la place des images fixes génériques (impact.png, burst.png…) quand
`slides.domain.procedural_vfx` est vrai (défaut).

`frames(name, size, color)` → liste d'images RGBA. Noms : lightning, orb, explosion, hit, ring, slash, beam, aura,
charge, smoke. `export(dir)` écrit les planches `<nom>_frames/` pour les voir / retoucher.
"""
from __future__ import annotations

import math
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

NAMES = ("lightning", "orb", "explosion", "hit", "ring", "slash", "beam", "aura", "charge", "smoke")
FPS = 24


# --------------------------------------------------------------------------- outils

def _noise(h: int, w: int, rng: np.random.Generator, octaves: int = 4, base: int = 4) -> np.ndarray:
    """Bruit de valeur 0-1 (grilles aléatoires agrandies, sommées)."""
    out = np.zeros((h, w), dtype=np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = base * (2 ** o)
        g = rng.random((n + 1, n + 1)).astype(np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BILINEAR)
        out += np.asarray(im).astype(np.float32) / 255 * amp
        tot += amp
        amp *= 0.5
    return out / tot


def _blur(a: np.ndarray, r: float) -> np.ndarray:
    if r <= 0:
        return a
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r))
    return np.asarray(im).astype(np.float32) / 255


def _polar(s: int):
    y, x = np.mgrid[0:s, 0:s].astype(np.float32)
    x = (x - s / 2 + 0.5) / (s / 2)
    y = (y - s / 2 + 0.5) / (s / 2)
    return np.sqrt(x * x + y * y), np.arctan2(y, x), x, y


def colorize(I: np.ndarray, A: np.ndarray, col, hot: float = 1.0) -> Image.Image:
    """Intensité + alpha → RGBA : couleur du camp, cœur blanc là où c'est intense."""
    I = np.clip(I, 0, 1)[..., None]
    c = np.asarray(col, dtype=np.float32)[None, None, :] / 255
    h = (I ** 2) * hot
    rgb = c * (1 - h) + h
    rgb = np.clip(rgb * (0.35 + 0.65 * I), 0, 1)
    out = np.dstack([rgb * 255, np.clip(A, 0, 1)[..., None] * 255]).astype(np.uint8)
    return Image.fromarray(out, "RGBA")


# --------------------------------------------------------------------------- effets (gris)

def _bolt(d: ImageDraw.ImageDraw, x, y, ang, length, rng: random.Random, width, depth=0):
    pts = [(x, y)]
    seg = max(3, int(length / 9))
    for _ in range(9):
        ang += rng.uniform(-0.55, 0.55)
        x += math.cos(ang) * seg
        y += math.sin(ang) * seg
        pts.append((x, y))
        if depth < 2 and rng.random() < 0.28:
            _bolt(d, x, y, ang + rng.choice((-1, 1)) * rng.uniform(0.4, 1.1), length * 0.45, rng,
                  max(1, width * 0.6), depth + 1)
    d.line(pts, fill=255, width=int(max(1, width)))


def g_lightning(n: int, s: int, seed: int):
    out = []
    rng = random.Random(seed)
    for i in range(n):
        core = Image.new("L", (s, s), 0)
        d = ImageDraw.Draw(core)
        for _ in range(rng.randint(2, 4)):
            ang = rng.uniform(0, 2 * math.pi)
            _bolt(d, s / 2 + rng.uniform(-s * 0.06, s * 0.06), s / 2 + rng.uniform(-s * 0.06, s * 0.06), ang,
                  s * rng.uniform(0.32, 0.48), rng, s * 0.028)
        c = np.asarray(core).astype(np.float32) / 255
        glow = _blur(c, s * 0.045)
        flick = 0.75 + 0.25 * math.sin(i * 2.4)
        I = np.clip(c + glow * 0.45, 0, 1)
        A = np.clip((c + glow * 2.2) * flick, 0, 1)
        out.append((I, A))
    return out


def g_orb(n: int, s: int, seed: int):
    rng = np.random.default_rng(seed)
    r, th, x, y = _polar(s)
    noise = _noise(s, s * 2, rng, 3, 6)                       # bande panoramique (bouclable en theta)
    out = []
    for i in range(n):
        rot = 2 * math.pi * i / n
        u = ((th + rot + r * 3.5) / (2 * math.pi)) % 1.0        # spirale
        ix = (u * (s * 2 - 1)).astype(int)
        iy = np.clip((r * (s - 1)), 0, s - 1).astype(int)
        sw = noise[iy, ix]
        sw = np.clip((sw - 0.42) * 3.2, 0, 1)
        core = np.clip(1 - r / 0.32, 0, 1) ** 1.5 * (0.85 + 0.15 * math.sin(i * 0.9))
        edge = np.clip(1 - abs(r - 0.9) / 0.06, 0, 1)
        mask = np.clip((0.97 - r) / 0.08, 0, 1)
        I = np.clip(core + sw * 0.75 * mask + edge * 0.6, 0, 1)
        A = np.clip((core * 1.2 + sw * 0.9 + edge * 0.9) * mask + _blur(core, s * 0.05) * 0.6, 0, 1)
        out.append((I, A))
    return out


def g_explosion(n: int, s: int, seed: int):
    rng = np.random.default_rng(seed)
    r, th, x, y = _polar(s)
    out = []
    nz = [_noise(s, s, rng, 4, 4) for _ in range(3)]
    for i in range(n):
        t = i / max(1, n - 1)
        R = 0.22 + 0.74 * math.sqrt(t)
        n_ = nz[i % 3] * 0.55 + nz[(i + 1) % 3] * 0.45
        edge = r * (0.65 + 0.8 * n_)                      # bord très irrégulier (langues de feu)
        ball = np.clip((R - edge) / 0.1, 0, 1)
        heat = ball * np.clip(1 - r / (R * 0.55), 0, 1) * max(0.0, 1 - t * 1.5)
        fire = ball * np.clip((n_ - 0.3) * 1.6, 0, 1) * max(0.0, 1 - t * 1.05)
        smoke = ball * (0.3 + 0.3 * n_) * min(1.0, t * 2) * max(0.0, 1 - t)
        ring = np.clip(1 - abs(r - min(0.98, R * 1.2)) / 0.03, 0, 1) * max(0.0, 1 - t * 1.3)
        spikes = 0
        if t < 0.35:
            k = 10
            da = np.abs(((th * k / (2 * math.pi)) % 1.0) - 0.5) * 2      # 0 au centre d'un rayon
            spikes = np.clip(1 - da / 0.22, 0, 1) * np.clip(1 - r / (R * 2.2), 0, 1) * (1 - t / 0.35) ** 0.6
        I = np.clip(heat * 1.5 + fire * 0.9 + ring * 1.1 + spikes * 1.2 + smoke * 0.12, 0, 1)
        A = np.clip(heat + fire + ring + spikes * 0.9 + smoke * 0.55, 0, 1) * (1 if t < 0.7 else (1 - t) / 0.3)
        out.append((I, A))
    return out


def g_hit(n: int, s: int, seed: int):
    rng = random.Random(seed)
    r, th, x, y = _polar(s)
    k = rng.randint(10, 14)
    lens = [rng.uniform(0.45, 1.0) for _ in range(k)]
    wid = [rng.uniform(0.05, 0.12) for _ in range(k)]
    off = rng.uniform(0, 2 * math.pi)
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        grow = min(1.0, (t + 0.08) / 0.3)
        star = np.zeros_like(r)
        for j in range(k):
            a = off + 2 * math.pi * j / k
            da = np.abs((th - a + math.pi) % (2 * math.pi) - math.pi)
            L = lens[j] * grow
            star = np.maximum(star, np.clip(1 - da / (wid[j] * np.clip(1 - r / L, 0, 1) + 1e-3), 0, 1)
                              * np.clip((L - r) / 0.05, 0, 1))
        flash = np.clip(1 - r / (0.22 * (1 - t * 0.7)), 0, 1)
        fade = 1 - t ** 1.5
        I = np.clip(star * 1.0 + flash * 1.3, 0, 1)
        A = np.clip(star + flash + _blur(flash, s * 0.04) * 0.7, 0, 1) * fade
        out.append((I, A))
    return out


def g_ring(n: int, s: int, seed: int):
    r, th, x, y = _polar(s)
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        R = 0.15 + 0.8 * (1 - (1 - t) ** 2)
        w = 0.05 * (1 - t) + 0.012
        ring = np.clip(1 - abs(r - R) / w, 0, 1)
        inner = np.clip(1 - abs(r - R * 0.72) / (w * 0.6), 0, 1) * 0.6
        I = np.clip(ring * 1.2 + inner, 0, 1)
        A = np.clip(ring + inner + _blur(ring, s * 0.02) * 0.5, 0, 1) * (1 - t) ** 0.7
        out.append((I, A))
    return out


def g_slash(n: int, s: int, seed: int):
    """Croissant effilé (épais au milieu, fin aux bouts) qui balaie, avec traînée."""
    r, th, x, y = _polar(s)
    out, prev = [], None
    for i in range(n):
        t = i / max(1, n - 1)
        rot = -2.4 + 3.0 * (1 - (1 - min(1.0, t / 0.7)) ** 2)
        a = (th - rot + math.pi) % (2 * math.pi) - math.pi            # angle relatif à la tête
        span = 1.5
        along = np.clip((a + span) / span, 0, 1)                        # 0 = queue, 1 = tête
        inside = (a < 0) & (a > -span)
        thick = 0.11 * np.sin(np.clip(along, 0, 1) * math.pi) + 0.01
        body = np.clip(1 - np.abs(r - 0.82) / thick, 0, 1) * inside
        c = body * (0.4 + 0.6 * along)
        trail = (prev * 0.5) if prev is not None else 0
        c = np.maximum(c, trail)
        prev = c
        I = np.clip(c * 1.3, 0, 1)
        A = np.clip(c + _blur(c, s * 0.02) * 0.7, 0, 1) * (1 if t < 0.75 else (1 - t) / 0.25)
        out.append((I, A))
    return out


def g_beam(n: int, s: int, seed: int):
    """Rayon horizontal (tête à droite) : cœur blanc, bords turbulents qui défilent, tête qui brûle."""
    rng = np.random.default_rng(seed)
    L, w = s * 2, s // 2
    y, x = np.mgrid[0:w, 0:L].astype(np.float32)
    yn = (y - w / 2 + 0.5) / (w / 2)
    xn = x / L
    noise = _noise(w, L * 2, rng, 3, 6)
    out = []
    for i in range(n):
        sh = int(L * 2 * i / n)
        nz = np.roll(noise, -sh, axis=1)[:, :L]
        edge = 0.35 + 0.6 * nz
        body = np.clip((edge - np.abs(yn)) / 0.1, 0, 1)
        core = np.clip((0.28 - np.abs(yn)) / 0.1, 0, 1)
        start = np.clip(xn / 0.08, 0, 1)
        head = np.clip(1 - np.sqrt(((xn - 0.93) * 4) ** 2 + yn ** 2) / 0.5, 0, 1)
        I = np.clip(core * 1.2 + body * (0.45 + 0.4 * nz) + head * 1.2, 0, 1)
        A = np.clip(body * 0.95 + core + head, 0, 1) * start
        out.append((I, A))
    return out


def g_aura(n: int, s: int, seed: int):
    """Flammes qui montent (pour une aura derrière un perso)."""
    rng = np.random.default_rng(seed)
    w, h = s, int(s * 1.3)
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    xn = (x - w / 2 + 0.5) / (w / 2)
    yn = y / h
    noise = _noise(h * 2, w, rng, 4, 5)
    out = []
    for i in range(n):
        sh = int(h * 2 * i / n)
        nz = np.roll(noise, sh, axis=0)[:h]
        shape = np.clip(1 - np.abs(xn) / (0.95 - 0.55 * (1 - yn)), 0, 1) * np.clip(yn * 1.6, 0, 1)
        tongues = np.clip((nz - (0.62 - 0.35 * shape)) * 4, 0, 1) * shape
        I = np.clip(tongues * (0.4 + 0.9 * yn), 0, 1)
        A = np.clip(tongues * 1.2 + _blur(tongues, s * 0.05) * 0.5, 0, 1)
        out.append((I, A))
    return out


def g_charge(n: int, s: int, seed: int):
    """Charge : particules qui convergent vers le centre + cercle qui se resserre."""
    rng = random.Random(seed)
    r, th, x, y = _polar(s)
    pts = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.6, 1.0), rng.uniform(0, 1)) for _ in range(40)]
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        im = Image.new("L", (s, s), 0)
        d = ImageDraw.Draw(im)
        for a, R0, ph in pts:
            q = (t + ph) % 1.0
            R = R0 * (1 - q) * s / 2
            px, py = s / 2 + math.cos(a) * R, s / 2 + math.sin(a) * R
            rr = s * 0.012 * (1 + q)
            d.ellipse((px - rr, py - rr, px + rr, py + rr), fill=int(255 * (0.4 + 0.6 * q)))
        c = np.asarray(im).astype(np.float32) / 255
        R = 0.95 - 0.8 * t
        ring = np.clip(1 - abs(r - R) / 0.02, 0, 1) * 0.8
        core = np.clip(1 - r / (0.12 + 0.25 * t), 0, 1) * t
        I = np.clip(c + ring + core * 1.3, 0, 1)
        A = np.clip(c + ring + core + _blur(core, s * 0.05) * 0.6, 0, 1)
        out.append((I, A))
    return out


def g_smoke(n: int, s: int, seed: int):
    rng = np.random.default_rng(seed)
    r, th, x, y = _polar(s)
    nz = [_noise(s, s, rng, 4, 3) for _ in range(3)]
    out = []
    for i in range(n):
        t = i / max(1, n - 1)
        R = 0.3 + 0.6 * math.sqrt(t)
        n_ = nz[i % 3] * 0.6 + nz[(i + 1) % 3] * 0.4
        puff = np.clip((R - r * (0.7 + 0.6 * n_)) / 0.15, 0, 1)
        I = np.clip(0.25 + 0.5 * n_, 0, 1) * puff
        A = puff * (0.9 - 0.2 * n_) * (1 - t) ** 0.8
        out.append((I, A))
    return out


GEN = {"lightning": (g_lightning, 16), "orb": (g_orb, 24), "explosion": (g_explosion, 20), "hit": (g_hit, 10),
       "ring": (g_ring, 12), "slash": (g_slash, 10), "beam": (g_beam, 12), "aura": (g_aura, 16),
       "charge": (g_charge, 16), "smoke": (g_smoke, 16)}


@lru_cache(maxsize=64)
def _grey(name: str, size: int, seed: int):
    fn, n = GEN[name]
    return fn(n, size, seed)


@lru_cache(maxsize=256)
def frames(name: str, size: int = 256, color=(255, 255, 255), hot: float = 1.0, seed: int = 0) -> tuple:
    """Images RGBA de l'effet, colorisées (cache par couleur)."""
    if name not in GEN:
        return ()
    col = tuple(int(c) for c in color[:3])
    return tuple(colorize(I, A, col, hot) for I, A in _grey(name, size, seed))


def export(folder: Path, size: int = 256, color=(120, 200, 255)) -> list[Path]:
    """Écrit chaque effet en dossier `<nom>_frames/` (PNG transparents) pour les regarder / retoucher."""
    out = []
    for name in GEN:
        d = Path(folder) / f"{name}_frames"
        d.mkdir(parents=True, exist_ok=True)
        for i, im in enumerate(frames(name, size, color)):
            im.save(d / f"{i:03d}.png")
        out.append(d)
    return out


def sheet(name: str, size: int = 128, color=(120, 200, 255)) -> Image.Image:
    """Planche de contrôle d'un effet (toutes ses images côte à côte, sur fond sombre)."""
    fr = frames(name, size, color)
    if not fr:
        return Image.new("RGB", (size, size), (20, 20, 30))
    w, h = fr[0].size
    cols = min(12, len(fr))
    rows = math.ceil(len(fr) / cols)
    out = Image.new("RGBA", (w * cols, h * rows), (24, 24, 34, 255))
    for i, im in enumerate(fr):
        out.alpha_composite(im, ((i % cols) * w, (i // cols) * h))
    return out.convert("RGB")
