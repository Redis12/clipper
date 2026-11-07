"""Effets du moteur stickman, tirés de l'analyse des vidéos de référence (ANALYSE_STICKMAN.md, 07/11).
Toutes les fonctions dessinent sur une image RGBA (canvas) en place, ou renvoient une nouvelle image.
"""
import math
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter


def _layer(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


# ---------------------------------------------------------------- mouvements rapides
def color_streaks(canvas, y0, y1, col, n=26, seed=0, t=0.0, alpha=150, blur=3, x0=0, x1=None, dirx=1):
    """Traits de vitesse À LA COULEUR DU PERSO (fan 15.6 s, SvS 1:30)."""
    W = canvas.width
    x1 = W if x1 is None else x1
    r = random.Random(seed + int(t * 60))
    L = _layer(canvas.size)
    d = ImageDraw.Draw(L)
    for _ in range(n):
        y = r.uniform(y0, y1)
        a = r.uniform(x0, x1)
        ln = r.uniform(120, 520)
        w = r.randint(3, 9)
        d.line((a, y, a - dirx * ln, y), fill=col + (int(alpha * r.uniform(0.5, 1)),), width=w)
    if blur:
        L = L.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(L)


def bg_speed_lines(canvas, t, col=(255, 255, 255), n=18, alpha=120, angle=0.0, seed=1):
    """Lignes de vitesse du décor (gris/blanc), éventuellement penchées."""
    W, H = canvas.size
    r = random.Random(seed + int(t * 48))
    L = _layer((W * 2, H * 2))
    d = ImageDraw.Draw(L)
    for _ in range(n):
        y = r.uniform(0, H * 2)
        x = r.uniform(0, W * 2)
        d.line((x, y, x + r.uniform(300, 900), y), fill=col + (alpha,), width=r.randint(2, 6))
    L = L.rotate(angle, resample=Image.BICUBIC).crop((W // 2, H // 2, W // 2 + W, H // 2 + H))
    canvas.alpha_composite(L.filter(ImageFilter.GaussianBlur(1.5)))


def arc_smear(canvas, pts, col, width=60, alpha=200, blur=2):
    """Croissant derrière un membre rapide (fan 8.4 s) : pts = positions récentes du poing/pied (ancien → récent)."""
    if len(pts) < 3:
        return
    L = _layer(canvas.size)
    d = ImageDraw.Draw(L)
    n = len(pts)
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        j = min(n - 1, i + 1)
        k = max(0, i - 1)
        dx, dy = pts[j][0] - pts[k][0], pts[j][1] - pts[k][1]
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        w = width * (i / (n - 1)) ** 1.2 / 2
        left.append((x + nx * w, y + ny * w))
        right.append((x - nx * w, y - ny * w))
    d.polygon(left + right[::-1], fill=col + (alpha,))
    if blur:
        L = L.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(L)


# ---------------------------------------------------------------- impacts
def impact_star(canvas, x, y, size, c_out=(255, 120, 40), c_in=(255, 235, 120), spikes=11, seed=0, rot=0.0, alpha=255):
    """Étoile d'impact à pointes irrégulières (SvS 1:03) + petits traits radiaux."""
    r = random.Random(seed)
    L = _layer(canvas.size)
    d = ImageDraw.Draw(L)
    for scale, col in ((1.0, c_out), (0.55, c_in), (0.22, (255, 255, 255))):
        pts = []
        for i in range(spikes * 2):
            a = rot + math.pi * i / spikes
            k = (1.0 if i % 2 == 0 else 0.38) * r.uniform(0.75, 1.15)
            pts.append((x + math.cos(a) * size * scale * k, y + math.sin(a) * size * scale * k))
        d.polygon(pts, fill=col + (alpha,))
    for i in range(8):
        a = r.uniform(0, math.tau)
        r1, r2 = size * r.uniform(1.1, 1.4), size * r.uniform(1.6, 2.2)
        d.line((x + math.cos(a) * r1, y + math.sin(a) * r1, x + math.cos(a) * r2, y + math.sin(a) * r2),
               fill=c_out + (alpha,), width=max(3, int(size / 22)))
    canvas.alpha_composite(L)


def manga_lines(canvas, cx, cy, col=(0, 0, 0), n=90, inner=180, alpha=255, seed=0, bg=None):
    """Lignes radiales façon manga (SvS 0:55, 1:25). bg = couleur de fond plein (sinon par-dessus l'image)."""
    W, H = canvas.size
    r = random.Random(seed)
    L = Image.new("RGBA", canvas.size, bg + (255,) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    R = math.hypot(W, H)
    for _ in range(n):
        a = r.uniform(0, math.tau)
        w = r.uniform(0.004, 0.02)
        ri = inner * r.uniform(0.7, 1.6)
        d.polygon([(cx + math.cos(a) * ri, cy + math.sin(a) * ri), (cx + math.cos(a - w) * R, cy + math.sin(a - w) * R),
                   (cx + math.cos(a + w) * R, cy + math.sin(a + w) * R)], fill=col + (alpha,))
    canvas.alpha_composite(L)


def tint_flash(canvas, col, alpha):
    """Écran teinté 1–2 images (SvS 3:42)."""
    if alpha > 0:
        canvas.alpha_composite(Image.new("RGBA", canvas.size, col + (int(alpha),)))


def silhouette_frame(canvas, mask, bg=(0, 0, 0), fg=(255, 255, 255)):
    """Impact frame : fond uni, persos en silhouette (SvS 1:40). mask = alpha des persos (L)."""
    out = Image.new("RGBA", canvas.size, bg + (255,))
    out.paste(fg + (255,), (0, 0), mask)
    canvas.paste(out, (0, 0))


def shock_rings(canvas, x, y, k, col=(90, 90, 100), n=3, rx=420, flat=0.32, width=14, alpha=170):
    """Anneaux de choc qui s'étalent en perspective (SvS 0:54, 1:25)."""
    L = _layer(canvas.size)
    d = ImageDraw.Draw(L)
    for j in range(n):
        q = k - j * 0.12
        if q <= 0:
            continue
        r = rx * (0.2 + q)
        a = int(alpha * max(0.0, 1 - q))
        d.ellipse((x - r, y - r * flat, x + r, y + r * flat), outline=col + (a,), width=max(2, min(int(r * flat * 0.4), int(width * (1 - q)))))
    canvas.alpha_composite(L.filter(ImageFilter.GaussianBlur(1.5)))


class Rubble:
    """Débris noirs qui sautent du sol (SvS 1:52, 2:18) + poussière grise qui roule (SvS 2:26)."""

    def __init__(self, seed=0):
        self.r = random.Random(seed)
        self.rocks, self.dust = [], []

    def burst(self, x, y, t, n=14, power=900, col=(30, 30, 34)):
        for _ in range(n):
            self.rocks.append([x + self.r.uniform(-40, 40), y, self.r.uniform(-power * .5, power * .5),
                               -self.r.uniform(power * .4, power), t, self.r.uniform(6, 16), col, y])

    def puff(self, x, y, t, n=3, size=(30, 60), col=(200, 195, 190), vx=0.0):
        for _ in range(n):
            self.dust.append([x + self.r.uniform(-30, 30), y, self.r.uniform(*size), t, col, vx])

    def draw(self, canvas, t, grav=2200):
        d = ImageDraw.Draw(canvas, "RGBA")
        keep = []
        for rk in self.rocks:
            a = t - rk[4]
            x, y = rk[0] + rk[2] * a, rk[1] + rk[3] * a + 0.5 * grav * a * a
            if y <= rk[7] + 2 and a < 2:
                s = rk[5]
                d.polygon([(x - s, y), (x - s * .2, y - s), (x + s, y - s * .3), (x + s * .5, y + s * .6)], fill=rk[6])
                keep.append(rk)
        self.rocks = keep
        keep = []
        for p in self.dust:
            a = t - p[3]
            if a < 0.9:
                r = p[2] * (1 + a * 1.6)
                x = p[0] + p[5] * a
                d.ellipse((x - r, p[1] - r * 0.55 - a * 40, x + r, p[1] + r * 0.55 - a * 40),
                          fill=p[4] + (int(150 * (1 - a / 0.9)),))
                keep.append(p)
        self.dust = keep


# ---------------------------------------------------------------- charge / transformation (gaara 3:24)
def power_column(canvas, x, ground, k, col=(170, 220, 255), t=0.0, width=240, height=1400, seed=3):
    """Colonne de lumière verticale + traits qui montent."""
    if k <= 0:
        return
    L = _layer(canvas.size)
    d = ImageDraw.Draw(L)
    w = width * (0.6 + 0.4 * k)
    d.rectangle((x - w / 2, ground - height, x + w / 2, ground), fill=col + (int(70 * k),))
    r = random.Random(seed + int(t * 30))
    for _ in range(int(14 * k)):
        xx = x + r.uniform(-w * .6, w * .6)
        y = ground - r.uniform(0, height)
        d.line((xx, y, xx, y - r.uniform(80, 260)), fill=(255, 255, 255, int(200 * k)), width=r.randint(2, 5))
    canvas.alpha_composite(L.filter(ImageFilter.GaussianBlur(2)))


def swirl_arcs(canvas, x, y, k, t, col=(120, 200, 255), rx=230, ry=420, n=3):
    """Arcs d'énergie qui tournent autour du perso."""
    if k <= 0:
        return
    L = _layer(canvas.size)
    d = ImageDraw.Draw(L)
    for j in range(n):
        ph = t * 5 + j * math.tau / n
        a0 = math.degrees(ph) % 360
        d.arc((x - rx, y - ry, x + rx, y + ry * 0.3), a0, a0 + 110, fill=col + (int(230 * k),), width=12)
    canvas.alpha_composite(L.filter(ImageFilter.GaussianBlur(3)))
    canvas.alpha_composite(L)


def rim_glow(sprite, col, size=10, strength=1.0):
    """Liseré lumineux autour d'un sprite RGBA (gaara 3:25) → image à coller DERRIÈRE le sprite."""
    a = sprite.getchannel("A").filter(ImageFilter.MaxFilter(size | 1))
    a = a.filter(ImageFilter.GaussianBlur(size * 0.6)).point(lambda v: min(255, int(v * 1.6 * strength)))
    g = Image.new("RGBA", sprite.size, col + (0,))
    g.putalpha(a)
    return g


# ---------------------------------------------------------------- caméra
def camera(img, zoom=1.0, cx=None, cy=None, tilt=0.0, shake=0.0, rnd=None):
    """Zoom vers (cx, cy) + horizon penché + tremblement. img RGB/RGBA → même taille, sans coins noirs."""
    W, H = img.size
    cx = W / 2 if cx is None else cx
    cy = H / 2 if cy is None else cy
    if shake and rnd is not None:
        cx += rnd.uniform(-shake, shake) / max(zoom, 1)
        cy += rnd.uniform(-shake, shake) / max(zoom, 1)
    if zoom == 1 and not tilt and not shake:
        return img
    a = math.radians(abs(tilt))
    marg = math.cos(a) + math.sin(a) * max(W / H, H / W)            # agrandissement pour couvrir les coins
    z = max(zoom, 1.0) * marg * (1.02 if shake else 1.0)
    w, h = W / z, H / z
    x0 = min(max(0, cx - w / 2), W - w)
    y0 = min(max(0, cy - h / 2), H - h)
    if not tilt:
        return img.crop((int(x0), int(y0), int(x0 + w), int(y0 + h))).resize((W, H), Image.BICUBIC)
    # on prend une zone plus grande (taille finale × marg), on la tourne, puis on recadre au centre
    W2, H2 = int(W * marg) + 2, int(H * marg) + 2
    w2, h2 = w * marg, h * marg
    x0 = min(max(0, cx - w2 / 2), W - w2)
    y0 = min(max(0, cy - h2 / 2), H - h2)
    big = img.crop((int(x0), int(y0), int(x0 + w2), int(y0 + h2))).resize((W2, H2), Image.BICUBIC)
    big = big.rotate(tilt, resample=Image.BICUBIC)
    l, t_ = (W2 - W) // 2, (H2 - H) // 2
    return big.crop((l, t_, l + W, t_ + H))
