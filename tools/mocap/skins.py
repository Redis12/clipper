"""N'importe quel perso avec NOS mouvements de Goku découpés (08/11, demandé : « généralise les animations de notre
Goku »). Le corps du Goku (library/_mocap/clips) est découpé en morceaux par couleur, chaque morceau est repeint aux
couleurs du perso, la tête du Goku est enlevée et remplacée par la tête du perso (prise dans son modèle Stick Nodes :
la sous-arborescence du cou = tête + cheveux), posée au bon endroit, penchée comme celle du Goku, tournée du bon côté.

    frames, feet = skins.load("naruto", "coup_de_poing_fente", height=500, flip=False)   # comme clips.load

Morceaux : haut du gi (au-dessus de la ceinture), pantalon, sous-vêtement bleu (col/épaules), ceinture, poignets,
bottes (+ liseré), bras, mains, emblème. Ajouter un perso = une entrée dans SKINS (couleurs + modèle pour la tête).
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "punch"))
sys.path.insert(0, str(HERE))
import clips  # noqa: E402
import reskin  # noqa: E402
import sticknodes as sn  # noqa: E402

SN = ROOT / "library" / "_sticknodes"
SKIN = (250, 214, 182)

# couleurs : top / top_dark (côté arrière), pants / pants_dark, under (col/épaules), belt, wrist, boots, trim,
# arms (None = peau), hands (None = peau), skin ; head = modèle Stick Nodes (tête + cheveux) ou "bald"
SKINS = {
    "saitama": dict(top=(244, 234, 0), top_dark=(220, 211, 0), pants=(244, 234, 0), pants_dark=(220, 211, 0),
                    under=(244, 234, 0), belt=(30, 30, 32), wrist=(220, 0, 3), boots=(220, 0, 3), trim=(203, 0, 3),
                    arms=(244, 234, 0), hands=(220, 0, 3), skin=(255, 201, 155), head="bald", cape=(244, 244, 244)),
    "naruto": dict(top=(250, 128, 20), top_dark=(225, 105, 10), pants=(250, 128, 20), pants_dark=(225, 105, 10),
                   under=(30, 30, 38), belt=(250, 128, 20), wrist=None, boots=(30, 30, 40), trim=(30, 30, 40),
                   arms=(250, 128, 20), hands=None, skin=(250, 210, 170),
                   head=SN / "Naruto" / "naruto adult.json", head_scale=0.8),
    "vegeta": dict(top=(245, 245, 245), top_dark=(215, 215, 220), pants=(25, 50, 170), pants_dark=(18, 38, 140),
                   under=(25, 50, 170), belt=(25, 50, 170), wrist=(245, 245, 245), boots=(245, 245, 245),
                   trim=(230, 190, 40), arms=(25, 50, 170), hands=(245, 245, 245), skin=(250, 210, 175),
                   head=SN / "Dragon Ball" / "Vegeta (Armour Calssic).json"),
    "luffy": dict(top=(215, 30, 35), top_dark=(185, 22, 28), pants=(45, 85, 175), pants_dark=(35, 68, 145),
                  under=(215, 30, 35), belt=(240, 200, 60), wrist=None, boots=(150, 105, 65), trim=(150, 105, 65),
                  arms=None, hands=None, skin=(250, 205, 165), head=SN / "Luffy" / "LuffyOP.json"),
    "ichigo": dict(top=(32, 32, 38), top_dark=(22, 22, 28), pants=(32, 32, 38), pants_dark=(22, 22, 28),
                   under=(235, 235, 240), belt=(235, 235, 240), wrist=(32, 32, 38), boots=(32, 32, 38),
                   trim=(235, 235, 240), arms=(32, 32, 38), hands=None, skin=(250, 210, 175),
                   head=SN / "Ichigo" / "_Ichigo-Bankai-Arlando.json"),
}

_HEAD = {}


def head_sprite(path):
    """tête + cheveux d'un modèle Stick Nodes → (image, centre de la tête, rayon, regarde à gauche ?)"""
    key = str(path)
    if key in _HEAD:
        return _HEAD[key]
    fig = sn.load(path)
    lay = sn.layout(fig)
    par, kids = {}, {}

    def walk(n):
        for c in n["children"]:
            par[c["draw_order_index"]] = n.get("draw_order_index")
            kids.setdefault(n.get("draw_order_index"), []).append(c["draw_order_index"])
            walk(c)
    walk(fig["nodes"][0])
    best = None
    for i, n, a, b, g in lay:
        c = n["color"]
        if "Circle" in str(n.get("node_type") or n.get("type")):
            skinish = c["red"] > 180 and c["green"] > 130 and c["blue"] > 90 and c["red"] > c["blue"] + 40
            sc = n["length"] * (2 if skinish else 1)
            if best is None or sc > best[0]:
                best = (sc, i, n, a, b)
    _, hi, hn, ha, hb = best
    keep = set()

    def sub(i):
        keep.add(i)
        for k in kids.get(i, []):
            sub(k)
    sub(par[hi])
    scale = 1.0
    im, pos, org = sn.render(fig, scale=scale, color_map=lambda i, c: c if i in keep else (0, 0, 0, 0))
    # centre du cercle de la tête = milieu du segment (cercle de diamètre = longueur)
    p0, p1 = pos.get(par[hi]), pos[hi]
    cx, cy = ((ha[0] + hb[0]) / 2 - 0, (ha[1] + hb[1]) / 2)
    # positions de layout → image : org = origine de la racine dans l'image
    cxi, cyi = org[0] + cx * scale, org[1] + cy * scale
    R = hn["length"] / 2 * scale
    bb = im.getbbox()
    im = im.crop(bb)
    # de quel côté regarde la tête : visage (peau) à gauche ou à droite du centre de l'ensemble
    a = np.asarray(im).astype(int)
    vis = a[..., 3] > 100
    sk = vis & (a[..., 0] > 180) & (a[..., 1] > 130) & (a[..., 2] > 90) & (a[..., 0] > a[..., 2] + 30)
    face_left = bool(sk.sum() > 30 and np.nonzero(sk)[1].mean() < np.nonzero(vis)[1].mean())
    res = (im, (cxi - bb[0], cyi - bb[1]), R, face_left)
    _HEAD[key] = res
    return res


