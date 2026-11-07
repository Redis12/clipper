"""« HOW FAR CAN GOKU HIT THE BALL? » (07/11) : stickman Goku SSJ1 de l'utilisateur, un coup, la boule fait le tour
de la Terre et revient frapper Goku. Easter eggs : MACH 1, Kame House, Vegeta (« KAKAROT!!! »), sortie de
l'atmosphère, vue de l'espace, BONK.

python3 tools/punch/how_far.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import goku_poses as gp  # noqa: E402
import rig  # noqa: E402
import sticknodes as sn  # noqa: E402
from mugen_punch import F, GROUND, H, W, FPS, ball_sprite, mountains, sky  # noqa: E402
from stick_punch import GX, SCALE, T_CHARGE, T_HIT, T_SSJ, T_SWING, ease, pose_at  # noqa: E402
from clipper.slides import fusion, render, vfxgen  # noqa: E402

BALL_R = 220
E0 = T_HIT + 0.2                          # départ de la boule
# (fin du segment en s après E0, distance en km à la fin)
SEG = [(2.2, 5.0), (4.2, 15.0), (5.8, 40.0), (7.4, 100.0), (14.6, 40075.0)]
TS = 1.5                                  # 1 unité d'histoire = 1,5 s réelle (vidéo ≈ 30 s)
SP = SEG[-1][0]
T_BACK = E0 + SP * TS                        # retour chez Goku
T_BONK = T_BACK + 1.0
DUR = T_BONK + 3.2
KAME_AT, VEG_AT, MACH_AT = 3.2, 4.85, 0.15


def km_at(t):
    e = (t - E0) / TS
    if e <= 0:
        return 0.0
    prev_t, prev_d = 0.0, 0.0
    for st, sd in SEG:
        if e <= st:
            x = (e - prev_t) / (st - prev_t)
            if prev_d <= 0:
                return sd * x ** 1.3
            return math.exp(math.log(prev_d) + (math.log(sd) - math.log(prev_d)) * x)
        prev_t, prev_d = st, sd
    return SEG[-1][1]


def fmt(km):
    if km < 1:
        return f"{km * 1000:,.0f} m"
    if km < 100:
        return f"{km:,.1f} km"
    return f"{km:,.0f} km"


def kame_house():
    im = Image.new("RGBA", (520, 360), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((20, 250, 500, 360), fill=(240, 215, 140))                    # île
    d.line((380, 290, 430, 120), fill=(120, 80, 40), width=14)              # palmier
    for a in range(0, 360, 60):
        r = math.radians(a)
        d.polygon([(430, 120), (430 + math.cos(r) * 95, 120 + math.sin(r) * 40 - 10), (430 + math.cos(r + .3) * 60, 120 + math.sin(r + .3) * 30)],
                  fill=(60, 170, 70))
    d.rectangle((140, 150, 330, 280), fill=(250, 150, 170))                  # maison rose
    d.polygon([(120, 160), (235, 80), (350, 160)], fill=(220, 50, 50))       # toit rouge
    d.rectangle((215, 210, 255, 280), fill=(120, 70, 50))
    d.rectangle((160, 180, 195, 210), fill=(140, 200, 255))
    d.rectangle((275, 180, 310, 210), fill=(140, 200, 255))
    d.text((235, 125), "KAME", fill="white", anchor="mm", font=F("anton.woff2", 26))
    return im


def earth(r):
    s = int(r * 2 + 120)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c = s / 2
    glow = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((c - r - 30, c - r - 30, c + r + 30, c + r + 30), fill=(90, 170, 255, 160))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(25)))
    d = ImageDraw.Draw(im)
    d.ellipse((c - r, c - r, c + r, c + r), fill=(30, 90, 200))
    rr = random.Random(4)
    land = Image.new("L", (s, s), 0)
    ld = ImageDraw.Draw(land)
    for _ in range(14):
        x, y = c + rr.uniform(-r * .7, r * .7), c + rr.uniform(-r * .7, r * .7)
        for _ in range(6):
            w = rr.uniform(r * .08, r * .22)
            ox, oy = rr.uniform(-w, w), rr.uniform(-w, w)
            ld.ellipse((x + ox - w, y + oy - w * .7, x + ox + w, y + oy + w * .7), fill=255)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).ellipse((c - r, c - r, c + r, c + r), fill=255)
    land = Image.composite(land, Image.new("L", (s, s), 0), mask)
    im.paste((70, 160, 80, 255), (0, 0), land)
    shade = Image.new("L", (s, s), 0)
    ImageDraw.Draw(shade).ellipse((c - r + r * .35, c - r + r * .2, c + r + r * .9, c + r + r * .7), fill=150)
    shade = Image.composite(shade.filter(ImageFilter.GaussianBlur(30)), Image.new("L", (s, s), 0), mask)
    im.paste((5, 10, 30, 255), (0, 0), shade)
    return im


def satellite():
    im = Image.new("RGBA", (220, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x0 in (8, 142):
        d.rectangle((x0, 38, x0 + 70, 82), fill=(40, 80, 170), outline=(180, 200, 255), width=3)
        for gx in range(x0 + 14, x0 + 70, 14):
            d.line((gx, 40, gx, 80), fill=(120, 160, 230), width=2)
    d.line((78, 60, 142, 60), fill=(200, 200, 210), width=5)
    d.rectangle((88, 34, 132, 86), fill=(225, 190, 90), outline=(120, 90, 40), width=3)
    d.ellipse((98, 8, 122, 32), outline=(230, 230, 240), width=4)
    return im


def frieza_ship():
    """Vaisseau rond blanc à hublots (clin d'œil, dessiné en code)."""
    im = Image.new("RGBA", (240, 180), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for lx in (50, 120, 190):
        d.line((lx, 110, lx + (lx - 120) * 0.3, 165), fill=(170, 170, 190), width=7)
    d.ellipse((10, 30, 230, 140), fill=(235, 235, 245), outline=(150, 150, 170), width=4)
    d.chord((10, 30, 230, 140), 0, 180, fill=(205, 205, 220))
    for hx in range(40, 220, 36):
        d.ellipse((hx - 9, 72, hx + 9, 90), fill=(170, 80, 220))
    d.ellipse((90, 18, 150, 50), fill=(200, 140, 255), outline=(120, 60, 180), width=3)
    return im


def day_sky(warm):
    """Ciel de jour (demandé : « le ciel c'est déprimant ») : bleu vif → clair, soleil + halo ; warm = un peu doré."""
    y = np.linspace(0, 1, H)[:, None, None]
    top = np.array([30, 110, 235.])
    bot = np.array([165, 220, 255.]) * (1 - warm * .4) + np.array([255, 225, 160.]) * warm * .4
    a = top * (1 - y) + bot * y
    im = Image.fromarray(a.repeat(W, 1).clip(0, 255).astype(np.uint8)).convert("RGBA")
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gd.ellipse((700, 380, 1020, 700), fill=(255, 250, 200, 120))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(60)))
    ImageDraw.Draw(im).ellipse((790, 470, 930, 610), fill=(255, 250, 215))
    return im


