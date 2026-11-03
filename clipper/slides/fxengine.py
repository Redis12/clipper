"""Moteur d'effets 2D du Domain War : particules, lueurs additives (bloom), caméra (zoom « punch »), flipbooks.

- `Particles` : étincelles (traits qui filent), braises (points lumineux qui montent), débris (qui retombent) ;
  numpy, dessinées en mode additif → elles brillent par-dessus tout.
- `bloom(img, energy)` : la couche d'énergie (rayons, explosions, particules) est ajoutée à l'image + une version
  floue et réduite (halo), comme les jeux.
- `Camera` : zoom bref vers un point (gros coup) + tremblement ; appliqué à toute l'image à la fin.
- `flipbook(path)` : animation image par image (GIF animé ou dossier d'images numérotées) → liste d'images.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

SPARK, EMBER, DEBRIS, SMOKE = 0, 1, 2, 3
GLOW = (SPARK, EMBER)                                   # particules lumineuses (additif) ; débris/fumée = normaux


class Particles:
    def __init__(self, seed: int = 0, cap: int = 2500):
        self.rnd = random.Random(seed)
        self.cap = cap
        self.p = np.zeros((0, 11), dtype=np.float32)   # x y vx vy age life size r g b kind

    def emit(self, x, y, n, speed=(200, 600), col=(255, 220, 120), life=(0.25, 0.6), size=(2, 5), kind=SPARK,
             spread=2 * math.pi, angle=0.0, vy0=0.0):
        n = int(n)
        if n <= 0:
            return
        r = self.rnd
        rows = []
        for _ in range(n):
            a = angle + r.uniform(-spread / 2, spread / 2)
            v = r.uniform(*speed)
            c = [min(255, max(0, ch + r.uniform(-25, 25))) for ch in col]
            rows.append([x, y, math.cos(a) * v, math.sin(a) * v + vy0, 0, r.uniform(*life), r.uniform(*size),
                         c[0], c[1], c[2], kind])
        self.p = np.vstack([self.p, np.array(rows, dtype=np.float32)])[-self.cap:]

    def step(self, dt: float) -> None:
        if not len(self.p):
            return
        p = self.p
        k = p[:, 10]
        p[:, 4] += dt
        drag = np.select([k == SPARK, k == EMBER, k == DEBRIS], [3.2, 1.2, 4.5], 2.5)   # vue de dessus : ça glisse
        p[:, 2] *= np.exp(-drag * dt)
        p[:, 3] *= np.exp(-drag * dt)
        p[:, 3] += np.select([k == EMBER, k == SMOKE, k == DEBRIS], [-140.0, -25.0, 0.0], 120.0) * dt  # montée
        p[:, 0] += p[:, 2] * dt
        p[:, 1] += p[:, 3] * dt
        self.p = p[p[:, 4] < p[:, 5]]

    def draw(self, layer: Image.Image, scale: float = 1.0, kinds=GLOW) -> None:
        """Dessine les particules des `kinds` donnés : lumineuses sur la couche d'énergie (additive),
        débris (éclats de roche qui tournent) et fumée (bouffées qui gonflent) sur une couche normale."""
        if not len(self.p):
            return
        d = ImageDraw.Draw(layer)
        for i, (x, y, vx, vy, age, life, size, r, g, b, kind) in enumerate(self.p):
            if kind not in kinds:
                continue
            q = 1 - age / life
            if kind == DEBRIS:                                 # éclat de roche : polygone qui tourne + reflet
                s = size * scale
                rot = (i * 1.7 + age * (8 + i % 5)) % 6.283
                pts = [(x + math.cos(rot + j * 2.1 + (i % 3) * 0.3) * s * (0.7 + 0.3 * ((i + j) % 2)),
                        y + math.sin(rot + j * 2.1 + (i % 3) * 0.3) * s * (0.7 + 0.3 * ((i + j) % 2))) for j in range(3)]
                al = int(255 * min(1.0, q * 3))
                d.polygon([(px + 2, py + 3) for px, py in pts], fill=(0, 0, 0, al // 3))     # ombre
                d.polygon(pts, fill=(int(r), int(g), int(b), al))
                d.line(pts[:2], fill=(min(255, int(r) + 70), min(255, int(g) + 70), min(255, int(b) + 70), al),
                       width=max(1, int(s / 4)))
                continue
            if kind == SMOKE:                                  # fumée : gonfle et s'efface
                s = size * scale * (1 + 2.2 * (1 - q))
                d.ellipse((x - s, y - s, x + s, y + s), fill=(int(r), int(g), int(b), int(110 * q ** 1.5)))
                continue
            col = (int(r), int(g), int(b), int(255 * min(1.0, q * 1.4)))
            s = size * scale * (0.4 + 0.6 * q)
            if kind == SPARK:                                  # trait dans le sens de la vitesse (flou de mouvement)
                L = 0.035
                d.line((x - vx * L, y - vy * L, x, y), fill=col, width=max(1, int(s)))
            else:
                d.ellipse((x - s, y - s, x + s, y + s), fill=col)


def add(img: Image.Image, layer: Image.Image, gain: float = 1.0) -> Image.Image:
    """Ajout additif d'une couche RGBA (couleur × alpha) sur l'image (seulement dans la zone utile)."""
    box = layer.getchannel("A").getbbox()
    if not box:
        return img
    a = np.asarray(layer.crop(box), dtype=np.float32)
    rgb = a[..., :3] * (a[..., 3:4] / 255.0) * gain
    base = np.asarray(img.crop(box).convert("RGB"), dtype=np.float32)
    out = Image.fromarray(np.clip(base + rgb, 0, 255).astype(np.uint8), "RGB").convert("RGBA")
    img = img.copy()
    img.paste(out, box[:2])
    return img


def bloom(img: Image.Image, energy: Image.Image, strength: float = 0.9, radius: float = 14) -> Image.Image:
    """Couche d'énergie collée normalement + son halo flou ajouté (lueur des jeux)."""
    box = energy.getchannel("A").getbbox()
    if not box:
        return img
    img = img.copy()
    img.alpha_composite(energy)
    w, h = energy.size
    small = energy.resize((max(1, w // 4), max(1, h // 4)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(radius / 4))
    glow = small.resize((w, h), Image.BILINEAR)
    return add(img, glow, strength)


class Camera:
    """Zoom « punch » vers un point + tremblement, appliqués à l'image finie."""

    def __init__(self):
        self.punches = []            # (t0, x, y, force, durée)

    def punch(self, t, x, y, force=0.06, dur=0.35):
        self.punches.append((t, x, y, force, dur))

    def apply(self, img: Image.Image, t: float, shake: float = 0.0, seed: int = 0, bg=(10, 10, 18)) -> Image.Image:
        z, cx, cy = 1.0, img.width / 2, img.height / 2
        live = [(t0, x, y, f, d) for t0, x, y, f, d in self.punches if 0 <= t - t0 < d]
        self.punches = [p for p in self.punches if t - p[0] < p[4]]
        if live:
            t0, x, y, f, d = max(live, key=lambda p: p[3] * (1 - (t - p[0]) / p[4]))
            a = (t - t0) / d
            z = 1 + f * (math.sin(min(1.0, a * 4) * math.pi / 2)) * (1 - a) ** 1.5
            cx, cy = x, y
        dx = dy = 0
        if shake > 0.5:
            rs = random.Random(seed)
            dx, dy = rs.uniform(-shake, shake), rs.uniform(-shake, shake)
        if z <= 1.001 and not (dx or dy):
            return img
        W, H = img.size
        if z > 1.001:
            cw, ch = W / z, H / z
            x0 = min(max(0, cx - cw / 2 - (cx - W / 2) * 0.5 / z), W - cw)   # vers le point, sans sortir de l'écran
            y0 = min(max(0, cy - ch / 2 - (cy - H / 2) * 0.5 / z), H - ch)
            img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
        if dx or dy:
            sh = Image.new("RGBA", (W, H), bg + (255,))
            sh.paste(img, (int(dx), int(dy)))
            img = sh
        return img


def flipbook(path: Path, max_frames: int = 60) -> list[Image.Image]:
    """Images d'une animation : GIF/WebP animé, ou dossier d'images (ordre des noms)."""
    path = Path(path)
    frames = []
    try:
        if path.is_dir():
            for p in sorted(x for x in path.iterdir() if x.suffix.lower() in (".png", ".webp", ".jpg", ".jpeg")):
                frames.append(Image.open(p).convert("RGBA"))
        elif path.suffix.lower() in (".mp4", ".webm", ".mov", ".mkv", ".avi"):   # vidéo : 24 i/s, 4 s max
            import subprocess
            import tempfile
            from ..util import require_bin
            with tempfile.TemporaryDirectory() as td:
                subprocess.run([require_bin("ffmpeg"), "-loglevel", "error", "-y", "-t", "4", "-i", str(path),
                                "-vf", "fps=24,scale='min(512,iw)':-2", f"{td}/%04d.png"], check=True)
                for p in sorted(Path(td).glob("*.png")):
                    frames.append(Image.open(p).convert("RGBA"))
        else:
            im = Image.open(path)
            for i in range(getattr(im, "n_frames", 1)):
                im.seek(i)
                frames.append(im.convert("RGBA"))
    except Exception:
        return []
    if len(frames) > max_frames:
        frames = [frames[int(i * len(frames) / max_frames)] for i in range(max_frames)]
    return frames


def vignette(W: int, H: int, strength: float = 0.55) -> Image.Image:
    """Assombrit les bords (cinématique)."""
    y, x = np.ogrid[:H, :W]
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    a = np.clip((d - 0.6) / 0.8, 0, 1) * 255 * strength
    v = np.zeros((H, W, 4), dtype=np.uint8)
    v[..., 3] = a.astype(np.uint8)
    return Image.fromarray(v, "RGBA")


def chroma(img: Image.Image, px: int) -> Image.Image:
    """Aberration chromatique (décalage rouge/bleu) pour les impacts énormes."""
    if px < 1:
        return img
    r, g, b, a = img.split()
    r = ImageChops.offset(r, px, 0)
    b = ImageChops.offset(b, -px, 0)
    return Image.merge("RGBA", (r, g, b, a))


# --------------------------------------------------------------------------- particules texturées (façon moteur de jeu)

PARTICLES_DIR = Path(__file__).resolve().parents[1] / "assets" / "particles"


class TexFX:
    """Particules texturées : textures Kenney « Particle Pack » (CC0, niveaux de gris) teintées, qui grossissent,
    tournent, s'étirent et s'effacent. Lumineuses (additif + halo) ou normales (fumée, terre).
    Une texture « chaude » : le cœur tire vers le blanc, les bords prennent la couleur."""

    def __init__(self, seed: int = 0, cap: int = 400):
        self.rnd = random.Random(seed)
        self.cap = cap
        self.items: list[dict] = []
        self._tex: dict = {}
        self._cache: dict = {}

    def texture(self, name: str) -> Image.Image | None:
        if name not in self._tex:
            p = PARTICLES_DIR / f"{name}.png"
            self._tex[name] = Image.open(p).convert("L") if p.exists() else None
        return self._tex[name]

    def tinted(self, name: str, col, hot: float) -> Image.Image | None:
        key = (name, tuple(int(c) for c in col), round(hot, 1))
        if key not in self._cache:
            L = self.texture(name)
            if L is None:
                self._cache[key] = None
            else:
                a = np.asarray(L, dtype=np.float32) / 255.0
                c = np.array(col, dtype=np.float32)
                w = np.clip(a ** 2 * hot, 0, 1)[..., None]       # cœur blanc
                rgb = c * (1 - w) + 255 * w
                self._cache[key] = Image.fromarray(np.dstack([rgb, a * 255]).astype(np.uint8), "RGBA")
        return self._cache[key]

    def spawn(self, name, x, y, size, life, col=(255, 255, 255), *, size1=None, vx=0.0, vy=0.0, rot=None, spin=0.0,
              stretch=1.0, alpha=1.0, hot=0.8, glow=True, delay=0.0, fade_in=0.08, drag=0.0, t=0.0):
        if len(self.items) >= self.cap:
            return
        self.items.append({"tex": name, "x": x, "y": y, "s0": size, "s1": size if size1 is None else size1,
                           "life": life, "age": -delay, "col": col, "vx": vx, "vy": vy,
                           "rot": self.rnd.uniform(0, 360) if rot is None else rot, "spin": spin,
                           "st": stretch, "al": alpha, "hot": hot, "glow": glow, "fin": fade_in, "drag": drag})

    def step(self, dt: float) -> None:
        keep = []
        for p in self.items:
            p["age"] += dt
            if p["age"] < p["life"]:
                if p["age"] > 0:
                    if p["drag"]:
                        f = math.exp(-p["drag"] * dt)
                        p["vx"] *= f
                        p["vy"] *= f
                    p["x"] += p["vx"] * dt
                    p["y"] += p["vy"] * dt
                    p["rot"] += p["spin"] * dt
                keep.append(p)
        self.items = keep

    def draw(self, layer: Image.Image, glow: bool = True) -> None:
        """Dessine les particules lumineuses (glow=True, sur la couche d'énergie) ou les autres (fumée, terre)."""
        for p in self.items:
            if p["age"] < 0 or p["glow"] != glow:
                continue
            q = p["age"] / p["life"]
            al = p["al"] * min(1.0, p["age"] / max(1e-3, p["fin"])) * (1 - q) ** 1.2
            if al < 0.02:
                continue
            size = p["s0"] + (p["s1"] - p["s0"]) * (1 - (1 - q) ** 2)
            w, h = max(2, int(size)), max(2, int(size * p["st"]))       # st > 1 : étiré (vertical avant rotation)
            qa = max(1, min(8, int(al * 8 + 0.5)))
            key = (p["tex"], tuple(int(c) for c in p["col"]), round(p["hot"], 1), w // 3, h // 3, int(p["rot"]) // 10 % 36, qa)
            im = self._cache.get(key)
            if im is None:
                base = self.tinted(p["tex"], p["col"], p["hot"])
                if base is None:
                    continue
                im = base.resize((max(2, w // 3 * 3), max(2, h // 3 * 3)), Image.BILINEAR)
                if qa < 8:
                    im.putalpha(im.getchannel("A").point(lambda v, z=qa / 8: int(v * z)))
                im = im.rotate(int(p["rot"]) // 10 * 10, expand=True, resample=Image.BILINEAR)
                if len(self._cache) > 6000:
                    self._cache.clear()
                self._cache[key] = im
            layer.alpha_composite(im, (int(p["x"] - im.width / 2), int(p["y"] - im.height / 2)))


def impact_frame(img: Image.Image, col=(255, 255, 255), invert: bool = False) -> Image.Image:
    """« Impact frame » d'anime : l'image devient une silhouette à 2 tons (noir + couleur), 1 ou 2 images."""
    g = img.convert("L")
    a = np.asarray(g).astype(np.float32)
    m = a > (110 if not invert else 140)
    if invert:
        m = ~m
    out = np.zeros((a.shape[0], a.shape[1], 3), dtype=np.uint8)
    out[m] = col
    return Image.fromarray(out, "RGB").convert("RGBA")


def ripple(img: Image.Image, x: float, y: float, r: float, amp: float, width: float) -> Image.Image:
    """Onde de choc : déformation radiale (les pixels sont poussés vers l'extérieur sur un anneau de rayon r)."""
    try:
        from scipy import ndimage
    except ImportError:
        return img
    x0, y0 = int(max(0, x - r - width * 2)), int(max(0, y - r - width * 2))
    x1, y1 = int(min(img.width, x + r + width * 2)), int(min(img.height, y + r + width * 2))
    if x1 - x0 < 4 or y1 - y0 < 4:
        return img
    reg = np.asarray(img.crop((x0, y0, x1, y1)).convert("RGB")).astype(np.float32)
    h, w = reg.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = xx - (x - x0), yy - (y - y0)
    d = np.sqrt(dx * dx + dy * dy) + 1e-6
    k = np.exp(-((d - r) / max(1.0, width)) ** 2) * amp
    sx, sy = xx - dx / d * k, yy - dy / d * k
    out = np.stack([ndimage.map_coordinates(reg[..., c], [sy, sx], order=1, mode="nearest") for c in range(3)], -1)
    im = img.copy()
    im.paste(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB"), (x0, y0))
    return im
