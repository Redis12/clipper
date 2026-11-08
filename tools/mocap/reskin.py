"""Change le perso d'un mouvement découpé (library/_mocap/clips, Goku Pivot) : idée de l'utilisateur (08/11) = garder
le corps (« green screen » du Goku), enlever la tête/les cheveux et dessiner la tête du nouveau perso.
    frames = reskin.saitama(frames, head_r=0.062 * hauteur)
Palette du Goku : gi orange (232,72,24)/(224,64,16), bleu nuit (0,24,64) poignets/bottes/ceinture/col, cheveux
(24,24,24), peau (248,216,184), liseré des bottes jaune-vert, emblème noir/blanc. Palette de Saitama prise dans le
pack Stick Nodes de l'utilisateur (library/_sticknodes/Saitama/Saitama-OPM) : combinaison (244,234,0)/(220,211,0),
gants/bottes (220,0,3), cape (244,244,244), peau (255,201,155), ceinture (216,204,101)."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

SAITAMA = {"suit": (244, 234, 0), "suit_dark": (220, 211, 0), "red": (220, 0, 3), "cape": (244, 244, 244),
           "skin": (255, 201, 155), "belt": (216, 204, 101)}


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


def head_of(a, r):
    """(cx, cy, sens, cou) : tête du Goku = plus grand cercle inscrit dans les cheveux (+ visage), un peu vers le
    visage ; sens = +1 s'il regarde à droite ; cou = point du gi le plus proche (attache de la cape)."""
    vis, orange, navy, dark, skin, *_ = _masks(a)
    lab, n = ndi.label(dark)
    if not n:
        return None
    core = lab == (int(np.argmax(ndi.sum(dark, lab, range(1, n + 1)))) + 1)
    ys, xs = np.nonzero(core)
    reg = np.zeros_like(core)
    reg[max(0, ys.min() - 40):ys.max() + 40, max(0, xs.min() - 10):xs.max() + 10] = True
    dt = ndi.distance_transform_edt(core | (skin & reg))
    cy, cx = np.unravel_index(int(np.argmax(dt)), dt.shape)
    face = skin & ndi.binary_dilation(core, iterations=6)
    side = 0.0
    if face.sum() > 20:
        fy, fx = [v.mean() for v in np.nonzero(face)]
        vy, vx = fy - cy, fx - cx
        L = max(1e-6, np.hypot(vy, vx))
        k = min(L, 0.35 * r)
        cy, cx = cy + vy / L * k, cx + vx / L * k
        side = fx - xs.mean()
    oy, ox = np.nonzero(orange | navy)
    neck = None
    below = oy > cy + 0.3 * r                       # le cou est sous la tête (sauf salto : alors n'importe où)
    if below.sum() > 50:
        oy, ox = oy[below], ox[below]
    if len(oy):
        j = int(np.argmin((oy - cy) ** 2 + (ox - cx) ** 2))
        neck = (float(ox[j]), float(oy[j]))
        dn = np.hypot(neck[0] - cx, neck[1] - cy)
        if dn > 1.15 * r:                           # la tête reste posée sur le cou
            t = (dn - 1.15 * r) / dn
            cx, cy = cx + (neck[0] - cx) * t, cy + (neck[1] - cy) * t
    return float(cx), float(cy), (1 if side >= 0 else -1), neck, core, face


def _shade(base, a, ref):
    lum = a[..., :3].astype(float).mean(-1) / (sum(ref) / 3)
    return np.clip(np.array(base, float)[None, None] * np.clip(lum, 0.75, 1.2)[..., None], 0, 255)


