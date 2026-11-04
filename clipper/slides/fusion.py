"""Vidéo « Fusion Battle » (façon Suika Game) : des icônes tombent par un entonnoir dans un bol rond ;
deux icônes identiques qui se touchent fusionnent en l'icône du niveau suivant, plus grosse.

La chaîne de niveaux est libre (Goku base → SSJ1 → SSJ2…, grades JJK, primes One Piece, chats…) :
- soit des persos de la bibliothèque, cochés dans l'ordre ;
- soit un dossier library/_fusion/<nom>/ avec des images numérotées (1.png, 2.png…), idéalement des PNG sans fond.

Son : un bruitage au choix (library/_sounds/*.mp3|wav, ou un « pop » synthétisé). À chaque fusion il est rejoué
de plus en plus grave, gras (saturé) et avec de l'écho selon le niveau : c'est ce qui rend la vidéo drôle/satisfaisante.

Rendu image par image avec Pillow, encodé par ffmpeg (H.264 9:16), comme la Battle.
"""
from __future__ import annotations

import json
import math
import random
import subprocess
import wave
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import config, db
from ..util import log, require_bin
from . import render

RATE = 44100
SOUND_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
TIER_COLORS = ["#7bd389", "#4cc9f0", "#3a86ff", "#8338ec", "#ff5dc8", "#ef476f", "#ff9f1c", "#ffd60a",
               "#f72585", "#06d6a0", "#e5e5e5", "#ff3b3b"]


def fcfg() -> dict:
    return config.get()["slides"].get("fusion", {})


def out_dir() -> Path:
    d = config.data_dir() / "fusions"
    d.mkdir(parents=True, exist_ok=True)
    return d


def sounds_dir() -> Path:
    from . import library
    d = library.root() / "_sounds"
    d.mkdir(parents=True, exist_ok=True)
    return d


def chains_dir() -> Path:
    from . import library
    d = library.root() / "_fusion"
    d.mkdir(parents=True, exist_ok=True)
    return d


# --------------------------------------------------------------------------- son

def load_sound(path: str | Path | None):
    """Bruitage → tableau mono float32 (44,1 kHz). Sans fichier : petit « bloop » synthétisé."""
    import numpy as np
    if path and Path(path).is_file():
        ffmpeg = require_bin("ffmpeg")
        r = subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(path), "-t", "4", "-ac", "1", "-ar", str(RATE),
                            "-f", "f32le", "-"], capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 400:
            a = np.frombuffer(r.stdout, dtype=np.float32).copy()
            nz = np.nonzero(np.abs(a) > 0.01)[0]            # on coupe le silence au début / à la fin
            if len(nz):
                a = a[max(0, nz[0] - 50): nz[-1] + 200]
            peak = float(np.max(np.abs(a))) or 1.0
            return a / peak
        log.warning("son %s illisible : on prend le pop par défaut", Path(path).name)
    t = np.arange(int(0.16 * RATE)) / RATE
    f = 950 * np.exp(-t * 9) + 380                            # « bloop » qui descend
    return (np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 18)).astype(np.float32)


def _lowpass(x, cutoff: float):
    import numpy as np
    n = len(x)
    spec = np.fft.rfft(x, n * 2)
    freqs = np.fft.rfftfreq(n * 2, 1 / RATE)
    spec *= 1 / (1 + (freqs / cutoff) ** 4)
    return np.fft.irfft(spec, n * 2)[:n].astype(np.float32)


def tier_sound(base, tier: int, tiers: int, step: float | None = None, fat: float = 1.0):
    """Le bruitage au niveau `tier` (0 = le plus petit) : plus grave, plus gras, plus d'écho à chaque niveau."""
    import numpy as np
    k = tier / max(1, tiers - 1)                              # 0 → 1
    step = step if step is not None else min(3.0, 24.0 / max(1, tiers - 1))  # demi-tons en moins par niveau
    ratio = 2 ** (-(tier * step) / 12)                        # < 1 : plus lent et plus grave (voix de « gros »)
    n = len(base)
    m = int(n / ratio)
    x = np.interp(np.arange(m) * ratio, np.arange(n), base).astype(np.float32)
    # basses : on ajoute la partie grave du son, de plus en plus fort
    x = x + _lowpass(x, 220) * (2.2 * k * fat)
    # « gras » : saturation douce qui augmente
    drive = 1 + 5 * k * fat
    x = np.tanh(x * drive) / math.tanh(drive)
    # écho : répétitions qui s'allongent et durent plus longtemps
    if k > 0:
        delay = int((0.07 + 0.11 * k) * RATE)
        taps = 1 + int(4 * k)
        out = np.zeros(len(x) + delay * taps, dtype=np.float32)
        out[:len(x)] += x
        g = 0.35 + 0.25 * k
        for i in range(1, taps + 1):
            out[i * delay: i * delay + len(x)] += x * (g ** i)
        x = out
    peak = float(np.max(np.abs(x))) or 1.0
    return (x / peak * (0.55 + 0.35 * k)).astype(np.float32)