def stars(n=220, seed=1):
    r = random.Random(seed)
    return [(r.uniform(0, W), r.uniform(0, H), r.uniform(1, 3.2), r.uniform(0.3, 1)) for _ in range(n)]


def main():
    fig = sn.load(sys.argv[1])
    out = Path(sys.argv[2])
    imP, posP, oP = sn.render(fig, scale=SCALE, absolute=gp.PUNCH)
    bottomP = np.nonzero(np.asarray(imP)[..., 3].max(1) > 0)[0].max()
    DASH = 120
    fist_x = GX + DASH + (posP[253][0] - oP[0])
    fist_y = GROUND - (bottomP - posP[253][1])
    BALL_X0 = fist_x + BALL_R - 25
    far = mountains(1, (120, 160, 220, 255), 170, 1150, 320, W * 14)
    near = mountains(2, (60, 130, 80, 255), 120, 1290, 230, W * 28)
    ball_big = ball_sprite(BALL_R)
    ball_mid = ball_sprite(130)
    kame = kame_house()
    veg = fusion.icon(str(ROOT / "library/_fusion/Vegeta/1 Base.jpg"), 230, (60, 90, 255))
    eimg = earth(330)
    st = stars()
    explo = list(vfxgen.frames("explosion", 520, (255, 210, 80)))
    ring = list(vfxgen.frames("ring", 700, (255, 240, 180)))
    bolt = list(vfxgen.frames("lightning", 260, (255, 240, 120)))
    fT, fS, fN, fL = F("anton.woff2", 100), F("mont900.woff2", 30), F("anton.woff2", 104), F("anton.woff2", 64)
    rnd = random.Random(7)
    sat, ship, hits = satellite(), frieza_ship(), {}
    debris, trail = [], []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    labels = []                                                       # (t0, texte, couleur)
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        tt = t if t < T_HIT else max(T_HIT, t - 0.2)
        e = (tt - E0) / TS if tt > E0 else tt - E0
        km = km_at(tt)
        if T_BACK <= t:
            km = SEG[-1][1]
        # ---------------------------------------------------------------- scènes
        if t < E0 + 7.4 * TS or t >= T_BACK:
            # monde « au sol » : de 0 à 2.2 s terre, puis mer ; la caméra monte vers le ciel entre 4.2 et 7.4 s
            if t >= T_BACK:
                warm, scroll, tilt, sea = 1.0, 0.0, 0.0, 0.0
            else:
                warm = min(1.0, max(0.0, e / 2.5)) if e > 0 else 0.0
                scroll = (km * 1300 if km < 15 else 15 * 1300 + (km - 15) * 400)
                tilt = ease((e - 4.2) / 3.2) if e > 4.2 else 0.0
                sea = ease((e - 1.9) / 0.6) if e > 1.9 else 0.0
            img = day_sky(warm)
            if tilt > 0:                                              # le ciel fonce, les étoiles arrivent
                dk = Image.new("RGBA", (W, H), (2, 2, 10, int(255 * min(1, tilt * 1.15))))
                img.alpha_composite(dk)
            shift = int(tilt * 1400)
            if shift < H:
                img.alpha_composite(far.crop((int(scroll * .2) % (W * 12), 0, int(scroll * .2) % (W * 12) + W, H)), (0, shift))
                if sea < 1:
                    nl = near.crop((int(scroll * .5) % (W * 26), 0, int(scroll * .5) % (W * 26) + W, H))
                    if sea > 0:
                        nl.putalpha(nl.getchannel("A").point(lambda v, s_=sea: int(v * (1 - s_))))
                    img.alpha_composite(nl, (0, shift))
            img = img.convert("RGB")
            d = ImageDraw.Draw(img, "RGBA")
            gy = GROUND + shift
            if gy < H:
                gcol = tuple(int(a * (1 - sea) + b * sea) for a, b in zip((70, 150, 70), (30, 120, 210)))
                d.rectangle((0, gy, W, H), fill=gcol)
                d.line((0, gy, W, gy), fill=(190, 240, 140), width=6)
                if sea > 0:
                    for k in range(14):
                        x = (k * 170 - scroll * 0.9) % (W + 200) - 100
                        d.arc((x, gy + 20 + (k % 3) * 40, x + 120, gy + 60 + (k % 3) * 40), 200, 340,
                              fill=(160, 210, 255, int(150 * sea)), width=3)
                else:
                    for gx in range(-(int(scroll) % 160), W, 160):
                        d.line((gx, gy + 18, gx + 60, gy + 18), fill=(80, 110, 160, 160), width=3)
            if tilt > 0.2:
                for sx, sy, sr, sa in st:
                    d.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(255, 255, 255, int(255 * sa * min(1, (tilt - .2) * 2))))
            # nuages qui filent (phase ciel)
            if 4.0 < e < 7.4:
                for k in range(6):
                    cx_ = (k * 300 - (e - 4.0) * 2600) % (W + 600) - 300
                    cy_ = 900 + (k % 3) * 220 - tilt * 300
                    d.ellipse((cx_, cy_, cx_ + 260, cy_ + 70), fill=(255, 255, 255, int(200 * (1 - tilt))))
            # Kame House
            if 2.4 < e < 4.4 and t < T_BACK:
                kx = W + 200 - (e - 2.4) * 900
                img.paste(kame, (int(kx), int(gy - 300)), kame)
                if abs(e - KAME_AT) < 0.9 and not any(l[1].startswith("KAME") for l in labels):
                    labels.append((t, "KAME HOUSE · 11 km", (255, 160, 190)))
            # Goku (au début, puis au retour)
            if t < E0 + 1.2 or t >= T_BACK:
                if t >= T_BACK:
                    pose = dict(gp.IDLE)
                    pose[53] += 2 * math.sin(t * 5)
                    gx_ = GX + 140
                else:
                    pose = pose_at(tt)
                    gx_ = GX + (120 * ease((tt - T_SWING) / (T_HIT - T_SWING)) if tt >= T_SWING else 0) - (scroll if tt > T_HIT else 0)
                ssj = tt >= T_SSJ
                cm = None if ssj else (lambda i, c: (22, 22, 28, 255) if c[:3] in gp.HAIR_COLORS else c)
                pim, pos, org = sn.render(fig, scale=SCALE, absolute=pose, color_map=cm)
                bottom = np.nonzero(np.asarray(pim)[..., 3].max(1) > 0)[0].max()
                px, py = int(gx_ - org[0]), int(GROUND - bottom)
                power = 0.0
                if T_SSJ <= tt < T_HIT + 0.3 and t < T_BACK:
                    power = min(1.0, (tt - T_SSJ) / 0.6) * (1 if tt < T_HIT else max(0, 1 - (tt - T_HIT) / 0.3))
                    au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ad = ImageDraw.Draw(au)
                    ch_ = (GROUND - py) * 0.62
                    for scl, col, al in ((1.25, (255, 225, 40), 150), (1.0, (255, 245, 150), 190), (0.7, (255, 255, 235), 170)):
                        ad.polygon(rig.aura_poly(gx_, GROUND - ch_ * 0.95, (150 + 40 * power) * scl, ch_ * scl, t * 1.3 + scl,
                                                 n=30, seed=int(scl * 10)), fill=col + (int(al * power),))
                    ad.rectangle((0, GROUND, W, H), fill=(0, 0, 0, 0))
                    g_ = au.filter(ImageFilter.GaussianBlur(18))
                    img.paste(g_, (0, 0), g_)
                    img.paste(au, (0, 0), au)
                    if fi % 3 == 0 and power > 0.3:
                        b = bolt[fi // 3 % len(bolt)]
                        img.paste(b, (int(gx_ - b.width / 2 + rnd.uniform(-60, 60)), int(py + rnd.uniform(0, 200))), b)
                    if rnd.random() < 0.45 * power:
                        debris.append([gx_ + rnd.uniform(-220, 220), GROUND - 6, rnd.uniform(-25, 25), -rnd.uniform(90, 220),
                                       t, rnd.uniform(6, 14), 2.0])
                if t >= T_BONK:                                       # Goku assommé : il bascule
                    ang = min(85, (t - T_BONK) * 260)
                    pim = pim.rotate(ang, expand=True, resample=Image.BICUBIC)
                    py += int(min(1.0, (t - T_BONK) / 0.35) * 140)
                img.paste(pim, (px, py), pim)
                d = ImageDraw.Draw(img, "RGBA")
                if 0 <= tt - T_SSJ < 0.35 and t < T_BACK:
                    d.rectangle((0, 0, W, H), fill=(255, 245, 180, int(235 * (1 - (tt - T_SSJ) / 0.35))))
        else:
            # ---------------------------------------------------------------- espace : tour de la Terre
            img = Image.new("RGB", (W, H), (3, 4, 14))
            d = ImageDraw.Draw(img, "RGBA")
            for sx, sy, sr, sa in st:
                d.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(255, 255, 255, int(255 * sa)))
            ec = (W / 2, H * 0.6)
            img.paste(eimg, (int(ec[0] - eimg.width / 2), int(ec[1] - eimg.height / 2)), eimg)
            d = ImageDraw.Draw(img, "RGBA")
            # Lune en easter egg
            d.ellipse((800, 640, 900, 740), fill=(220, 220, 210))
            d.ellipse((830, 670, 850, 690), fill=(180, 180, 170))
            k = (e - 7.4) / (SP - 7.4)
            ang = math.radians(200 - 360 * (0.15 * ease(k) + 0.85 * k))
            R = 330 + 70
            bxp, byp = ec[0] + math.cos(ang) * R, ec[1] - math.sin(ang) * R
            deg = math.degrees(ang)
            for name, adeg, spr, lab, col in (("sat", 150, sat, "SATELLITE DOWN", (200, 220, 255)),
                                              ("ship", 40, ship, "FRIEZA'S SHIP?!", (200, 120, 255))):
                ox, oy = ec[0] + math.cos(math.radians(adeg)) * R, ec[1] - math.sin(math.radians(adeg)) * R
                if name not in hits and deg <= adeg:
                    hits[name] = t
                    labels.append((t, lab, col))
                if name not in hits:
                    img.paste(spr, (int(ox - spr.width / 2), int(oy - spr.height / 2 + 6 * math.sin(t * 3))), spr)
                else:
                    a_ = t - hits[name]
                    if a_ < 1.2:                                      # éjecté en tournant
                        rs = spr.rotate(a_ * 700, resample=Image.BICUBIC)
                        img.paste(rs, (int(ox - rs.width / 2 + a_ * 500), int(oy - rs.height / 2 - a_ * 420)), rs)
                    if a_ < 0.8:
                        ex = explo[min(len(explo) - 1, int(a_ / 0.8 * len(explo)))]
                        img.paste(ex, (int(ox - ex.width / 2), int(oy - ex.height / 2)), ex)
            d = ImageDraw.Draw(img, "RGBA")
            trail.append((bxp, byp))
            del trail[:-40]
            for j, (tx, ty) in enumerate(trail):
                a_ = j / len(trail)
                d.ellipse((tx - 10 * a_, ty - 10 * a_, tx + 10 * a_, ty + 10 * a_), fill=(255, 150, 60, int(220 * a_)))
            d.ellipse((bxp - 22, byp - 22, bxp + 22, byp + 22), fill=(120, 230, 255))
            d.ellipse((bxp - 34, byp - 34, bxp + 34, byp + 34), outline=(255, 200, 120, 200), width=4)
            if k > 0.08 and not any(l[1].startswith("LEAVING") for l in labels):
                pass
            if k > 0.78 and not any(l[1].startswith("AROUND") for l in labels):
                labels.append((t, "AROUND THE WORLD?!", (120, 230, 255)))
        d = ImageDraw.Draw(img, "RGBA")
        # ---------------------------------------------------------------- la boule (phases au sol / ciel)
        if t < E0 + 7.4 * TS:
            if t < E0:
                bx, by, bimg = BALL_X0, GROUND - BALL_R, ball_big
            else:
                rise = ease(min(1.0, e / 0.7))
                bx = BALL_X0 + (540 - BALL_X0) * rise
                by = GROUND - BALL_R - rise * 380 - (ease((e - 4.2) / 3.2) * -200 if e > 4.2 else 0)
                bimg = ball_big if e < 4.0 else ball_mid
            rb = bimg.rotate(-math.degrees(km * 40), resample=Image.BICUBIC)
            heat = ease((e - 5.6) / 1.4) if e > 5.6 else 0.0
            if heat > 0:                                              # rentre en chauffe : traînée de feu
                fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                fd = ImageDraw.Draw(fl)
                rr_ = bimg.width / 2 - 30
                fd.polygon([(bx - rr_ * 0.7, by - rr_ * 0.7), (bx - rr_ * 4.5, by + rr_ * 1.2), (bx - rr_ * 0.7, by + rr_ * 0.7)],
                           fill=(255, 120, 30, int(200 * heat)))
                fl = fl.filter(ImageFilter.GaussianBlur(20))
                img.paste(fl, (0, 0), fl)
            img.paste(rb, (int(bx - rb.width / 2), int(by - rb.height / 2)), rb)
            d = ImageDraw.Draw(img, "RGBA")
            if e > 0.5:                                               # lignes de vitesse
                for _ in range(16):
                    y = rnd.uniform(560, H - 200)
                    x = rnd.uniform(0, W)
                    d.line((x, y, x + rnd.uniform(200, 500), y), fill=(255, 255, 255, 70), width=3)
            if 0 <= e - MACH_AT < 0.6:                                # bang supersonique
                a_ = (e - MACH_AT) / 0.6
                for j in range(3):
                    rr2 = 120 + a_ * 600 + j * 50
                    d.arc((bx - rr2 * 0.5, by - rr2, bx + rr2 * 0.5, by + rr2), 100, 260,
                          fill=(255, 255, 255, int(220 * (1 - a_))), width=8)
                if not any(l[1].startswith("MACH") for l in labels):
                    labels.append((t, "MACH 1!", (255, 255, 255)))
            # Vegeta
            if 4.3 < e < 6.4:
                vx = W + 150 - (e - 4.3) * 1600 if e < VEG_AT else None
                if vx is not None:
                    img.paste(veg, (int(vx - veg.width / 2), int(by - veg.height / 2)), veg)
                else:
                    a_ = e - VEG_AT
                    vr = veg.rotate(a_ * 900, resample=Image.BICUBIC)
                    img.paste(vr, (int(bx - 160 - a_ * 900), int(by + a_ * 1100 - vr.height / 2)), vr)
                    d = ImageDraw.Draw(img, "RGBA")
                    if a_ < 1.2:
                        bx2, by2 = W / 2, by + 300
                        d.rounded_rectangle((bx2 - 280, by2 - 70, bx2 + 280, by2 + 70), 30, fill=(255, 255, 255, 240),
                                            outline=(0, 0, 0), width=5)
                        d.polygon([(bx2 - 40, by2 + 66), (bx2, by2 + 140), (bx2 + 30, by2 + 66)], fill=(255, 255, 255))
                        d.text((bx2, by2), "KAKAROT!!!", font=F("anton.woff2", 92), fill=(220, 30, 30), anchor="mm")
                    if not any(l[1].startswith("VEGETA") for l in labels):
                        labels.append((t, "VEGETA · 28 km", (120, 160, 255)))
            if e > 5.9 and not any(l[1].startswith("LEAVING") for l in labels):
                labels.append((t, "LEAVING EARTH · 100 km", (255, 150, 80)))
        # ---------------------------------------------------------------- le coup : impact, débris
        ee = t - T_HIT
        if 0 <= ee < 0.2:
            g = img.convert("L").point(lambda v: 255 if v > 80 else 0)
            img = Image.merge("RGB", (g, g.point(lambda v: v * .85), g.point(lambda v: v * .3)))
            if ee < 1 / FPS:
                for _ in range(22):
                    debris.append([fist_x + rnd.uniform(-30, 30), fist_y + rnd.uniform(-50, 50), rnd.uniform(-250, 700),
                                   -rnd.uniform(300, 950), t, rnd.uniform(8, 18), 1.6])
        d = ImageDraw.Draw(img, "RGBA")
        if 0.2 <= ee < 1.0:
            k = (ee - 0.2) / 0.8
            ex = explo[min(len(explo) - 1, int(k * len(explo)))]
            img.paste(ex, (int(fist_x - ex.width / 2), int(fist_y - ex.height / 2)), ex)
            rr = ring[min(len(ring) - 1, int(k * len(ring)))]
            img.paste(rr, (int(fist_x - rr.width / 2), int(fist_y - rr.height / 2)), rr)
            d = ImageDraw.Draw(img, "RGBA")
            if ee < 0.45:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(190 * (1 - (ee - 0.2) / 0.25))))
        alive = []
        for db in debris:
            a = t - db[4]
            if a < db[6] and t < T_BACK:
                x, y = db[0] + db[2] * a, db[1] + db[3] * a + 950 * a * a
                if y < GROUND + 4:
                    s = db[5]
                    d.polygon([(x - s, y), (x - s * .3, y - s), (x + s, y - s * .4), (x + s * .6, y + s * .7)], fill=(70, 60, 80, 255))
                    alive.append(db)
        debris[:] = alive
        # ---------------------------------------------------------------- retour : la boule revient et BONK
        if T_BACK <= t:
            if t < T_BONK:
                k = (t - T_BACK) / (T_BONK - T_BACK)
                hx = GX + 140
                bx = -300 + (hx - 40 + 300) * k ** 2
                by = GROUND - 470
                rb = ball_mid.rotate(-k * 900, resample=Image.BICUBIC)
                img.paste(rb, (int(bx - rb.width / 2), int(by - rb.height / 2)), rb)
                d = ImageDraw.Draw(img, "RGBA")
                for _ in range(10):
                    y = by + rnd.uniform(-120, 120)
                    d.line((bx - 500, y, bx - 150, y), fill=(255, 255, 255, 80), width=3)
                d.text((W / 2, 640), "MEANWHILE...", font=fL, fill=(255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=(20, 10, 40))
            else:
                a_ = t - T_BONK
                if a_ < 0.15:
                    d.rectangle((0, 0, W, H), fill=(255, 255, 255, 220))
                if a_ < 1.0:
                    hx, hy = GX + 140, GROUND - 470
                    for j in range(10):
                        an = j * math.tau / 10
                        d.line((hx, hy, hx + math.cos(an) * (80 + a_ * 260), hy + math.sin(an) * (80 + a_ * 260)),
                               fill=(255, 230, 80, int(255 * (1 - a_))), width=8)
                    d.text((hx + 160, hy - 120), "BONK!", font=F("anton.woff2", int(130 * (1 + 0.3 * max(0, 0.2 - a_)))),
                           fill=(255, 220, 60), anchor="mm", stroke_width=6, stroke_fill=(40, 10, 10))
                d.text((W / 2, 660), "IT WENT AROUND", font=F("anton.woff2", 104), fill=(255, 255, 255), anchor="mm",
                       stroke_width=5, stroke_fill=(20, 10, 40))
                d.text((W / 2, 770), "THE WORLD", font=F("anton.woff2", 104), fill=(255, 200, 60), anchor="mm",
                       stroke_width=5, stroke_fill=(20, 10, 40))
                rgba = img.convert("RGBA")
                render.draw_rich(rgba, (W / 2, 850), "Who hits it farther? Comment 👇", F("mont900.woff2", 52),
                                 (255, 255, 255), anchor="ma", stroke_width=3, stroke_fill=(0, 0, 0))
                img = rgba.convert("RGB")
                d = ImageDraw.Draw(img, "RGBA")
        # ---------------------------------------------------------------- titre + compteur + étiquettes
        d.text((W / 2, 70), "HOW FAR CAN GOKU", font=fT, fill="white", anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W / 2, 176), "HIT THE BALL?", font=fT, fill=(255, 200, 60), anchor="mt", stroke_width=4, stroke_fill=(20, 10, 40))
        d.text((W / 2, 318), "DISTANCE", font=fS, fill=(200, 200, 230), anchor="mt")
        dcol = (255, 90, 120) if km <= 0 else ((90, 255, 160) if km < 100 else (120, 230, 255))
        d.text((W / 2, 356), fmt(km), font=fN, fill=dcol, anchor="mt", stroke_width=4, stroke_fill=(10, 10, 30))
        for (t0, txt, col) in labels:
            a = t - t0
            if 0 <= a < 1.6:
                s = 1 + 0.25 * max(0.0, 1 - a / 0.15)
                al = int(255 * min(1.0, (1.6 - a) / 0.3))
                d.text((W / 2, 520), txt, font=F("anton.woff2", int(70 * s)), fill=col + (al,), anchor="mm",
                       stroke_width=4, stroke_fill=(10, 10, 30, al))
        # secousses
        sh = 0
        if T_CHARGE <= tt < T_HIT:
            sh = 4
        if 0 <= tt - T_SSJ < 0.45:
            sh = 16
        if 0 <= ee < 0.8:
            sh = 30 * (1 - ee / 0.8)
        if abs(t - (E0 + VEG_AT * TS)) < 0.25 or 0 <= t - T_BONK < 0.4 or any(0 <= t - h_ < 0.3 for h_ in hits.values()):
            sh = 20
        if sh:
            dx, dy = rnd.randint(-int(sh), int(sh)), rnd.randint(-int(sh), int(sh))
            bgf = Image.new("RGB", (W, H), (0, 0, 0))
            bgf.paste(img, (dx, dy))
            img = bgf
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    # ---------------------------------------------------------------- son
    from clipper.slides import domain
    rate = fusion.RATE
    na = int(DUR * rate) + rate
    audio = np.zeros(na, np.float32)

    def put(t_, x, g):
        if x is None:
            return
        i = int(t_ * rate)
        seg = x[: max(0, na - i)]
        audio[i:i + len(seg)] += seg * g
    fr_ = "dragon ball"
    S = lambda fam, seed=0: domain.sfx(fam, mode="anime", seed=seed, franchise=fr_)  # noqa: E731
    put(T_CHARGE, S("bomb", 5), 0.25)
    put(T_SSJ - 0.05, S("transform"), 0.9)
    put(T_SWING, S("teleport"), 0.5)
    put(T_HIT, S("hit", 1), 1.0)
    put(T_HIT + 0.2, S("bomb", 2), 0.9)
    put(E0 + MACH_AT * TS, S("bomb", 4), 0.7)
    put(E0 + 1.0 * TS, S("beam", 3), 0.35)
    put(E0 + VEG_AT * TS, S("hit", 2), 1.0)
    put(E0 + VEG_AT * TS + 0.05, S("ko"), 0.6)
    put(E0 + 5.8 * TS, S("beam", 1), 0.5)
    put(E0 + 7.4 * TS, S("teleport", 1), 0.5)
    for adeg in (150, 40):                                           # satellite, vaisseau
        kk = next(i / 2000 for i in range(2000) if 200 - 360 * (0.15 * ease(i / 2000) + 0.85 * i / 2000) <= adeg)
        th = E0 + (7.4 + kk * (SP - 7.4)) * TS
        put(th, S("hit", 4), 0.9)
        put(th + 0.03, S("bomb", 6), 0.6)
    put(T_BACK + 0.4, S("teleport", 2), 0.6)
    put(T_BONK, S("hit", 3), 1.0)
    put(T_BONK + 0.05, S("ko", 1), 0.7)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out.with_suffix(".raw.mp4"))],
                   check=True)
    render.stamp_video(out.with_suffix(".raw.mp4"), out)
    print("OUT", out, round(DUR, 1))


if __name__ == "__main__":
    main()
