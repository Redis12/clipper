"""Vidéo « Which anime character wins? » : des persos-balles rebondissent dans une arène ronde.

Chaque perso est relié au bord de l'arène par plusieurs liens (ses « vies »). Quand une balle touche le lien d'un
autre perso, elle le lui vole : le lien change de couleur et se rattache à elle. Un perso sans lien est éliminé.
Le dernier en vie gagne (ou celui qui a le plus de liens à la fin du temps). Résultat imprévisible = les gens
commentent leur pronostic.

Rendu image par image avec Pillow, encodé par ffmpeg (H.264 9:16), petit son « pop » à chaque vol.
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

PALETTE = ["#ff3b3b", "#ff9f1c", "#ffd60a", "#7bd389", "#2ec4b6", "#3a86ff", "#8338ec", "#ff5dc8",
           "#e5e5e5", "#06d6a0", "#ef476f", "#4cc9f0", "#f72585", "#b5e48c", "#ffb703", "#a0c4ff"]


def bcfg() -> dict:
    return config.get()["slides"].get("battle", {})


def out_dir() -> Path:
    d = config.data_dir() / "battles"
    d.mkdir(parents=True, exist_ok=True)
    return d


@dataclass
class Ball:
    name: str
    color: tuple
    avatar: Image.Image
    x: float
    y: float
    vx: float
    vy: float
    alive: bool = True
    rad: float = 0.0
    out_at: float = -1.0
    flash: float = 0.0
    trail: list = field(default_factory=list)         # dernières positions (traînée lumineuse)


@dataclass
class Link:
    angle: float
    owner: int
    cool: float = 0.0
    flash: float = 0.0


@dataclass
class Sim:
    balls: list
    links: list
    cx: float
    cy: float
    R: float
    r: float
    t: float = 0.0
    max_s: float = 180.0
    v0: float = 1.0
    accel: float = 1.015
    vmax: float = 3.0
    rnd: random.Random = field(default_factory=random.Random)
    steal_boost: float = 1.03
    slow_until: float = 0.0
    link_cool: float = 0.35
    events: list = field(default_factory=list)        # temps des vols (pour le son)
    steals: list = field(default_factory=list)        # (t, x, y, voleur, victime) : effets visuels
    outs: list = field(default_factory=list)          # (t, perso, x, y) : éliminations


def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def avatar(path: str | None, size: int, color: tuple) -> Image.Image:
    """Portrait rond avec un anneau de couleur (recadrage centré sur le perso)."""
    if path and Path(path).exists():
        with Image.open(path) as src:
            src.load()
            im = src.convert("RGB")
        try:                                          # recadré sur la tête (comme Fusion / Domain War)
            from . import faces
            sq = faces.head_square(im, path).resize((size, size), Image.LANCZOS)
        except Exception:
            sq = render.smart_crop(im, size, size)
    else:
        sq = Image.new("RGB", (size, size), (60, 60, 70))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(sq, (0, 0), mask)
    ImageDraw.Draw(out).ellipse((1, 1, size - 2, size - 2), outline=color + (255,), width=max(4, size // 14))
    return out


def setup(fighters: list[dict], W: int, H: int, links_per: int, seed: int) -> Sim:
    rnd = random.Random(seed)
    n = len(fighters)
    cx, cy, R = W / 2, H * 0.56, W * 0.44
    r = max(40.0, min(78.0, R * math.pi / n * 0.5))
    speed = R * float(bcfg().get("speed", 0.38))
    balls, links = [], []
    off = rnd.random() * 2 * math.pi
    for i, f in enumerate(fighters):
        col = hex_rgb(PALETTE[i % len(PALETTE)])
        a = off + (i + 0.5) * 2 * math.pi / n
        d = rnd.uniform(0, 2 * math.pi)
        balls.append(Ball(f["name"], col, avatar(f.get("image_path"), int(r * 4), col),
                          cx + math.cos(a) * R * 0.62, cy + math.sin(a) * R * 0.62,
                          math.cos(d) * speed, math.sin(d) * speed))
        sector = 2 * math.pi / n
        for j in range(links_per):                    # liens répartis dans le secteur du perso
            links.append(Link(off + i * sector + sector * (0.12 + 0.76 * (j + 0.5) / links_per), i))
    sim = Sim(balls, links, cx, cy, R, r)
    sim.v0, sim.accel = speed, float(bcfg().get("accel", 1.015))
    sim.rnd = random.Random(seed + 1)
    sim.steal_boost = float(bcfg().get("steal_boost", 1.03))
    sim.link_cool = float(bcfg().get("link_cool", 0.35))
    sim.vmax = float(bcfg().get("max_speed_x", 14.0))
    return sim


def _seg_dist(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy or 1e-9
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    qx, qy = ax + t * dx - px, ay + t * dy - py
    return math.hypot(qx, qy)


def _accel(b: Ball, sim: Sim, factor: float | None = None) -> None:
    v = math.hypot(b.vx, b.vy) or 1e-9
    target = min(v * (factor or sim.accel), sim.v0 * sim.vmax)
    b.vx, b.vy = b.vx / v * target, b.vy / v * target


def step(sim: Sim, dt: float, boost: float = 1.0) -> None:
    alive = [b for b in sim.balls if b.alive]
    total = len(sim.links) or 1
    cnt0 = counts(sim)
    for k, b in enumerate(sim.balls):                 # plus on a de liens, plus on grossit (et plus on vole)
        # Croissance plus que proportionnelle : le gros attrape plus de liens qu'il n'en offre → effet boule de neige,
        # la partie se termine toujours (sinon les 2 derniers s'échangent leurs liens indéfiniment).
        b.rad = sim.r                                 # taille fixe

    if sim.slow_until and sim.t < sim.slow_until:    # démarrage lent (option durée minimum)
        boost *= 0.45 + 0.55 * sim.t / sim.slow_until
    for b in alive:
        b.x += b.vx * dt * boost
        b.y += b.vy * dt * boost
        dx, dy = b.x - sim.cx, b.y - sim.cy
        d = math.hypot(dx, dy) or 1e-9
        if d + b.rad > sim.R:                         # rebond sur le bord
            nx, ny = dx / d, dy / d
            dot = b.vx * nx + b.vy * ny
            if dot > 0:
                b.vx -= 2 * dot * nx
                b.vy -= 2 * dot * ny
                _accel(b, sim)                        # chaque rebond accélère un peu : la fin devient le chaos
            b.x, b.y = sim.cx + nx * (sim.R - b.rad), sim.cy + ny * (sim.R - b.rad)
    for i, a in enumerate(alive):                     # chocs entre balles (masses égales)
        for b in alive[i + 1:]:
            dx, dy = b.x - a.x, b.y - a.y
            d = math.hypot(dx, dy)
            if 0 < d < a.rad + b.rad:
                nx, ny = dx / d, dy / d
                p = (a.vx - b.vx) * nx + (a.vy - b.vy) * ny
                if p > 0:
                    a.vx -= p * nx
                    a.vy -= p * ny
                    b.vx += p * nx
                    b.vy += p * ny
                    _accel(a, sim)
                    _accel(b, sim)
                push = (a.rad + b.rad - d) / 2
                a.x -= nx * push
                a.y -= ny * push
                b.x += nx * push
                b.y += ny * push
    idx = {id(b): k for k, b in enumerate(sim.balls)}
    for L in sim.links:                               # vols de liens
        L.cool = max(0.0, L.cool - dt)
        L.flash = max(0.0, L.flash - dt)
        if L.cool > 0:
            continue
        o = sim.balls[L.owner]
        ax, ay = sim.cx + math.cos(L.angle) * sim.R, sim.cy + math.sin(L.angle) * sim.R
        # Le lien ne compte qu'à partir du bord de son perso : se cogner à une balle ne vole rien,
        # il faut traverser le trait lui-même.
        lx, ly = ax - o.x, ay - o.y
        ln = math.hypot(lx, ly) or 1e-9
        skip = min(ln * 0.9, o.rad * 1.6)
        sx, sy = o.x + lx / ln * skip, o.y + ly / ln * skip
        for b in alive:
            k = idx[id(b)]
            if k == L.owner:
                continue
            if _seg_dist(b.x, b.y, sx, sy, ax, ay) < b.rad * 0.92:
                victim = L.owner
                # Règle unique : toucher un trait = ce lien passe chez toi, l'autre le perd.
                victim = L.owner
                v = math.hypot(b.vx, b.vy) / (sim.v0 or 1)
                L.owner, L.cool, L.flash = k, sim.link_cool, min(0.25, sim.link_cool)
                cnt0[k] += 1
                cnt0[victim] -= 1
                _accel(b, sim, sim.steal_boost)      # voler donne de l'élan : le leader va plus vite, vole plus
                b.flash = 0.12
                sim.events.append(sim.t)
                sim.steals.append((sim.t, b.x, b.y, k, victim))
                break
    cnt = counts(sim)
    for k, b in enumerate(sim.balls):
        b.flash = max(0.0, b.flash - dt)
        if b.alive and cnt[k] == 0:
            b.alive, b.out_at = False, sim.t
            sim.outs.append((sim.t, k, b.x, b.y))
    sim.t += dt


def advance(sim: Sim, frame_dt: float, min_sub: int = 3) -> None:
    """Avance d'une image ; plus les balles vont vite, plus on découpe en sous-pas (pas de traversée)."""
    vmax = max((math.hypot(b.vx, b.vy) for b in sim.balls if b.alive), default=0)
    n = max(min_sub, int(math.ceil(vmax * frame_dt / (sim.r * 0.4))))
    for _ in range(n):
        step(sim, frame_dt / n)
    for b in sim.balls:                               # traînée : 7 dernières positions
        if b.alive:
            b.trail.append((b.x, b.y))
            del b.trail[:-7]
        else:
            b.trail.clear()