def saitama_frame(im, head_r=31.0, cape=True, cape_phase=0.0, P=SAITAMA):
    a = np.array(im.convert("RGBA"))
    vis, orange, navy, dark, skin, white, lime, red = _masks(a)
    H, W = vis.shape
    r = float(head_r)
    out = a.astype(float).copy()
    hd = head_of(a, r)
    gi_area = ndi.binary_fill_holes(orange | navy)
    remove = np.zeros_like(vis)
    if hd:
        cx, cy, side, neck, core, face = hd
        zone = ndi.binary_dilation(core, iterations=max(12, int(r * 1.3)))
        remove = (zone & ~(orange | navy | skin) & ~gi_area) | core
        yy, xx = np.mgrid[:H, :W]
        dd = np.hypot(xx - cx, yy - cy)
        sk_lab, sn = ndi.label(skin)
        touch = set(np.unique(sk_lab[face])) - {0}
        facecomp = np.isin(sk_lab, list(touch)) & (dd < r * 2.0)
        remove |= facecomp & (dd > r * 0.98)
    emblem = gi_area & ~orange & ~navy & vis
    # gi : clair → combinaison, foncé (jambe/bras arrière) → jaune foncé
    lum = a[..., 0].astype(int)
    light = orange & (lum >= 228)
    out[..., :3][light] = _shade(P["suit"], a, (232, 72, 24))[light]
    darkgi = orange & ~light
    out[..., :3][darkgi] = _shade(P["suit_dark"], a, (224, 64, 16))[darkgi]
    out[..., :3][emblem] = P["suit"]
    # bleu nuit : ceinture (touche le gi des deux côtés, au milieu) → ceinture, le reste (poignets, bottes, col) → rouge
    nl, nn = ndi.label(navy)
    for i in range(1, nn + 1):
        m = nl == i
        ys, xs = np.nonzero(m)
        ring = ndi.binary_dilation(m, iterations=3) & ~m
        frac_gi = (ring & orange).sum() / max(1, ring.sum())
        low = ys.mean() > H * 0.7
        if not low and frac_gi > 0.55 and (xs.max() - xs.min()) > 0.8 * r:
            out[..., :3][m] = P["belt"]
        else:
            out[..., :3][m] = _shade(P["red"], a, (2, 26, 62))[m]
    out[..., :3][(lime | red) & ~emblem] = P["red"]
    # peau : bras (touchent le gi) → manches jaunes, mains (touchent seulement un poignet) → gants rouges
    sk_lab, sn = ndi.label(skin & ~remove)
    face_ids = set()
    if hd:
        face_ids = set(np.unique(sk_lab[ndi.binary_dilation(hd[4], iterations=6)])) - {0}
    for i in range(1, sn + 1):
        if i in face_ids:
            continue
        m = sk_lab == i
        ring = ndi.binary_dilation(m, iterations=3) & ~m
        if (ring & orange).sum() > 4 or m.sum() > 1.3 * r * r:
            out[..., :3][m] = P["suit"]
        elif (ring & navy).sum() > 2:
            out[..., :3][m] = P["red"]
    for i in face_ids:
        out[..., :3][sk_lab == i] = P["skin"]
    out[remove, 3] = 0
    body = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    if not hd:
        return body
    cx, cy, side, neck, *_ = hd
    back = Image.new("RGBA", body.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(back)
    if cape and neck:
        nx, ny = neck
        bx = -side                                                   # la cape part derrière
        sway = np.sin(cape_phase) * 0.25 * r
        top = [(nx - 0.8 * r, ny - 0.1 * r), (nx + 0.8 * r, ny - 0.1 * r)]
        bot_y = ny + 3.4 * r
        bot_c = nx + bx * (1.1 * r) + sway
        poly = [top[0], top[1], (bot_c + 1.15 * r, bot_y), (bot_c + 0.4 * r, bot_y + 0.25 * r),
                (bot_c - 0.4 * r, bot_y - 0.05 * r), (bot_c - 1.15 * r, bot_y + 0.2 * r)]
        d.polygon(poly, fill=P["cape"] + (255,))
        d.line(poly + [poly[0]], fill=(200, 200, 205, 255), width=max(2, int(r * 0.06)))
    if neck:                                                         # cou (derrière le col)
        d.line((cx, cy, neck[0], neck[1]), fill=P["skin"] + (255,), width=max(3, int(r * 0.6)))
    img = Image.alpha_composite(back, body)
    hdl = Image.new("RGBA", body.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(hdl)
    d.ellipse((cx - r, cy - r * 1.04, cx + r, cy + r * 1.04), fill=P["skin"] + (255,))
    d.ellipse((cx - side * 0.15 * r - 0.55 * r, cy - 0.85 * r, cx - side * 0.15 * r - 0.05 * r, cy - 0.45 * r),
              fill=(255, 226, 196, 255))                             # reflet du crâne
    hdl = hdl.filter(ImageFilter.GaussianBlur(0.7))
    img.alpha_composite(hdl)
    if cape and neck:                                                # col de la cape (boutons) par-dessus
        d = ImageDraw.Draw(img)
        nx, ny = neck
        d.ellipse((nx - 0.6 * r, ny - 0.25 * r, nx + 0.6 * r, ny + 0.25 * r), fill=P["cape"] + (255,))
        d.ellipse((nx + side * 0.35 * r - 0.11 * r, ny - 0.1 * r, nx + side * 0.35 * r + 0.11 * r, ny + 0.12 * r),
                  fill=(141, 136, 0, 255))
    return img


def saitama(frames, head_r=31.0, cape=True):
    return [saitama_frame(f, head_r, cape, cape_phase=i * 0.35) for i, f in enumerate(frames)]
