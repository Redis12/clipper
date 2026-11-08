"""Change le perso d'un mouvement découpé (library/_mocap/clips) : recoloration de la palette du Goku Pivot.
    frames = reskin.saitama(frames)      # chauve, combinaison jaune, gants/bottes rouges, ceinture noire
Couleurs du Goku : gi orange (232,72,24)/(224,64,16), bleu nuit (0,24,64) poignets/bottes/ceinture/col,
cheveux (24,24,24), peau (248,216,184), liseré des bottes jaune-vert, emblème noir/blanc sur la poitrine."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi


def _masks(a):
    r, g, b, al = [a[..., i].astype(int) for i in range(4)]
    vis = al > 20
    mx, mn = np.maximum(np.maximum(r, g), b), np.minimum(np.minimum(r, g), b)
    orange = vis & (r > 150) & (g < 140) & (b < 90) & (r - g > 90)
    navy = vis & (b > r + 25) & (b > 45) & (b > g + 20) & (b < 150) & (r < 90)
    dark = vis & (mx < 70) & ~navy
    skin = vis & (r > 200) & (g > 170) & (b > 130) & (r - b < 110) & (r - b > 30)
    white = vis & (mn > 200) & (mx - mn < 30)
    lime = vis & (r > 170) & (g > 170) & (b < 140) & ~skin
    red = vis & (r > 150) & (g < 80) & (b < 80) & ~orange
    return vis, orange, navy, dark, skin, white, lime, red


def _shade(base, a, ref):
    """garde l'ombrage : luminosité relative à la couleur de référence."""
    lum = a[..., :3].astype(float).mean(-1) / (sum(ref) / 3)
    return np.clip(np.array(base, float)[None, None] * np.clip(lum, 0.7, 1.25)[..., None], 0, 255)


def saitama_frame(im, head_r=None):
    a = np.array(im.convert("RGBA"))
    vis, orange, navy, dark, skin, white, lime, red = _masks(a)
    H, W = vis.shape
    out = a.astype(float).copy()
    # cheveux = gros bloc sombre + mèches fines autour (pas l'emblème) ; on les enlève
    lab, n = ndi.label(dark)
    hair = np.zeros_like(dark)
    if n:
        sizes = ndi.sum(dark, lab, range(1, n + 1))
        big = int(np.argmax(sizes)) + 1
        core = lab == big
        zone = ndi.binary_dilation(core, iterations=max(12, int((head_r or 30) * 1.3)))
        hair = (zone & ~(orange | navy | skin) & ~ndi.binary_fill_holes(orange | navy)) | core
            # emblème : tout ce qui est entouré par le gi → jaune
    emblem = ndi.binary_fill_holes(orange | navy) & ~orange & ~navy & vis
    # tête : rayon fixe ; centre = visage visible décalé vers les cheveux
    head = None
    sk_lab, sn = ndi.label(skin)
    if hair.any() and sn:
        near = ndi.binary_dilation(hair, iterations=4)
        cand = [i for i in range(1, sn + 1) if (near & (sk_lab == i)).any()]
        if cand:
            face = np.isin(sk_lab, cand)
            ys, xs = np.nonzero(face)
            hy, hx = np.nonzero(core)
            r = head_r or 30.0
            fy, fx = ys.mean(), xs.mean()
            vy, vx = hy.mean() - fy, hx.mean() - fx
            L = max(1e-6, (vy * vy + vx * vx) ** 0.5)
            k = min(L, 0.45 * r)
            head = (fx + vx / L * k, fy + vy / L * k, r)
            yy, xx = np.mgrid[:H, :W]
            dd = np.hypot(xx - head[0], yy - head[1])
            hair |= face & (dd > r * 0.98) & (dd < r * 1.7)               # le bout de visage du Goku qui dépasse
    gi = (250, 214, 52)
    out[..., :3][orange] = _shade(gi, a, (228, 68, 20))[orange]
    out[emblem] = np.array(gi + (255,), float) * [0.97, 0.97, 0.97, 1]
    # bleu nuit : ceinture (près du gi, horizontale au milieu) noire, le reste rouge (gants, bottes)
    nl, nn = ndi.label(navy)
    for i in range(1, nn + 1):
        m = nl == i
        ys, xs = np.nonzero(m)
        touch_gi = (ndi.binary_dilation(m, iterations=3) & orange).sum()
        low = ys.mean() > H * 0.72
        col = (235, 40, 40) if (low or touch_gi < 0.6 * m.sum()) else (25, 25, 28)
        out[..., :3][m] = _shade(col, a, (2, 26, 62))[m] if col[0] > 100 else np.array(col, float)
    out[lime | (red & ~emblem)] = (235, 40, 40, 255)
    out[hair, 3] = 0
    img = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    if head:
        cx, cy, r = head
        hd = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(hd)
        d.ellipse((cx - r, cy - r * 1.05, cx + r, cy + r * 1.05), fill=(250, 216, 186, 255))
        d.ellipse((cx - r * 0.55, cy - r * 0.85, cx - r * 0.05, cy - r * 0.45), fill=(255, 236, 214, 255))   # reflet du crâne
        hd = hd.filter(ImageFilter.GaussianBlur(0.8))
        base = img.copy()
        img = Image.alpha_composite(hd, base)          # la tête derrière le corps (le col passe devant)
    return img


def saitama(frames, head_r=None):
    return [saitama_frame(f, head_r) for f in frames]