def counts(sim: Sim) -> list[int]:
    c = [0] * len(sim.balls)
    for L in sim.links:
        c[L.owner] += 1
    return c


_BG: dict = {}


def background(sim: Sim, W: int, H: int, title: str) -> Image.Image:
    """Fond fixe (couleur, bord pointillé, titre), dessiné une seule fois."""
    key = (W, H, title, round(sim.R))
    if key not in _BG:
        k = W / 1080
        bg = Image.new("RGBA", (W, H), (11, 13, 20, 255))
        d = ImageDraw.Draw(bg)
        for s in range(180):
            a0, a1 = s * 2 * math.pi / 180, (s + 0.55) * 2 * math.pi / 180
            d.line([(sim.cx + math.cos(a) * sim.R, sim.cy + math.sin(a) * sim.R) for a in (a0, a1)],
                   fill=(200, 205, 220, 200), width=max(2, int(4 * k)))
        tf = render.font(int(92 * k))
        y = int(H * 0.06)
        for line in render.wrap(title.upper(), tf, int(W * 0.86), d):
            d.text((W / 2, y), line, font=tf, anchor="ma", fill=(235, 238, 245), stroke_width=int(3 * k),
                   stroke_fill=(0, 0, 0))
            y += int(sum(tf.getmetrics()) * 1.05)
        _BG.clear()
        _BG[key] = bg
    return _BG[key]