def write_wav(path: Path, audio) -> None:
    import numpy as np
    a = np.clip(audio, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


def mix_events(events: list[tuple[float, int]], duration: float, tiers: int, sound: str | None,
               step: float | None = None, fat: float = 1.0):
    """Piste son de la vidéo : un bruitage par fusion, au niveau atteint."""
    import numpy as np
    paths = [x for x in (sound if isinstance(sound, (list, tuple)) else str(sound or "").split("|")) if x] or [None]
    bases = [load_sound(x) for x in paths]                  # plusieurs sons (04/11 : « varie les sons ») : du plus
    cache = {}                                              # léger (petits niveaux) au plus lourd (formes finales)
    n = int(duration * RATE) + RATE
    audio = np.zeros(n, dtype=np.float32)
    for t, tier in events:
        if tier not in cache:
            base = bases[min(len(bases) - 1, tier * len(bases) // max(1, tiers))]
            cache[tier] = tier_sound(base, tier, tiers, step, fat)
        s = cache[tier]
        i = int(t * RATE)
        if i >= n:
            continue
        seg = s[: n - i]
        audio[i:i + len(seg)] += seg
    out = np.tanh(audio * 1.1) / math.tanh(1.1)                # limiteur doux (plusieurs fusions en même temps)
    return out * float(fcfg().get("volume", 0.13))             # niveau général (03/11 : « le son est bcp trop fort »)


def preview(sound: str | None, tiers: int = 7, step: float | None = None, fat: float = 1.0) -> Path:
    """Aperçu : le bruitage joué à chaque niveau, du plus petit au plus gros (pour choisir son son)."""
    gap = 0.55
    events = [(0.1 + i * gap * (1 + i * 0.08), i) for i in range(tiers)]
    dur = events[-1][0] + 2.5
    p = out_dir() / "_preview.wav"
    write_wav(p, mix_events(events, dur, tiers, sound, step, fat))
    return p


def sound_list() -> list[dict]:
    return [{"name": p.name, "path": str(p)} for p in sorted(sounds_dir().iterdir())
            if p.is_file() and p.suffix.lower() in SOUND_EXT]


def sound_path(name: str | None) -> str | None:
    if not name:
        return None
    p = sounds_dir() / Path(name).name
    return str(p) if p.is_file() else None


# --------------------------------------------------------------------------- chaînes de niveaux

def chain_list() -> list[dict]:
    """Dossiers library/_fusion/<nom>/ : une chaîne prête (images triées par nom = ordre des niveaux)."""
    out = []
    for d in sorted(chains_dir().iterdir()):
        if d.is_dir():
            imgs = chain_images(d.name)
            if len(imgs) >= 2:
                out.append({"name": d.name, "count": len(imgs)})
    return out


def _natkey(p: Path):
    import re
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", p.stem)]


import re as _re


def _order_file(d: Path) -> list[tuple[Path, str]] | None:
    """ordre.txt (optionnel) : une ligne par niveau, du plus petit au plus gros : « fichier = Nom affiché »
    (ou juste « fichier »). Permet de fixer l'ordre sans renommer les images."""
    for fn in ("ordre.txt", "order.txt"):
        f = d / fn
        if f.is_file():
            files = {p.name.lower(): p for p in d.iterdir() if p.suffix.lower() in IMG_EXT}
            stems = {p.stem.lower(): p for p in files.values()}
            for p in files.values():                      # « 5 SSJGOD.jpg » est aussi trouvé par « SSJGOD »
                stems.setdefault(_re.sub(r"^\d+[\s._-]*", "", p.stem).lower(), p)
            out = []
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, _, label = line.partition("=")
                key = key.strip().lower()
                p = files.get(key) or stems.get(key) or stems.get(Path(key).stem) \
                    or stems.get(_re.sub(r"^\d+[\s._-]*", "", Path(key).stem))
                if p:
                    out.append((p, label.strip() or p.stem))
            return out
    return None


def chain_images(name: str) -> list[Path]:
    d = chains_dir() / Path(name).name
    if not d.is_dir():
        return []
    listed = _order_file(d)
    if listed is not None:
        return [p for p, _ in listed]
    return sorted((p for p in d.iterdir() if p.suffix.lower() in IMG_EXT), key=_natkey)


def tiers_from_chain(name: str) -> list[dict]:
    import re
    d = chains_dir() / Path(name).name
    listed = _order_file(d) if d.is_dir() else None
    if listed is not None:
        out = []
        for p, label in listed:                            # « Zoro.jpeg = Zoro | easter » → easter egg, pas un niveau
            lab, _, flag = label.partition("|")
            out.append({"name": lab.strip() or p.stem, "image_path": str(p), "easter": "easter" in flag.lower()})
        return out
    out = []
    for p in chain_images(name):
        label = re.sub(r"^\d+[\s._-]*", "", p.stem).replace("_", " ").strip() or p.stem
        out.append({"name": label, "image_path": str(p)})
    return out


# --------------------------------------------------------------------------- simulation

@dataclass
class Ball:
    tier: int
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    born: float = 0.0
    alive: bool = True


@dataclass
class Drop:                    # icône qui descend dans l'entonnoir (animation, pas encore dans la physique)
    tier: int
    t0: float


@dataclass
class Sim:
    cx: float
    cy: float
    R: float
    radii: list
    top: int                                   # dernier niveau (le « boss »)
    balls: list = field(default_factory=list)
    t: float = 0.0
    g: float = 0.0
    rnd: random.Random = field(default_factory=random.Random)
    events: list = field(default_factory=list)  # (temps, niveau) des fusions → son
    rings: list = field(default_factory=list)   # (x, y, rayon, temps, niveau) des fusions → effet visuel
    best: int = 0
    bounce: bool = True                         # True : les icônes rebondissent partout ; False : tas façon Suika
    speed: float = 0.0                          # vitesse entretenue en mode rebond (px/s)
    pull: float = 0.0                           # attraction discrète entre icônes identiques (évite les blocages)
    done_at: float = -1.0


def radii_for(tiers: int, R: float) -> list[float]:
    r_max = R * 0.40
    r_min = R * max(0.10 if tiers <= 8 else 0.08, min(0.17, 0.42 / (1.25 ** (tiers - 1))))
    if tiers == 1:
        return [r_max]
    g = (r_max / r_min) ** (1 / (tiers - 1))
    return [r_min * g ** i for i in range(tiers)]


def setup(tiers: int, W: int, H: int, seed: int, bounce: bool = True, speed: float = 0.6,
          cx: float | None = None, cy: float | None = None, R: float | None = None) -> Sim:
    R = R or W * 0.44
    sim = Sim(cx=W / 2 if cx is None else cx, cy=H * 0.535 if cy is None else cy, R=R, radii=radii_for(tiers, R),
              top=tiers - 1, rnd=random.Random(seed))
    sim.g = R * 2.6
    sim.bounce = bounce
    if bounce:                                  # gravité légère (petites courbes), chocs élastiques, vitesse entretenue
        sim.g = R * 0.25
        sim.speed = R * speed
    return sim


def spawn_tier(sim: Sim) -> int:
    """Comme Suika : on lâche surtout des petits niveaux, en privilégiant ceux qui ont un « partenaire » seul."""
    hi = max(1, min(4, sim.top // 2, sim.best + 1))      # jamais une forme pas encore apparue (pas de spoil)
    alone = [t for t in range(hi) if sum(1 for b in sim.balls if b.alive and b.tier == t) % 2 == 1]
    if alone and sim.rnd.random() < 0.55:
        return sim.rnd.choice(alone)
    w = [0.5, 0.27, 0.15, 0.08][:hi]
    return sim.rnd.choices(range(hi), weights=w)[0]


def drop_gap(sim: Sim, base: float, low: float) -> float:
    """Délai entre deux lâchers : plus lent quand il y a peu de niveaux (la vidéo dure ~30-60 s quoi qu'il arrive)."""
    f = max(0.55, min(2.6, 2 ** ((6 - sim.top) * 0.55)))
    return max(low * f, (base - sim.t * 0.01) * f)


def fill_ratio(sim: Sim) -> float:
    return sum(sim.radii[b.tier] ** 2 for b in sim.balls if b.alive) / sim.R ** 2


def physics_step(sim: Sim, dt: float) -> None:
    balls = [b for b in sim.balls if b.alive]
    R, cx, cy = sim.R, sim.cx, sim.cy
    for b in balls:
        b.vy += sim.g * dt
        if sim.bounce:                                # chaque icône garde à peu près sa vitesse (les grosses un peu moins)
            want = sim.speed * (1.0 - 0.35 * b.tier / max(1, sim.top))
            v = math.hypot(b.vx, b.vy)
            if v < 1e-3:
                a = sim.rnd.uniform(0, 2 * math.pi)
                b.vx, b.vy, v = math.cos(a) * want, math.sin(a) * want, want
            k = 1 + (want / v - 1) * min(1.0, dt * 3)
            b.vx *= k
            b.vy *= k
        else:
            b.vx *= 0.999
            b.vy *= 0.999
    if sim.pull > 0:                                  # rapproche un peu les jumeaux proches
        for i, a in enumerate(balls):
            for b in balls[i + 1:]:
                if a.tier != b.tier or a.tier >= sim.top:
                    continue
                dx, dy = b.x - a.x, b.y - a.y
                d = math.hypot(dx, dy) or 1e-6
                reach = (sim.radii[a.tier] + sim.radii[b.tier]) * 3.0
                if d < reach:
                    f = sim.pull * sim.g * dt / d
                    a.vx += dx * f
                    a.vy += dy * f
                    b.vx -= dx * f
                    b.vy -= dy * f
    for b in balls:
        b.x += b.vx * dt
        b.y += b.vy * dt
    for _ in range(3):                                # contraintes : chocs entre icônes + paroi du bol
        for i, a in enumerate(balls):
            if not a.alive:
                continue
            ra = sim.radii[a.tier]
            for b in balls[i + 1:]:
                if not b.alive:
                    continue
                rb = sim.radii[b.tier]
                dx, dy = b.x - a.x, b.y - a.y
                d2 = dx * dx + dy * dy
                lim = ra + rb
                if d2 >= lim * lim:
                    continue
                d = math.sqrt(d2) or 1e-6
                if a.tier == b.tier and a.tier < sim.top:
                    merge(sim, a, b)
                    break
                nx, ny = dx / d, dy / d
                over = lim - d
                ma, mb = ra * ra, rb * rb
                wa, wb = mb / (ma + mb), ma / (ma + mb)
                a.x -= nx * over * wa
                a.y -= ny * over * wa
                b.x += nx * over * wb
                b.y += ny * over * wb
                rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
                if rel < 0:
                    j = -(2.0 if sim.bounce else 1.25) * rel
                    a.vx -= nx * j * wa
                    a.vy -= ny * j * wa
                    b.vx += nx * j * wb
                    b.vy += ny * j * wb
        for b in balls:
            if not b.alive:
                continue
            r = sim.radii[b.tier]
            dx, dy = b.x - cx, b.y - cy
            d = math.hypot(dx, dy) or 1e-6
            if d + r > R:
                nx, ny = dx / d, dy / d
                b.x, b.y = cx + nx * (R - r), cy + ny * (R - r)
                vn = b.vx * nx + b.vy * ny
                if vn > 0:
                    e = 2.0 if sim.bounce else 1.3
                    b.vx -= e * vn * nx
                    b.vy -= e * vn * ny
                    if not sim.bounce:
                        b.vx *= 0.985
    sim.balls = [b for b in sim.balls if b.alive]
    sim.t += dt


def merge(sim: Sim, a: Ball, b: Ball) -> None:
    a.alive = b.alive = False
    t = a.tier + 1
    ra, rb = sim.radii[a.tier], sim.radii[t]
    x, y = (a.x + b.x) / 2, (a.y + b.y) / 2
    dx, dy = x - sim.cx, y - sim.cy                       # le nouveau doit tenir dans le bol
    d = math.hypot(dx, dy) or 1e-6
    if d + rb > sim.R:
        x, y = sim.cx + dx / d * (sim.R - rb), sim.cy + dy / d * (sim.R - rb)
    nb = Ball(t, x, y, (a.vx + b.vx) / 2, (a.vy + b.vy) / 2 - (0 if sim.bounce else sim.R * 0.25), born=sim.t)
    sim.balls.append(nb)
    sim.events.append((sim.t, t))
    sim.rings.append((x, y, rb, sim.t, t))
    sim.best = max(sim.best, t)
    if t >= sim.top and sim.done_at < 0:
        sim.done_at = sim.t


# --------------------------------------------------------------------------- dessin

def icon(path: str | None, size: int, color: tuple) -> Image.Image:
    """Icône ronde centrée sur la tête du perso (quel que soit le format de l'image). PNG sans fond : posé sur
    un disque coloré. Image coupée à l'intérieur de l'anneau, anneau par-dessus, bords lissés (04/11 : l'image
    dépassait du cercle)."""
    from . import faces
    ss = 3                                                     # suréchantillonnage : bords nets et lissés
    S = size * ss
    ring = max(3, size // 16) * ss
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).ellipse((ring // 2, ring // 2, S - 1 - ring // 2, S - 1 - ring // 2), fill=255)
    if path and Path(path).exists():
        with Image.open(path) as src:
            src.load()
            transparent = src.mode in ("RGBA", "LA", "P") and src.convert("RGBA").getextrema()[3][0] < 250
            im = src.convert("RGBA") if transparent else src.convert("RGB")
        sq = faces.head_square(im, path, vision=bool(fcfg().get("vision_faces", True)))
        sq = sq.resize((S, S), Image.LANCZOS).convert("RGBA")
        if transparent:
            disk = Image.new("RGBA", (S, S), tuple(int(c * 0.35) for c in color) + (255,))
            disk.alpha_composite(sq)
            sq = disk
        out.paste(sq, (0, 0), mask)
    else:
        ImageDraw.Draw(out).ellipse((0, 0, S - 1, S - 1), fill=color + (255,))
    ImageDraw.Draw(out).ellipse((1, 1, S - 2, S - 2), outline=color + (255,), width=ring)
    return out.resize((size, size), Image.LANCZOS)


def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Painter:
    def __init__(self, sim: Sim, tiers: list[dict], W: int, H: int, title: str, funnel_top: float | None = None,
                 with_bg: bool = True):
        self.sim, self.tiers, self.W, self.H, self.title = sim, tiers, W, H, title
        self.k = W / 1080
        self.colors = [hex_rgb(TIER_COLORS[i % len(TIER_COLORS)]) for i in range(len(tiers))]
        self.icons = {}
        self.neck = neck_width(sim)
        self.funnel_top = H * 0.155 if funnel_top is None else funnel_top
        self.bowl_top = sim.cy - sim.R
        self.bg = self._background() if with_bg else None

    def get_icon(self, tier: int, size: int) -> Image.Image:
        size = max(8, int(size))
        key = (tier, size)
        if key not in self.icons:
            big = (tier, "src")
            if big not in self.icons:
                self.icons[big] = icon(self.tiers[tier].get("image_path"), 512, self.colors[tier])
            self.icons[key] = self.icons[big].resize((size, size), Image.LANCZOS)
        return self.icons[key]

    def get_glow(self, tier: int, r: float) -> Image.Image:
        key = ("glow", tier)
        if key not in self.icons:
            size = int(r * 3)
            g = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse((size / 2 - r * 1.05, size / 2 - r * 1.05, size / 2 + r * 1.05, size / 2 + r * 1.05),
                                      fill=self.colors[tier] + (130,))
            self.icons[key] = g.filter(ImageFilter.GaussianBlur(r * 0.25))
        return self.icons[key]

    def _background(self) -> Image.Image:
        bg = Image.new("RGBA", (self.W, self.H), (12, 12, 22, 255))
        self.draw_bowl(bg)
        W, H, k = self.W, self.H, self.k
        d = ImageDraw.Draw(bg)
        tf = render.font(int(84 * k))
        y = int(H * 0.035)
        for line in render.wrap(self.title.upper(), tf, int(W * 0.88), d)[:2]:
            d.text((W / 2, y), line, font=tf, anchor="ma", fill=(240, 242, 250), stroke_width=int(3 * k),
                   stroke_fill=(0, 0, 0))
            y += int(sum(tf.getmetrics()) * 1.02)
        return bg

    def draw_bowl(self, bg: Image.Image, neon: tuple | None = None) -> None:
        """Bol rond + tube au-dessus, néon (dessiné une fois, sur le fond). Sans couleur : arc-en-ciel
        (vert en haut à gauche → jaune → orange → rose en bas → violet → bleu → cyan en haut à droite)."""
        import colorsys
        W, H, k, s = self.W, self.H, self.k, self.sim
        gap = math.asin(min(0.99, self.neck / s.R))           # ouverture du bol en haut
        start, end = -90 + math.degrees(gap), 270 - math.degrees(gap)
        box = (s.cx - s.R - 6 * k, s.cy - s.R - 6 * k, s.cx + s.R + 6 * k, s.cy + s.R + 6 * k)
        top = self.funnel_top - s.radii[0] * 1.2            # tube droit (comme les vidéos virales)
        fl = [(s.cx - self.neck - 6 * k, top), (s.cx - self.neck - 6 * k, self.bowl_top - 4 * k)]
        fr = [(s.cx + self.neck + 6 * k, top), (s.cx + self.neck + 6 * k, self.bowl_top - 4 * k)]

        def col(phi: float) -> tuple:                        # phi = angle Pillow (degrés, sens horaire depuis 3 h)
            if neon:
                return neon
            theta = (270 - phi) % 360                        # 0 = en haut, en tournant par la gauche
            h = ((120 - theta * 300 / 360) % 360) / 360
            return tuple(int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.85, 1.0))

        def light(c):
            return tuple(int(v + (255 - v) * 0.45) for v in c)
        d = ImageDraw.Draw(bg)
        d.ellipse((s.cx - s.R, s.cy - s.R, s.cx + s.R, s.cy + s.R), fill=(14, 15, 26, 255))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        steps = 180
        segs = [(start + (end - start) * i / steps, start + (end - start) * (i + 1) / steps) for i in range(steps)]
        for a0, a1 in segs:
            gd.arc(box, a0, a1 + 0.6, fill=col((a0 + a1) / 2) + (255,), width=int(24 * k))
        cl, cr = col(end), col(start)                        # tube : gauche = haut-gauche du bol, droite = haut-droite
        gd.line(fl, fill=cl + (255,), width=int(20 * k))
        gd.line(fr, fill=cr + (255,), width=int(20 * k))
        bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(16 * k)))
        d = ImageDraw.Draw(bg)
        for a0, a1 in segs:
            d.arc(box, a0, a1 + 0.6, fill=light(col((a0 + a1) / 2)), width=int(9 * k))
        d.line(fl, fill=light(cl), width=int(9 * k))
        d.line(fr, fill=light(cr), width=int(9 * k))

    def frame(self, drop: Drop | None = None, nxt: int | None = None, tube: list | None = None) -> Image.Image:
        img = self.bg.copy()
        self.draw_dynamic(img, drop, nxt, tube)
        return img.convert("RGB")

    def draw_dynamic(self, img: Image.Image, drop: Drop | None = None, nxt: int | None = None,
                     tube: list | None = None) -> None:
        """Icônes, chute dans le tube, anneaux de fusion (sur une image RGBA)."""
        s, k = self.sim, self.k
        for ty in tube or []:                                 # colonne du tout début, encore dans le tube
            r = s.radii[0]
            img.alpha_composite(self.get_icon(0, 2 * r), (int(s.cx - r), int(ty - r)))
        if tube:
            nxt = None
        if nxt is not None and drop is None:                  # prochaine icône, en attente en haut de l'entonnoir
            r = s.radii[nxt]
            ic = self.get_icon(nxt, 2 * r)
            img.alpha_composite(ic, (int(s.cx - r), int(self.funnel_top - r * 0.6)))
        if drop is not None:
            x, y = self.drop_pos(drop)
            r = s.radii[drop.tier]
            img.alpha_composite(self.get_icon(drop.tier, 2 * r), (int(x - r), int(y - r)))
        for b in s.balls:                                     # halo coloré derrière chaque icône
            r = s.radii[b.tier]
            gl = self.get_glow(b.tier, r)
            img.alpha_composite(gl, (int(b.x - gl.width / 2), int(b.y - gl.height / 2)))
        for b in s.balls:
            r = s.radii[b.tier]
            age = s.t - b.born
            if b.born > 0 and age < 0.18:                      # petit « pop » de naissance
                r *= 1 + 0.22 * math.sin(age / 0.18 * math.pi)
            img.alpha_composite(self.get_icon(b.tier, 2 * r), (int(b.x - r), int(b.y - r)))
        for (x, y, r, t0, tier) in s.rings:                    # anneau qui s'étend à chaque fusion
            a = (s.t - t0) / 0.35
            if 0 <= a < 1:
                rr = r * (1 + 0.6 * a)
                col = self.colors[tier] + (int(255 * (1 - a)),)
                over = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ImageDraw.Draw(over).ellipse((x - rr, y - rr, x + rr, y + rr), outline=col,
                                             width=max(3, int(10 * k * (1 - a))))
                img.alpha_composite(over)
        s.rings = [g for g in s.rings if s.t - g[3] < 0.4]

    def drop_pos(self, drop: Drop) -> tuple[float, float]:
        return drop_pos(self.sim, self.funnel_top, drop)

    def final(self, t: float) -> Image.Image:
        """Écran de fin : la forme finale en grand + appel à s'abonner."""
        W, H, k = self.W, self.H, self.k
        img = Image.new("RGBA", (W, H), (12, 12, 22, 255))
        d = ImageDraw.Draw(img)
        top = self.sim.top
        a = min(1.0, t / 0.4)
        size = int(W * 0.62 * (0.7 + 0.3 * a))
        col = self.colors[top]
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((W / 2 - size * 0.62, H * 0.44 - size * 0.62, W / 2 + size * 0.62,
                                      H * 0.44 + size * 0.62), fill=col + (150,))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60 * k)))
        img.alpha_composite(self.get_icon(top, size), (int(W / 2 - size / 2), int(H * 0.44 - size / 2)))
        f1, f2 = render.font(int(110 * k)), render.font(int(78 * k))
        d.text((W / 2, H * 0.12), "FINAL FORM", font=f1, anchor="ma", fill=col, stroke_width=int(4 * k),
               stroke_fill=(0, 0, 0))
        y = H * 0.44 + size / 2 + 50 * k
        for line in render.wrap(self.tiers[top]["name"].upper(), f2, int(W * 0.88), d)[:2]:
            d.text((W / 2, y), line, font=f2, anchor="ma", fill=(255, 255, 255), stroke_width=int(3 * k),
                   stroke_fill=(0, 0, 0))
            y += int(sum(f2.getmetrics()) * 1.05)
        cta = (render.rcfg().get("end_cta") or "").strip()
        if cta:                                               # « Follow @animelorehq for more 🔥 » (emoji en couleur)
            render.draw_rich(img, (W / 2, H * 0.86), cta, render.font(int(52 * k)), render.rcfg()["accent_color"],
                             "ma", int(3 * k), (0, 0, 0))
        return img.convert("RGB")


DROP_TIME = 0.32


def neck_width(sim: Sim) -> float:
    return max(sim.radii[: max(1, min(3, sim.top))]) * 1.25


def drop_pos(sim: Sim, funnel_top: float, drop: Drop) -> tuple[float, float]:
    """Position de l'icône qui descend le tube (part de la place « en attente »)."""
    r = sim.radii[drop.tier]
    y0, y1 = funnel_top + r * 0.4, sim.cy - sim.R + r + 4
    a = min(1.0, (sim.t - drop.t0) / DROP_TIME)
    return sim.cx, y0 + (y1 - y0) * a * a


class Feeder:
    """Lâchers d'icônes + anti-blocage pour un bol (même logique pour la vidéo seule et la course)."""

    def __init__(self, sim: Sim, funnel_top: float, c: dict):
        self.sim, self.funnel_top = sim, funnel_top
        self.gap0, self.gap1 = float(c.get("drop_every", 0.55)), float(c.get("drop_every_min", 0.26))
        self.max_s = float(c.get("max_seconds", 120))
        self.drop, self.nxt, self.next_drop = None, spawn_tier(sim), 0.6
        self.burst = 0
        self.tube: list[float] = []                       # icônes de la colonne de départ encore dans le tube
        if c.get("fast_start", True):                     # accroche : une colonne d'icônes du tube jusqu'au fond
            self._column()

    def _column(self) -> None:
        """Tout début (comme les vidéos virales) : une file d'icônes de base qui tombe du haut du tube jusqu'en
        bas du bol. Espacées : elles ne fusionnent qu'en bas, quand la première rebondit sur les suivantes."""
        sim = self.sim
        r = sim.radii[0]
        step = 2.3 * r
        self.col_v = sim.speed if sim.bounce else sim.R * 1.1   # même vitesse partout : pas de rattrapage en haut
        y = sim.cy + sim.R * 0.78
        top = self.funnel_top - r * 0.2
        entry = sim.cy - sim.R + r + 4
        while y > top:
            if y >= entry:
                sim.balls.append(Ball(0, sim.cx + sim.rnd.uniform(-3, 3), y, sim.rnd.uniform(-0.04, 0.04) * sim.R,
                                      self.col_v))
            else:
                self.tube.append(y)
            y -= step
        self.next_drop = 99.0                             # les lâchers normaux reprennent après la colonne

    def tick(self, frame_dt: float, sub: int) -> None:
        sim = self.sim
        if self.tube:                                     # la colonne continue de descendre dans le tube
            entry = sim.cy - sim.R + sim.radii[0] + 4
            v = self.col_v
            moved = []
            for y in self.tube:
                y += v * frame_dt
                if y >= entry:
                    sim.balls.append(Ball(0, sim.cx + sim.rnd.uniform(-3, 3), entry,
                                          sim.rnd.uniform(-0.04, 0.04) * sim.R, v))
                else:
                    moved.append(y)
            self.tube = moved
            if not self.tube:
                self.next_drop = sim.t + 0.25
        # lâcher : on accélère au fil de la vidéo, on attend si le bol est trop plein
        if self.drop is None and sim.t >= self.next_drop and sim.done_at < 0 and fill_ratio(sim) < 0.60:
            self.drop, self.nxt = Drop(self.nxt, sim.t), spawn_tier(sim)

        if self.drop is not None and sim.t - self.drop.t0 >= DROP_TIME:
            x, y = drop_pos(sim, self.funnel_top, self.drop)
            sim.balls.append(Ball(self.drop.tier, x + sim.rnd.uniform(-2, 2), y, sim.rnd.uniform(-30, 30),
                                  sim.R * 1.4))
            self.drop = None
            self.next_drop = sim.t + drop_gap(sim, self.gap0, self.gap1)
        # anti-blocage discret : plus ça stagne / plus le bol est plein, plus les jumeaux s'attirent
        stuck = sim.t - (sim.events[-1][0] if sim.events else 0)
        sim.pull = min(3.0, 0.15 + max(0.0, stuck - 4) * 0.25 + max(0.0, fill_ratio(sim) - 0.5) * 4)
        if sim.t < 3.0:                                    # début : les icônes du bas se trouvent vite
            sim.pull = max(sim.pull, 1.2)
        if sim.t > self.max_s:
            sim.pull = 6.0
        for _ in range(sub):
            physics_step(sim, frame_dt / sub)

    @property
    def waiting(self) -> int | None:
        return self.nxt if self.sim.done_at < 0 else None


# --------------------------------------------------------------------------- génération

def _easter_overlay(img: Image.Image, egg: dict, icon_im: Image.Image, t: float, sim, W: int, H: int) -> Image.Image:
    """Easter egg (idée de l'utilisateur : « un Zoro qui s'est perdu ») : le perso entre par le côté en bas, hésite,
    regarde à gauche et à droite (« ? »), dit sa réplique, puis repart… dans le mauvais sens. ~5 s, purement visuel."""
    k = W / 1080
    D = 6.0
    if not (0 <= t < D):
        return img
    size = icon_im.width
    y0 = min(H * 0.93 - size / 2, sim.cy + sim.R + size * 1.15)   # sous le bol, sans le toucher
    xs, xm = W + size, W * 0.62
    if t < 1.3:                                             # entre en marchant (petits sauts)
        a = t / 1.3
        x = xs + (xm - xs) * (1 - (1 - a) ** 2)
        hop = abs(math.sin(t * 9)) * 14 * k
        flip = False
    elif t < 4.2:                                           # perdu : regarde à gauche, à droite
        x, hop = xm, 0
        flip = int((t - 1.3) / 0.6) % 2 == 1
    else:                                                   # repart dans le mauvais sens (vers la droite)
        a = (t - 4.2) / (D - 4.2)
        x = xm + (xs - xm) * a ** 1.6
        hop = abs(math.sin(t * 9)) * 14 * k
        flip = False
    im = icon_im.transpose(Image.FLIP_LEFT_RIGHT) if flip else icon_im
    img = img.convert("RGBA")
    img.alpha_composite(im, (int(x - size / 2), int(y0 - size / 2 - hop)))
    d = ImageDraw.Draw(img)
    if 1.3 <= t < 4.2:
        for j in range(3):                                  # « ? » qui sautillent
            if t - 1.3 > j * 0.25:
                qx = x + (j - 1) * size * 0.35
                qy = y0 - size * 0.62 - abs(math.sin(t * 6 + j)) * 10 * k
                d.text((qx, qy), "?", font=render.font(int(64 * k)), anchor="mm", fill=(255, 214, 10),
                       stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
    if 1.8 <= t < 5.0 and egg.get("text"):                  # bulle : « Where am I? »
        f = render.font(int(54 * k))
        txt = egg["text"]
        tw = render.text_width(d, txt, f) + 40 * k
        bx, by = max(tw / 2 + 20 * k, x - size * 0.62 - tw / 2), y0 - size * 0.1
        d.rounded_rectangle((bx - tw / 2, by - 36 * k, bx + tw / 2, by + 36 * k), radius=24 * k, fill=(255, 255, 255),
                            outline=(0, 0, 0), width=int(4 * k))
        d.polygon(((bx + tw / 2 - 4 * k, by - 12 * k), (bx + tw / 2 - 4 * k, by + 12 * k), (x - size * 0.45, by)),
                  fill=(255, 255, 255))
        render.draw_rich(img, (bx, by - 22 * k), txt, f, (0, 0, 0), "ma", 0, (0, 0, 0))
    return img.convert("RGB")


def generate(tiers: list[dict], title: str = "Fusion Battle", sound: str | None = None, seed: int | None = None,
             step: float | None = None, fat: float = 1.0, out: Path | None = None, easter: dict | None = None,
             opts: dict | None = None, music: str | None = None, music_gain: float = 0.5) -> Path:
    """Simule et rend la vidéo jusqu'à l'apparition du dernier niveau. Rend le chemin du MP4.
    `easter` = {"image_path", "name", "text"} : un perso « perdu » traverse l'écran juste avant la forme finale
    (aussi : ligne « fichier = Nom | easter » dans ordre.txt)."""
    c = dict(fcfg())
    c.update(opts or {})                                   # réglages ponctuels (ex. lâchers plus lents : ≥ 30 s)
    eggs = [t for t in tiers if t.get("easter")]
    tiers = [t for t in tiers if not t.get("easter")]
    if easter is None and eggs:
        easter = {**eggs[0], "text": f"Where am I? 🗺️"}
    if len(tiers) < 3:
        raise ValueError("Il faut au moins 3 niveaux")
    tiers = tiers[:10]
    W, H = (int(v) for v in c.get("size", [1080, 1920]))
    fps = int(c.get("fps", 30))
    seed = int(seed if seed is not None else random.randrange(1_000_000))
    sim = setup(len(tiers), W, H, seed, bounce=str(c.get("style", "bounce")) != "pile",
                speed=float(c.get("speed", 0.6)))
    painter = Painter(sim, tiers, W, H, title)
    out = out or out_dir() / f"fusion_{seed}.mp4"
    tmp_video = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp_video)], stdin=subprocess.PIPE)
    sub = int(c.get("substeps", 6))
    max_s = float(c.get("max_seconds", 120))
    feeder = Feeder(sim, painter.funnel_top, c)
    frames = 0
    end_hold = int(fps * 0.5)
    egg_t0 = None
    egg_icon = icon(easter.get("image_path"), int(W * 0.26), (120, 200, 120)) if easter else None
    try:
        while True:
            feeder.tick(1 / fps, sub)
            im = painter.frame(feeder.drop, feeder.waiting, feeder.tube)
            if easter and egg_t0 is None and sim.best >= sim.top - 1:   # l'avant-dernière forme vient d'apparaître
                egg_t0 = sim.t + 0.6
            if egg_t0 is not None:
                im = _easter_overlay(im, easter, egg_icon, sim.t - egg_t0, sim, W, H)
            proc.stdin.write(im.tobytes())
            frames += 1
            if sim.done_at >= 0 and sim.t - sim.done_at >= end_hold / fps and \
                    (egg_t0 is None or sim.t - egg_t0 >= 6.0):     # on laisse l'easter egg finir
                break
            if sim.t > max_s * 1.6:                        # filet de sécurité absolu
                log.warning("fusion : dernier niveau pas atteint, on termine quand même")
                break
        fin = int(fps * float(c.get("final_seconds", 1.5)))
        for f in range(fin):
            proc.stdin.write(painter.final(f / fps).tobytes())
        frames += fin
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué pendant l'encodage de la vidéo")
    finally:
        if proc.poll() is None:
            proc.kill()
    duration = frames / fps
    wav = out.with_suffix(".wav")
    audio = mix_events(sim.events, duration, len(tiers), sound, step, fat)
    if music:                                              # musique de fond jouée une fois, en continu (pas par fusion)
        import numpy as np
        r = subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(music), "-t", f"{duration:.2f}", "-ac", "1",
                            "-ar", str(RATE), "-f", "f32le", "-"], capture_output=True)
        m = np.frombuffer(r.stdout, dtype=np.float32).copy()
        if len(m):
            m = m / (float(np.max(np.abs(m))) or 1.0)
            if len(m) < len(audio):                        # trop courte : on la boucle
                m = np.tile(m, len(audio) // len(m) + 1)
            m = m[:len(audio)]
            f = int(1.0 * RATE)
            m[-f:] *= np.linspace(1, 0, f)                 # fondu de fin
            audio = audio + m * float(fcfg().get("volume", 0.13)) * music_gain
    write_wav(wav, audio)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp_video), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp_video.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"title": title, "seed": seed, "seconds": round(duration, 1), "tiers": [t["name"] for t in tiers],
            "reached": tiers[sim.best]["name"], "complete": sim.best >= sim.top,
            "music": Path(music).name if music else None, "sound": ([Path(x).name for x in sound] if isinstance(sound, (list, tuple)) else
                      (Path(sound).name if sound else None)), "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    _brand_video(out)
    log.info("fusion : %s atteint en %.0f s → %s", meta["reached"], duration, out.name)
    return out


def listing() -> list[dict]:
    items = []
    vids = [p for pre in ("fusion", "race", "domain") for p in out_dir().glob(f"{pre}_*.mp4")]  # + Race, Domain War
    for p in sorted(vids, key=lambda p: p.stat().st_mtime, reverse=True):
        j = p.with_suffix(".json")
        meta = json.loads(j.read_text(encoding="utf-8")) if j.exists() else {}
        items.append({"file": p.name, **meta})
    return items


def _brand_video(out):
    """Filigrane anti-vol sur les NOUVELLES vidéos (depuis le 02/11 ; config `slides.render.video_watermark`)."""
    from . import render as _r
    if _r.rcfg().get("video_watermark", True):
        try:
            _r.stamp_video(out)
        except Exception as e:  # pas de badge, ffmpeg… : la vidéo reste sans filigrane
            log.info("filigrane vidéo : %s", e)