def _belt(navy, orange, r, prev):
    nl, nn = ndi.label(navy)
    best = None
    for i in range(1, nn + 1):
        m = nl == i
        ys, xs = np.nonzero(m)
        ring = ndi.binary_dilation(m, iterations=3) & ~m
        fr = (ring & orange).sum() / max(1, ring.sum())
        if fr > 0.5 and (xs.max() - xs.min() + ys.max() - ys.min()) > 0.9 * r:
            sc = fr * m.sum()
            if best is None or sc > best[0]:
                best = (sc, i, (xs.mean(), ys.mean()))
    return (nl, best[1], best[2]) if best else (nl, None, prev)


def segment(a, r, state):
    vis, orange, navy, dark, skin, white, lime, red = reskin._masks(a)
    H, W = vis.shape
    hd = reskin.head_of(a, r)
    gi_area = ndi.binary_fill_holes(orange | navy)
    remove = np.zeros_like(vis)
    head = None
    if hd:
        cx, cy, side, neck, core, face = hd
        zone = ndi.binary_dilation(core, iterations=max(12, int(r * 1.3)))
        remove = (zone & ~(orange | navy | skin) & ~gi_area) | core
        ol, on = ndi.label(orange & zone)                          # mèches classées « gi » par erreur
        if on:
            sz = ndi.sum(orange & zone, ol, range(1, on + 1))
            remove |= np.isin(ol, [i + 1 for i, v in enumerate(sz) if v < 0.5 * r * r]) & ~gi_area
        yy, xx = np.mgrid[:H, :W]
        dd = np.hypot(xx - cx, yy - cy)
        sk_lab, sn_ = ndi.label(skin)
        touch = set(np.unique(sk_lab[face])) - {0}
        remove |= np.isin(sk_lab, list(touch)) & (dd < r * 1.25)
        thin = orange & ~ndi.binary_opening(orange, iterations=3)
        remove |= thin & (dd < r * 1.7)
        head = (cx, cy, side, neck)
        state["side"] = side
    emblem = ndi.binary_dilation(ndi.binary_fill_holes(orange) & ~orange, iterations=2) & vis & ~remove & ~navy
    nl, bi, bc = _belt(navy, orange, r, state.get("belt"))
    state["belt"] = bc
    belt = (nl == bi) if bi else np.zeros_like(vis)
    # haut / pantalon : le gi coupé par la ceinture ; les morceaux qui touchent le cou = haut. Si haut et pantalon
    # se touchent (ceinture cachée), on coupe ce morceau-là selon l'axe ceinture → cou.
    top = np.zeros_like(vis)
    nk = state.get("neck") if not (head and head[3]) else head[3]
    if nk is not None:
        state["neck"] = nk
        cut = orange & ~ndi.binary_dilation(belt, iterations=2)
        ol, on = ndi.label(cut)
        yy, xx = np.mgrid[:H, :W]
        near = np.hypot(xx - nk[0], yy - nk[1]) < 1.5 * r
        ids = set(np.unique(ol[near & cut])) - {0}
        for i in ids:
            m = ol == i
            ys = np.nonzero(m)[0]
            merged = m.sum() > 0 and (ys.max() - nk[1]) > 5.5 * r          # descend jusqu'aux jambes
            if merged and bc is not None:
                ax, ay = nk[0] - bc[0], nk[1] - bc[1]
                L = max(1e-6, math.hypot(ax, ay))
                proj = ((xx - bc[0]) * ax + (yy - bc[1]) * ay) / L
                top |= m & (proj > 0.08 * r)
            elif merged:
                top |= m & (yy < nk[1] + 2.6 * r)
            else:
                top |= m
    pants = orange & ~top
    lum = a[..., 0].astype(int)
    light = ndi.median_filter(((lum >= 228) & orange).astype(np.uint8), size=max(5, int(r / 4) | 1)) > 0
    # bleu nuit : bottes (touchent le liseré ou tout en bas), poignets (touchent une main), col/épaules
    rr, gg, bb_ = [a[..., i].astype(int) for i in range(3)]
    lightblue = vis & (bb_ > rr + 20) & (bb_ >= 140) & ~skin
    boots = np.zeros_like(vis)
    wrists = np.zeros_like(vis)
    under = np.zeros_like(vis)
    sk_lab, sn_ = ndi.label(skin & ~remove)
    hand_ids = set()
    for i in range(1, sn_ + 1):
        m = sk_lab == i
        ring = ndi.binary_dilation(m, iterations=3) & ~m
        if not (ring & orange).sum() > 4 and m.sum() < 1.3 * r * r:
            hand_ids.add(i)
    hands = np.isin(sk_lab, list(hand_ids)) & ndi.binary_opening(skin, iterations=2)
    arms = (skin & ~remove) & ~np.isin(sk_lab, list(hand_ids)) & ndi.binary_opening(skin, iterations=2)
    near_hand = ndi.binary_dilation(hands, iterations=4)
    for i in range(1, nl.max() + 1):
        if i == bi:
            continue
        m = nl == i
        ys, xs = np.nonzero(m)
        if (ndi.binary_dilation(m, iterations=3) & lime).sum() > 3 or ys.mean() > H * 0.72:
            boots |= m
        elif (m & near_hand).any():
            wrists |= m
        else:
            under |= m
    under |= lightblue & ~remove
    hands &= ~emblem
    arms &= ~emblem
    under &= ~emblem
    trim = (lime | red) & ~emblem & ndi.binary_dilation(boots, iterations=max(4, int(r * 0.25)))
    return dict(remove=remove, emblem=emblem, belt=belt, top=top, pants=pants, light=light, boots=boots,
                wrists=wrists, under=under, hands=hands, arms=arms, trim=trim, head=head)