def mix(c, a):
    """Couleur éclaircie vers le blanc (a = 0 : couleur, 1 : blanc)."""
    return tuple(int(v + (255 - v) * a) for v in c[:3])


def back_out(x: float) -> float:
    """Dépasse un peu puis revient (effet « pop »)."""
    x = min(1.0, max(0.0, x))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2


class BattleFX:
    """Effets visuels « satisfaisants » (demandé le 02/11) : étincelles + éclat à chaque vol de lien, explosion +
    onde de choc + secousse + « impact frame » à chaque élimination, traînées, aura du leader, arène néon à la
    couleur du leader, confettis et rayons à l'écran de victoire. Moteur partagé avec le Domain War (fxengine,
    pack pixel-art vfxpack s'il est là, sinon vfxgen)."""

    def __init__(self, W: int, H: int, seed: int, fps: int):
        from . import fxengine, vfxgen, vfxpack
        self.fe, self.vg, self.vp = fxengine, vfxgen, vfxpack
        self.W, self.H, self.fps, self.k = W, H, fps, W / 1080
        self.parts = fxengine.Particles(seed)
        self.tex = fxengine.TexFX(seed)
        self.cam = fxengine.Camera()
        self.anims: list = []                        # (t0, frames, x, y, taille, durée, ancre y)
        self.ripples: list = []                      # (t0, x, y)
        self.seen_steal = self.seen_out = 0
        self.stop, self.stop_col = 0, (255, 255, 255)
        self.shake_t = -9.0
        self.pack = vfxpack.available()
        self._fr: dict = {}

    def frames(self, kind: str, col) -> list:
        key = (kind, tuple(int(c) // 8 for c in col[:3]))
        if key not in self._fr:
            fr: list = []
            if self.pack and kind == "explosion":
                fr = list(self.vp.frames("explosion_dome", None, tuple(col[:3])))
            elif self.pack and kind == "hit":
                fr = list(self.vp.frames("punch_impact", None, tuple(col[:3])))
            if not fr:
                fr = list(self.vg.frames(kind, 256, tuple(col[:3])))
            self._fr[key] = fr
        return self._fr[key]

    def consume(self, sim: "Sim") -> None:
        """Déclenche les effets des vols / éliminations survenus depuis la dernière image."""
        k = self.k
        for t, x, y, kk, victim in sim.steals[self.seen_steal:]:
            c = sim.balls[kk].color
            self.parts.emit(x, y, 12, speed=(220 * k, 720 * k), col=mix(c, 0.45), life=(0.15, 0.4), size=(2 * k, 5 * k))
            self.tex.spawn("star_08", x, y, sim.r * 1.0, 0.22, c, size1=sim.r * 2.6, hot=1.0)
            self.tex.spawn("circle_05", x, y, sim.r * 0.8, 0.3, c, size1=sim.r * 2.8, hot=0.6)
        self.seen_steal = len(sim.steals)
        for t, kk, x, y in sim.outs[self.seen_out:]:
            c = sim.balls[kk].color
            fr = self.frames("explosion", mix(c, 0.2))
            ay = self.vp.anchor("explosion_dome")[1] if self.pack else 0.5
            self.anims.append((t, fr, x, y, sim.r * 7, 0.8, ay))
            self.anims.append((t, self.frames("ring", mix(c, 0.4)), x, y, sim.r * 9, 0.5, 0.5))
            self.parts.emit(x, y, 40, speed=(300 * k, 1100 * k), col=mix(c, 0.5), life=(0.2, 0.6), size=(2 * k, 6 * k))
            self.parts.emit(x, y, 16, speed=(120 * k, 420 * k), col=(110, 100, 95), life=(0.5, 1.0),
                            size=(4 * k, 9 * k), kind=self.fe.DEBRIS)
            self.tex.spawn("star_09", x, y, sim.r * 1.5, 0.25, mix(c, 0.5), size1=sim.r * 4.5, hot=0.6, alpha=0.8)
            self.ripples.append((t, x, y))
            self.cam.punch(t, x, y, 0.06, 0.45)
            self.shake_t = t
            alive = sum(1 for b in sim.balls if b.alive)
            if alive <= 3:                              # fin de partie : arrêt sur image + impact frames
                self.stop, self.stop_col = 4, mix(c, 0.2)
            else:                                       # début (éliminations rapprochées) : juste un mini-arrêt
                self.stop, self.stop_col = max(self.stop, 2), None
        self.seen_out = len(sim.outs)

    def step(self, dt: float) -> None:
        self.parts.step(dt)
        self.tex.step(dt)

    def energy(self, img: Image.Image, t: float) -> Image.Image:
        """Couche lumineuse (particules, éclats, explosions) + halo."""
        en = Image.new("RGBA", img.size, (0, 0, 0, 0))
        keep = []
        for a in self.anims:
            t0, fr, x, y, size, dur, ay = a
            q = (t - t0) / dur
            if q >= 1 or not fr:
                continue
            keep.append(a)
            if q < 0:
                continue
            f = fr[min(len(fr) - 1, int(q * len(fr)))]
            sc = size / max(f.width, f.height)
            w, h = max(2, int(f.width * sc)), max(2, int(f.height * sc))
            im = f.resize((w, h), Image.NEAREST if f.info.get("pixel") else Image.BILINEAR)
            en.alpha_composite(im, (int(x - w / 2), int(y - ay * h)))
        self.anims = keep
        self.parts.draw(en, 1.0)
        self.tex.draw(en, glow=True)
        return self.fe.bloom(img, en, 0.8)

    def ground(self, img: Image.Image) -> None:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        self.parts.draw(g, 1.0, kinds=(self.fe.DEBRIS, self.fe.SMOKE))
        self.tex.draw(g, glow=False)
        img.alpha_composite(g)

    def post(self, img: Image.Image, t: float, frame: int, cell: float) -> Image.Image:
        keep = []
        for t0, x, y in self.ripples:                 # onde de choc : l'image se déforme en anneau
            a = t - t0
            if a < 0.42:
                keep.append((t0, x, y))
                img = self.fe.ripple(img, x, y, cell * (1 + 22 * a), cell * 0.9 * (1 - a / 0.42), cell * 1.6)
        self.ripples = keep
        shake = 14 * self.k * max(0.0, 1 - (t - self.shake_t) / 0.35) if t >= self.shake_t else 0
        return self.cam.apply(img, t, shake, seed=frame)


def draw(sim: Sim, W: int, H: int, title: str, winner: int | None = None, win_t: float = 0.0,
         fx: BattleFX | None = None, intro: float | None = None) -> Image.Image:
    """Une image. `intro` (0→1) = accroche : les persos apparaissent un par un ; `fx` = effets (BattleFX)."""
    k = W / 1080
    img = background(sim, W, H, title).copy()
    c = counts(sim)
    alive_idx = [i for i, b in enumerate(sim.balls) if b.alive]
    lead = max(alive_idx, key=lambda i: (c[i], -i)) if alive_idx else 0
    lc = sim.balls[lead].color
    ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))   # arène néon à la couleur du leader
    rd = ImageDraw.Draw(ring)
    pulse = 0.75 + 0.25 * math.sin(sim.t * 4)
    rd.ellipse((sim.cx - sim.R, sim.cy - sim.R, sim.cx + sim.R, sim.cy + sim.R), outline=lc + (int(170 * pulse),),
               width=max(3, int(9 * k)))
    small = ring.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(5))
    img.alpha_composite(small.resize((W, H), Image.BILINEAR))
    img.alpha_composite(ring)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for L in sim.links:
        o = sim.balls[L.owner]
        ax, ay = sim.cx + math.cos(L.angle) * sim.R, sim.cy + math.sin(L.angle) * sim.R
        w = max(2, int((8 if L.flash > 0 else 3) * k))
        col = (255, 255, 255) if L.flash > 0.15 else o.color      # un lien volé claque en blanc puis prend la couleur
        d.line((o.x, o.y, ax, ay), fill=col + (255 if L.flash > 0 else 215,), width=w)
        d.ellipse((ax - 5 * k, ay - 5 * k, ax + 5 * k, ay + 5 * k), fill=o.color + (255,))   # point d'ancrage
    for b in sim.balls:                               # traînées lumineuses
        n = len(b.trail)
        for j, (tx, ty) in enumerate(b.trail[:-1]):
            q = (j + 1) / n
            rr = sim.r * (0.25 + 0.55 * q)
            d.ellipse((tx - rr, ty - rr, tx + rr, ty + rr), fill=b.color + (int(110 * q),))
    small = lay.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2))
    img.alpha_composite(small.resize((W, H), Image.BILINEAR))   # lueur des liens (calculée en petit : rapide)
    img.alpha_composite(lay)
    if fx is not None:
        fx.ground(img)
    nf = render.font_from(render.PLAIN_FONTS, int(30 * k))
    n_b = len(sim.balls)
    for kk, b in enumerate(sim.balls):
        sc = 1.0
        if intro is not None:                         # accroche : chacun apparaît en « pop », l'un après l'autre
            q = (intro - kk / max(1, n_b) * 0.6) / 0.25
            if q <= 0:
                continue
            sc = back_out(q)
        if not b.alive:
            fade = 1 - min(1.0, (sim.t - b.out_at) / 0.25)
            if fade <= 0:
                continue
            av = b.avatar.copy()
            av.putalpha(av.getchannel("A").point(lambda v, f=fade: int(v * f)))
            sc *= 1 + 0.6 * (1 - fade)
        else:
            av = b.avatar
        if b.flash > 0:                               # petit éclair blanc quand il vole un lien
            av = av.copy()
            ImageDraw.Draw(av).ellipse((0, 0, av.width - 1, av.height - 1), outline=(255, 255, 255, 255),
                                       width=max(3, av.width // 14))
            sc *= 1 + 0.12 * b.flash / 0.12
        size = max(8, int(2 * (b.rad or sim.r) * sc))
        if b.alive and kk == lead and intro is None and len(alive_idx) > 1:   # leader : halo pulsé + couronne
            hr = size * (0.75 + 0.06 * math.sin(sim.t * 10))
            g = Image.new("RGBA", (int(hr * 2.4), int(hr * 2.4)), (0, 0, 0, 0))
            ImageDraw.Draw(g).ellipse((hr * 0.2, hr * 0.2, hr * 2.2, hr * 2.2), fill=mix(b.color, 0.3) + (150,))
            g = g.filter(ImageFilter.GaussianBlur(hr * 0.25))
            img.alpha_composite(g, (int(b.x - g.width / 2), int(b.y - g.height / 2)))
        if av.width != size:
            av = av.resize((size, size), Image.BILINEAR)
        img.alpha_composite(av, (int(b.x - size / 2), int(b.y - size / 2)))
        if b.alive and kk == lead and intro is None and len(alive_idx) > 1:
            cw = size * 0.55                          # couronne dorée
            x0, y0 = b.x - cw / 2, b.y - size / 2 - cw * 0.55
            pts = [(x0, y0 + cw * 0.5), (x0, y0 + cw * 0.1), (x0 + cw * 0.25, y0 + cw * 0.32), (x0 + cw * 0.5, y0),
                   (x0 + cw * 0.75, y0 + cw * 0.32), (x0 + cw, y0 + cw * 0.1), (x0 + cw, y0 + cw * 0.5)]
            cd = ImageDraw.Draw(img)
            cd.polygon(pts, fill=(255, 205, 40), outline=(0, 0, 0))
        if b.alive and intro is None:
            ImageDraw.Draw(img).text((b.x, b.y + size / 2 + 4 * k), f"{b.name.split()[0]} · {c[kk]}", font=nf,
                                     anchor="mt", fill=b.color + (255,), stroke_width=3, stroke_fill=(0, 0, 0))
    if fx is not None:
        img = fx.energy(img, sim.t)
    dr = ImageDraw.Draw(img)
    alive = len(alive_idx)
    sf = render.font_from(render.PLAIN_FONTS, int(44 * k))
    if intro is not None:                             # accroche : « WHO WINS? » + appel au commentaire
        if intro > 0.35:
            q = min(1.0, (intro - 0.35) / 0.15)
            f2 = render.font(int(90 * k * (1 + 0.4 * (1 - q))))
            dr.text((W / 2, sim.cy + sim.R + 70 * k), "WHO WINS?", font=f2, anchor="mt", fill=(255, 214, 10),
                    stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            render.draw_rich(img, (W / 2, sim.cy + sim.R + 190 * k), "Comment your pick 👇",
                             render.font(int(48 * k)), (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
            render.like_follow(img, W / 2, sim.cy + sim.R + 270 * k, (intro - 0.35) / 0.3)
    elif alive == 2 and winner is None:               # les 2 derniers
        f2 = render.font(int(70 * k * (1 + 0.05 * math.sin(sim.t * 8))))
        dr.text((W / 2, sim.cy + sim.R + 60 * k), "FINAL DUEL", font=f2, anchor="mt",
                fill=(255, 70, 70), stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
    elif winner is None:
        dr.text((W / 2, sim.cy + sim.R + 60 * k), f"{alive} left", font=sf, anchor="mt", fill=(170, 175, 190))
    if winner is not None:                            # écran de victoire : rayons, pop, confettis
        a = min(1.0, win_t / 0.4)
        dim = Image.new("RGBA", (W, H), (0, 0, 0, int(190 * a)))
        img.alpha_composite(dim)
        b = sim.balls[winner]
        rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rr_ = ImageDraw.Draw(rays)
        size = int(W * 0.42 * back_out(win_t / 0.45))
        cxw, cyw = W / 2, H * 0.40 + W * 0.21
        for i in range(16):                           # rayons qui tournent derrière le gagnant
            an = i / 16 * 2 * math.pi + win_t * 0.7
            pts = [(cxw, cyw), (cxw + math.cos(an - 0.09) * W * 1.2, cyw + math.sin(an - 0.09) * W * 1.2),
                   (cxw + math.cos(an + 0.09) * W * 1.2, cyw + math.sin(an + 0.09) * W * 1.2)]
            rr_.polygon(pts, fill=b.color + (int(70 * a),))
        img.alpha_composite(rays)
        if fx is not None:
            img = fx.energy(img, sim.t)
        if size > 8:
            av = avatar_from(b, size)
            img.alpha_composite(av, (int(cxw - size / 2), int(cyw - size / 2)))
        dr = ImageDraw.Draw(img)
        q = min(1.0, win_t / 0.25)
        wf = render.font(int(120 * k * (1 + 0.5 * (1 - q))))
        dr.text((W / 2, H * 0.31), "WINNER", font=wf, anchor="mm", fill=b.color, stroke_width=int(5 * k),
                stroke_fill=(0, 0, 0))
        nf2 = render.font(int(80 * k))
        dr.text((W / 2, H * 0.40 + W * 0.42 + 30 * k), b.name.upper(), font=nf2, anchor="ma", fill=(255, 255, 255),
                stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
        nxt = "Who should fight next? Comment 👇"
        render.draw_rich(img, (W / 2, H * 0.40 + W * 0.42 + 140 * k), nxt, render.font(int(46 * k)),
                         (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
        cta = (render.rcfg().get("end_cta") or "").strip()
        if cta:                                       # « Follow @animelorehq for more 🔥 »
            cf = render.font(int(52 * k))
            render.draw_rich(img, (W / 2, H * 0.40 + W * 0.42 + 230 * k), cta, cf, render.rcfg()["accent_color"],
                             "ma", int(3 * k), (0, 0, 0))
    return img.convert("RGB")


def avatar_from(b: Ball, size: int) -> Image.Image:
    return b.avatar.resize((size, size), Image.LANCZOS)


def pop_wav(path: Path, events: list[float], duration: float, rate: int = 44100) -> None:
    """Ancienne piste son (un « pop » par vol). Gardée pour compatibilité ; `soundtrack` la remplace."""
    import numpy as np

    n = int(duration * rate) + rate
    audio = np.zeros(n, dtype=np.float32)
    t = np.arange(int(0.07 * rate)) / rate
    blip = (np.sin(2 * np.pi * 880 * t) * np.exp(-t * 55)).astype(np.float32)
    for e in events:
        i = int(e * rate)
        audio[i:i + len(blip)] += blip[: max(0, n - i)] * 0.35
    audio = np.clip(audio, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((audio * 32767).astype(np.int16).tobytes())


def _note(f: float, rate: int):
    """Petite note « marimba » (fondamentale + harmoniques, attaque nette, chute rapide)."""
    import numpy as np
    t = np.arange(int(0.16 * rate)) / rate
    env = np.exp(-t * 26) * np.minimum(1, t / 0.002)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 60) \
        + 0.15 * np.sin(2 * np.pi * f * 2 * t)
    return (x * env).astype(np.float32)


SCALE = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]                # pentatonique : toujours joli, monte en combo


def soundtrack(path: Path, steals: list[float], outs: list[float], hits: list[float], win_at: float,
               duration: float, names: list[str]) -> None:
    """Son « satisfaisant » : chaque vol = une note ; des vols rapprochés montent la gamme (combo) ; élimination =
    coup + explosion (vrais sons de la banque library/_sfx si présents, sinon retravaillés) ; gong à la victoire."""
    import numpy as np

    from . import domain, fusion
    rate = fusion.RATE
    n = int(duration * rate) + rate
    audio = np.zeros(n, dtype=np.float32)

    def put(t, x, g):
        i = int(t * rate)
        if 0 <= i < n and x is not None:
            seg = x[: n - i]
            audio[i:i + len(seg)] += seg * g
    try:
        from . import seo
        fr = {(seo.anime_of(nm) or ("",))[0].lower() for nm in names}
        franchise = fr.pop() if len(fr) == 1 else None
    except Exception:
        franchise = None

    def S(fam, seed=0):
        try:
            return domain.sfx(fam, mode="anime", seed=seed, franchise=franchise)
        except Exception:
            return None
    notes = {}
    last, combo = -9.0, 0
    for t in steals:
        combo = min(len(SCALE) - 1, combo + 1) if t - last < 0.45 else 0
        last = t
        f = 523.25 * 2 ** (SCALE[combo] / 12)
        if combo not in notes:
            notes[combo] = _note(f, rate)
        put(t, notes[combo], 0.32)
    ko, boom = S("hit", 1), S("bomb", 2)
    for t in outs:
        put(t, ko, 0.8)
        put(t + 0.04, boom, 0.7)
    for t in hits:                                       # accroche : choc
        put(t, S("hit", 3), 0.7)
    put(win_at, S("win"), 0.9)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    # 15/11 : l'utilisateur trouvait le son « trop haut » (−11 LUFS) → −9 dB (≈ −20 LUFS, comme les autres formats)
    fusion.write_wav(path, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.355)


def generate(fighters: list[dict], title: str = "Which anime character wins?", links_per: int | None = None,
             seed: int | None = None, out: Path | None = None) -> Path:
    """Simule et rend la vidéo. Rend le chemin du MP4."""
    c = bcfg()
    if len(fighters) < 2:
        raise ValueError("Il faut au moins 2 personnages")
    W, H = (int(v) for v in c.get("size", [1080, 1920]))
    fps = int(c.get("fps", 30))
    max_s = float(c.get("safety_seconds", 150))   # filet de sécurité invisible (jamais atteint en pratique)
    links_per = int(links_per or c.get("links_per", 8))
    seed = int(seed if seed is not None else random.randrange(1_000_000))
    sim = setup(fighters, W, H, links_per, seed)
    sim.max_s = max_s
    fx = BattleFX(W, H, seed, fps)
    out = out or out_dir() / f"battle_{seed}.mp4"
    tmp_video = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp_video)], stdin=subprocess.PIPE)
    sub = 3
    intro = int(fps * float(c.get("intro_seconds", 1.2)))
    winner, win_frames = None, int(fps * float(c.get("end_seconds", 1.5)))
    frame = 0
    pauses: list = []                                  # (temps simu, secondes de vidéo en plus) : coupes, arrêts
    intro_hits: list = []

    def write(im):
        nonlocal frame
        proc.stdin.write(im.tobytes())
        frame += 1

    def vt(t):                                         # temps simu → temps vidéo
        return (intro + cover_n) / fps + t + sum(dd for t0, dd in pauses if t0 <= t + 1e-6)
    cover_n = 3                                        # 1re image = couverture TikTok/YouTube : tous les persos visibles
    try:
        cov = draw(sim, W, H, title, fx=fx, intro=1.0)
        for _ in range(cover_n):
            write(cov.convert("RGB"))
        for f in range(intro):                        # accroche : les persos apparaissent un par un en « pop »
            a = (f + 1) / intro
            n_b = len(sim.balls)
            for kk, b in enumerate(sim.balls):        # éclat quand chacun apparaît
                q0 = kk / max(1, n_b) * 0.6
                if q0 <= a < q0 + 1 / intro + 1e-6:
                    fx.tex.spawn("star_09", b.x, b.y, sim.r, 0.25, mix(b.color, 0.3), size1=sim.r * 4, hot=1.0)
                    intro_hits.append((f + cover_n) / fps)
            fx.step(1 / fps)
            img = draw(sim, W, H, title, fx=fx, intro=a)
            write(fx.post(img.convert("RGBA"), sim.t, frame, sim.r).convert("RGB"))
        rnd = random.Random(seed + 7)
        duel_len = float(c.get("duel_seconds", 20)) + rnd.uniform(-3, 3)
        stall_len = float(c.get("stall_seconds", 15))
        min_len = float(c.get("min_seconds", 0))           # 0 = pas de durée minimum (60 = monétisation TikTok)
        if min_len:
            sim.slow_until = min(12.0, min_len * 0.2)      # démarrage lent : on gratte du temps au début
        last_alive, last_change, duel_start = len(fighters), 0.0, None

        def cut():                                    # flash blanc = le « cut » (comme les vidéos virales)
            for f in range(3):
                a = int(255 * (1 - f / 3))
                write(Image.new("RGB", (W, H), (a, a, a)))
            pauses.append((sim.t, 3 / fps))
        while True:
            advance(sim, 1 / fps, sub)
            fx.consume(sim)
            fx.step(1 / fps)
            img = fx.post(draw(sim, W, H, title, fx=fx).convert("RGBA"), sim.t, frame, sim.r).convert("RGB")
            write(img)
            if fx.stop:                               # élimination : arrêt sur image + 2 « impact frames »
                for j in range(fx.stop):
                    write((fx.fe.impact_frame(img.convert("RGBA"), fx.stop_col, invert=j == 1)
                           if j < 2 and fx.stop_col is not None else img.convert("RGBA")).convert("RGB"))
                pauses.append((sim.t, fx.stop / fps))
                fx.stop = 0
            alive = [k for k, b in enumerate(sim.balls) if b.alive]
            if len(alive) != last_alive:
                last_alive, last_change = len(alive), sim.t
            if len(alive) == 2 and duel_start is None:
                duel_start = sim.t
            if len(alive) <= 1:
                winner = alive[0]
                break
            long_duel = (duel_start is not None and sim.t - duel_start >= duel_len
                         and sim.t + intro / fps >= min_len - 3.6)   # option : vidéo d'au moins `min_seconds`
            stalled = sim.t - last_change >= stall_len
            if stalled and len(alive) > 2:            # 3+ qui tournent en rond : CUT → le plus faible est sorti
                cnt = counts(sim)
                weak = min(alive, key=lambda k: (cnt[k], k))
                lead = max(alive, key=lambda k: (cnt[k], -k))
                cut()
                for L in sim.links:
                    if L.owner == weak:
                        L.owner = lead
                b = sim.balls[weak]
                b.alive, b.out_at = False, sim.t
                sim.outs.append((sim.t, weak, b.x, b.y))
                last_alive, last_change = len(alive) - 1, sim.t
                if len(alive) - 1 == 2:
                    duel_start = sim.t
                continue
            if long_duel or stalled or sim.t >= max_s:
                cnt = counts(sim)
                winner = max(alive, key=lambda k: (cnt[k], -k))
                cut()
                for L in sim.links:                   # après le cut : il a tout raflé
                    L.owner, L.flash = winner, 0.0
                for k in alive:
                    if k != winner:
                        b = sim.balls[k]
                        b.alive, b.out_at = False, sim.t
                        sim.outs.append((sim.t, k, b.x, b.y))
                fx.consume(sim)
                fx.stop = 0
                for _ in range(int(fps * 0.6)):
                    sim.t += 1 / fps
                    fx.step(1 / fps)
                    write(fx.post(draw(sim, W, H, title, fx=fx).convert("RGBA"), sim.t, frame, sim.r).convert("RGB"))
                break
        win_at = frame / fps
        wb = sim.balls[winner]
        for f in range(win_frames):
            sim.t += 1 / fps
            if f % 3 == 0:                            # confettis à la couleur du gagnant (et dorés)
                for _ in range(2):
                    x0 = random.Random(f * 13 + _).uniform(0, W)
                    fx.parts.emit(x0, -10, 3, speed=(80 * fx.k, 260 * fx.k), col=random.choice([wb.color, (255, 214, 10),
                                  (255, 255, 255)]), life=(1.2, 2.2), size=(4 * fx.k, 8 * fx.k), kind=fx.fe.EMBER,
                                  angle=math.pi / 2, spread=0.8, vy0=300 * fx.k)
            if f == 0:
                fx.tex.spawn("star_09", W / 2, H * 0.40 + W * 0.21, W * 0.2, 0.5, (255, 250, 230), size1=W * 0.9, hot=1.0)
            fx.step(1 / fps)
            write(draw(sim, W, H, title, winner, f / fps, fx=fx))
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué pendant l'encodage de la vidéo")
    finally:
        if proc.poll() is None:
            proc.kill()
    duration = frame / fps
    wav = out.with_suffix(".wav")
    try:
        soundtrack(wav, [vt(e) for e in sim.events], [vt(t) for t, *_ in sim.outs], intro_hits, win_at, duration,
                   [f["name"] for f in fighters])
    except Exception as e:                             # pas de numpy / son illisible → l'ancien « pop »
        log.info("battle : son simple (%s)", e)
        pop_wav(wav, [vt(e) for e in sim.events], duration)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp_video), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp_video.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"title": title, "seed": seed, "winner": sim.balls[winner].name, "seconds": round(duration, 1),
            "fighters": [f["name"] for f in fighters], "kind": "battle", "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    _brand_video(out)
    log.info("battle : %s gagne (%.0f s) → %s", meta["winner"], duration, out.name)
    return out


def fighters_from_library(names: list[str]) -> list[dict]:
    """« Satoru Gojo » → une image de son dossier (la plus nette). Les noms inconnus sont ignorés."""
    from . import library
    rows = db.query("SELECT * FROM images WHERE character IS NOT NULL AND origin='library'")
    out = []
    for n in names:
        key = library.norm(n)
        cand = [r for r in rows if library.norm(r["character"]) == key and Path(r["path"]).exists()]
        if cand:
            best = max(cand, key=lambda r: r["sharp"] or 0)
            out.append({"name": best["character"], "image_path": best["path"]})
    return out


def listing() -> list[dict]:
    items = []
    for p in sorted(out_dir().glob("battle_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        j = p.with_suffix(".json")
        meta = json.loads(j.read_text(encoding="utf-8")) if j.exists() else {}
        items.append({"file": p.name, **meta})
    return items


def roster() -> list[dict]:
    """Persos disponibles (un par dossier de la bibliothèque), avec l'id de leur image la plus nette."""
    best: dict = {}
    for r in db.query("SELECT * FROM images WHERE character IS NOT NULL AND origin='library'"):
        if not Path(r["path"]).exists():
            continue
        key = (r["anime"], r["character"])
        if key not in best or (r["sharp"] or 0) > (best[key]["sharp"] or 0):
            best[key] = r
    return sorted(({"anime": a, "name": c, "image_id": r["id"]} for (a, c), r in best.items()),
                  key=lambda x: (x["anime"].lower(), x["name"].lower()))


def _brand_video(out):
    """Filigrane anti-vol sur les NOUVELLES vidéos (depuis le 02/11 ; config `slides.render.video_watermark`)."""
    from . import render as _r
    if _r.rcfg().get("video_watermark", True):
        try:
            _r.stamp_video(out)
        except Exception as e:  # pas de badge, ffmpeg… : la vidéo reste sans filigrane
            log.info("filigrane vidéo : %s", e)