def _paint(out, a, mask, col, ref=None):
    if col is None or not mask.any():
        return
    if ref is None:
        out[..., :3][mask] = col
        return
    out[..., :3][mask] = col


def skin_frame(im, sk, r, state, cape_phase=0.0):
    a = np.array(im.convert("RGBA"))
    S = segment(a, r, state)
    out = a.astype(float).copy()
    L, D = S["light"], ~S["light"]
    _paint(out, a, S["top"] & L, sk["top"], (232, 72, 24))
    _paint(out, a, S["top"] & D, sk["top_dark"], (224, 64, 16))
    _paint(out, a, S["pants"] & L, sk["pants"], (232, 72, 24))
    _paint(out, a, S["pants"] & D, sk["pants_dark"], (224, 64, 16))
    emb_col = sk["top"]
    _paint(out, a, S["emblem"], emb_col)
    _paint(out, a, S["belt"], sk["belt"] or sk["top"], None)
    _paint(out, a, S["under"], sk["under"], (2, 26, 62))
    _paint(out, a, S["wrists"], sk["wrist"] or sk["skin"], (2, 26, 62) if sk["wrist"] else None)
    _paint(out, a, S["boots"], sk["boots"], (2, 26, 62))
    _paint(out, a, S["trim"], sk["trim"])
    _paint(out, a, S["arms"], sk["arms"] or sk["skin"], (248, 216, 184))
    _paint(out, a, S["hands"], sk["hands"] or sk["skin"], (248, 216, 184))
    painted = np.zeros(a.shape[:2], bool)
    for k_ in ("top", "pants", "emblem", "belt", "under", "wrists", "boots", "trim", "arms", "hands"):
        painted |= S[k_]
    left = (a[..., 3] > 20) & ~painted & ~S["remove"]
    if left.any() and painted.any():
        _, (iy, ix) = ndi.distance_transform_edt(~painted, return_indices=True)
        out[..., :3][left] = out[..., :3][iy[left], ix[left]]
    lab = np.zeros(a.shape[:2], np.int16)                    # 1 = corps, 2 = bras/mains : trait entre les deux
    for k_ in ("top", "pants", "belt", "under", "boots", "emblem"):
        lab[S[k_]] = 1
    for k_ in ("arms", "hands", "wrists"):
        lab[S[k_]] = 2
    edge = np.zeros(lab.shape, bool)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        sh = np.roll(np.roll(lab, dy, 0), dx, 1)
        edge |= (lab > 0) & (sh > 0) & (sh != lab)
    edge = ndi.binary_dilation(edge, iterations=max(1, int(r / 30))) & (lab > 0)
    out[..., :3][edge] *= 0.72
    out[S["remove"], 3] = 0
    body = Image.fromarray(out.clip(0, 255).astype(np.uint8))
    if not S["head"]:
        return body
    cx, cy, side, neck = S["head"]
    side = state.get("side", side)
    back = Image.new("RGBA", body.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(back)
    if neck:
        d.line((cx, cy, neck[0], neck[1]), fill=tuple(sk["skin"]) + (255,), width=max(3, int(r * 0.6)))
        if sk.get("cape"):
            nx, ny = neck
            bx = -side
            sway = math.sin(cape_phase) * 0.25 * r
            bot_y, bot_c = ny + 3.4 * r, nx + bx * 1.1 * r + sway
            poly = [(nx - 0.8 * r, ny - 0.1 * r), (nx + 0.8 * r, ny - 0.1 * r), (bot_c + 1.15 * r, bot_y),
                    (bot_c + 0.4 * r, bot_y + 0.25 * r), (bot_c - 0.4 * r, bot_y - 0.05 * r),
                    (bot_c - 1.15 * r, bot_y + 0.2 * r)]
            d.polygon(poly, fill=tuple(sk["cape"]) + (255,))
    img = Image.alpha_composite(back, body)
    # tête du perso : inclinaison = celle du Goku (cou → tête)
    tilt = 0.0
    if neck:
        tilt = math.degrees(math.atan2(cx - neck[0], neck[1] - cy))      # + = penchée vers la droite
        if abs(tilt) < 100:                                              # amorti (sauf salto, tête en bas)
            tilt = max(-30.0, min(30.0, 0.6 * tilt))
    if sk["head"] == "bald":
        hdl = Image.new("RGBA", body.size, (0, 0, 0, 0))
        dd = ImageDraw.Draw(hdl)
        dd.ellipse((cx - r, cy - r * 1.04, cx + r, cy + r * 1.04), fill=tuple(sk["skin"]) + (255,))
        dd.ellipse((cx - side * 0.15 * r - 0.55 * r, cy - 0.85 * r, cx - side * 0.15 * r - 0.05 * r, cy - 0.45 * r),
                   fill=(255, 226, 196, 255))
        img.alpha_composite(hdl.filter(ImageFilter.GaussianBlur(0.7)))
    else:
        spr, (hx, hy), R, auto_left = head_sprite(sk["head"])
        k = r * sk.get("head_scale", 1.12) / R
        spr = spr.resize((max(1, round(spr.width * k)), max(1, round(spr.height * k))), Image.LANCZOS)
        hx, hy = hx * k, hy * k
        face_left = sk.get("head_face_left", auto_left)
        if (side < 0) != face_left:
            spr = spr.transpose(Image.FLIP_LEFT_RIGHT)
            hx = spr.width - hx
        # rotation autour du centre de la tête
        big = Image.new("RGBA", (spr.width * 3, spr.height * 3), (0, 0, 0, 0))
        ox, oy = spr.width, spr.height
        big.alpha_composite(spr, (ox, oy))
        big = big.rotate(-tilt, resample=Image.BICUBIC, center=(ox + hx, oy + hy))
        img.alpha_composite(big, (int(round(cx - ox - hx)), int(round(cy - oy - hy)))) if cx - ox - hx >= 0 and cy - oy - hy >= 0 else img.paste(big, (int(round(cx - ox - hx)), int(round(cy - oy - hy))), big)
    return img


def load(char, move, height=500.0, flip=False):
    """comme clips.load, mais avec le perso `char`."""
    frames, feet = clips.load(move, height, flip=False)
    sk = SKINS[char]
    r = 0.062 * height
    st = {}
    out = [skin_frame(f, sk, r, st, cape_phase=i * 0.35) for i, f in enumerate(frames)]
    if flip:
        out = [o.transpose(Image.FLIP_LEFT_RIGHT) for o in out]
    return out, feet
