"""« EVERY GOKU FORM HITS THE BALL » (07/11) : le stickman Goku de l'utilisateur frappe la balle sous 5 formes
(cheveux + aura recolorés), chaque coup l'envoie beaucoup plus loin : Base → Kame House (1,2 km), SSJ → tour de la
Terre (40 075 km, rappel de « How far »), SSJ God → la Lune, SSJ Blue → le Soleil, Ultra Instinct → la planète de
Beerus (« ??? », Beerus se réveille). Classement des 5 formes en bas.

python3 tools/punch/every_form.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
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
import hud  # noqa: E402
import rig  # noqa: E402
import sticknodes as sn  # noqa: E402
from how_far import earth, kame_house, stars  # noqa: E402
from mugen_punch import GROUND, H, W, FPS, ball_sprite, mountains  # noqa: E402
from one_punch_line import desert_sky  # noqa: E402
from stick_punch import GX, SCALE, T_CHARGE, T_HIT, ease, pose_at  # noqa: E402
from clipper.slides import fusion, render, vfxgen  # noqa: E402

GSC = SCALE * 0.8
DASH = 90
BALL_R = 120
RD = 6.6                                   # durée d'une manche
T_PUNCH, T_HITL, T_CUT, T_RES = 0.5, 2.0, 2.6, 5.4
END = 2.6
FORMS = [  # nom court, nom long, cheveux, aura, km, scène, résultat
    ("BASE", "BASE FORM", (22, 22, 28), None, 1.2, "kame", "KAME HOUSE"),
    ("SSJ", "SUPER SAIYAN", (255, 225, 40), (255, 215, 40), 40075, "earth", "AROUND THE WORLD"),
    ("GOD", "SUPER SAIYAN GOD", (235, 50, 70), (255, 80, 60), 384400, "moon", "THE MOON"),
    ("BLUE", "SUPER SAIYAN BLUE", (60, 200, 255), (70, 170, 255), 149.6e6, "sun", "THE SUN"),
    ("UI", "ULTRA INSTINCT", (225, 230, 245), (200, 215, 255), None, "beerus", "BEERUS' PLANET"),
]
DUR = RD * len(FORMS) + END


def fmt(km):
    if km is None:
        return "???"
    if km < 100:
        return f"{km:,.1f} KM"
    if km < 1e6:
        return f"{km:,.0f} KM"
    return f"{km / 1e6:,.1f}M KM"


def glow(img, x, y, r, col, a=170, blur=None):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((x - r, y - r, x + r, y + r), fill=col + (a,))
    g = g.filter(ImageFilter.GaussianBlur(blur or r * 0.45))
    img.paste(g, (0, 0), g)


def space_bg(seed, nebula=None):
    y = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([4, 5, 18.]), np.array([12, 8, 34.])
    if nebula:
        bot = np.array(nebula, float)
    a = top * (1 - y) + bot * y
    im = Image.fromarray(a.repeat(W, 1).clip(0, 255).astype(np.uint8)).convert("RGB")
    d = ImageDraw.Draw(im)
    for sx, sy, sr, sa in stars(260, seed):
        c = int(255 * sa)
        d.ellipse((sx - sr, sy - sr, sx + sr, sy + sr), fill=(c, c, c))
    return im


def moon_sprite(r):
    s = int(r * 2 + 40)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    d.ellipse((c - r, c - r, c + r, c + r), fill=(205, 205, 200))
    rr = random.Random(3)
    for _ in range(14):
        x, y, q = c + rr.uniform(-r * .6, r * .6), c + rr.uniform(-r * .6, r * .6), rr.uniform(r * .06, r * .18)
        d.ellipse((x - q, y - q, x + q, y + q), fill=(175, 175, 170))
    return im


def sun_sprite(r):
    s = int(r * 2.8)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    c = s / 2
    g = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse((c - r * 1.3, c - r * 1.3, c + r * 1.3, c + r * 1.3), fill=(255, 150, 30, 200))
    im.alpha_composite(g.filter(ImageFilter.GaussianBlur(r * 0.25)))
    d = ImageDraw.Draw(im)
    d.ellipse((c - r, c - r, c + r, c + r), fill=(255, 190, 40))
    d.ellipse((c - r * .8, c - r * .8, c + r * .8, c + r * .8), fill=(255, 225, 90))
    return im


def planet_sprite(r):
    """Petite planète de Beerus : herbe, eau, pyramide (dessinée en code)."""
    s = int(r * 2 + 40)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    d.ellipse((c - r, c - r, c + r, c + r), fill=(80, 170, 120))
    d.chord((c - r, c - r, c + r, c + r), 200, 340, fill=(60, 140, 200))
    d.polygon([(c - r * .35, c - r * .55), (c, c - r * 1.15), (c + r * .35, c - r * .55)], fill=(215, 180, 110))
    d.line((c + r * .5, c - r * .7, c + r * .65, c - r * 1.2), fill=(90, 60, 40), width=8)
    d.ellipse((c + r * .45, c - r * 1.45, c + r * .9, c - r * 1.05), fill=(60, 150, 70))
    return im


def main():
    fig = sn.load(sys.argv[1])
    out = Path(sys.argv[2])
    beerus = sn.load(str(ROOT / "library/_sticknodes/Dragon Ball/Beerus (God Dest).json"))
    bim, _, _ = sn.render(beerus, scale=0.62)
    imP, posP, oP = sn.render(fig, scale=GSC, absolute=gp.PUNCH)
    bottomP = np.nonzero(np.asarray(imP)[..., 3].max(1) > 0)[0].max()
    fist_x = GX + DASH + (posP[253][0] - oP[0])
    fist_y = GROUND - (bottomP - posP[253][1])
    BX = fist_x + BALL_R - 20
    BY = GROUND - BALL_R
    ball = ball_sprite(BALL_R)
    ball_s = ball_sprite(34)
    far = mountains(1, (214, 150, 110, 255), 260, 1080, 420, W * 2)
    near = mountains(2, (176, 108, 72, 255), 150, 1190, 260, W * 2)
    ground_bg = desert_sky().convert("RGBA")
    ground_bg.alpha_composite(far.crop((0, 0, W, H)))
    ground_bg.alpha_composite(near.crop((0, 0, W, H)))
    gd = ImageDraw.Draw(ground_bg)
    gd.rectangle((0, 1180, W, H), fill=(222, 178, 120))
    for k in range(9):
        gd.ellipse((k * 130 + 20, GROUND + 140 + (k % 3) * 60, k * 130 + 70, GROUND + 165 + (k % 3) * 60), fill=(196, 140, 96))
    ground_bg = ground_bg.convert("RGB")
    kame = kame_house()
    eimg = earth(330)
    e_small = earth(90)
    moon = moon_sprite(250)
    sun = sun_sprite(430)
    planet = planet_sprite(210)
    sp1, sp2 = space_bg(2), space_bg(5, nebula=(60, 20, 80))
    explo = list(vfxgen.frames("explosion", 560, (255, 210, 80)))
    ring = list(vfxgen.frames("ring", 800, (255, 240, 180)))
    rnd = random.Random(9)
    results = [None] * len(FORMS)
    debris = []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        ri = min(len(FORMS) - 1, int(t // RD))
        u = t - ri * RD
        ending = t >= RD * len(FORMS)
        short, long_, hair, aura, km, scene, label = FORMS[ri]
        dist_txt = ""
        sh = 0
        if not ending and u < T_CUT:
            # ------------------------------------------------ Goku + la balle
            img = ground_bg.copy()
            if u < T_PUNCH:
                pose = dict(gp.IDLE)
                pose[53] += 2 * math.sin(t * 5)
                gx_ = GX
            elif u < T_HITL:
                k = (u - T_PUNCH) / (T_HITL - T_PUNCH)
                pose = pose_at(T_CHARGE + k * (T_HIT - T_CHARGE))
                gx_ = GX + DASH * ease((k - 0.85) / 0.15)
            else:
                pose, gx_ = gp.PUNCH, GX + DASH
            hc = hair

            def cm(i, c, hc=hc):
                return hc + (255,) if c[:3] in gp.HAIR_COLORS else c
            pim, pos, org = sn.render(fig, scale=GSC, absolute=pose, color_map=cm)
            bottom = np.nonzero(np.asarray(pim)[..., 3].max(1) > 0)[0].max()
            px, py = int(gx_ - org[0]), int(GROUND - bottom)
            power = (0.45 if u < T_PUNCH else min(1.0, 0.45 + (u - T_PUNCH))) if aura else 0
            if aura and power > 0:
                au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ad = ImageDraw.Draw(au)
                ch_ = (GROUND - py) * 0.62
                lite = tuple(min(255, v + 90) for v in aura)
                for scl, col, al in ((1.25, aura, 150), (1.0, lite, 180), (0.7, (255, 255, 240), 150)):
                    ad.polygon(rig.aura_poly(gx_, GROUND - ch_ * 0.95, (115 + 30 * power) * scl, ch_ * scl, t * 1.3 + scl,
                                             n=30, seed=int(scl * 10)), fill=col + (int(al * power),))
                g_ = au.filter(ImageFilter.GaussianBlur(16))
                img.paste(g_, (0, 0), g_)
                img.paste(au, (0, 0), au)
            img.paste(pim, (px, py), pim)
            # la balle : déjà posée à la 1re manche, tombe du ciel ensuite
            if u < T_HITL + 0.15:
                if ri == 0:
                    by = BY
                else:
                    k = min(1.0, u / 0.45)
                    by = -200 + (BY + 200) * k * k
                    if k >= 1:
                        by = BY - abs(math.sin((u - 0.45) * 9)) * 40 * max(0, 1 - (u - 0.45) / 0.5)
                rb = ball.rotate(-u * 60, resample=Image.BICUBIC)
                d = ImageDraw.Draw(img, "RGBA")
                d.ellipse((BX - BALL_R, GROUND - 14, BX + BALL_R, GROUND + 14), fill=(0, 0, 0, 60))
                img.paste(rb, (int(BX - rb.width / 2), int(by - rb.height / 2)), rb)
            else:
                a_ = u - T_HITL - 0.15
                bx = BX + 5200 * a_ * a_ + 900 * a_
                rb = ball.rotate(-a_ * 2000, resample=Image.BICUBIC)
                img.paste(rb, (int(bx - rb.width / 2), int(BY - 300 * a_ - rb.height / 2)), rb)
            d = ImageDraw.Draw(img, "RGBA")
            # transformation : flash + bannière au début de la manche
            if ri > 0 and u < 0.35:
                d.rectangle((0, 0, W, H), fill=hair + (int(220 * (1 - u / 0.35)),))
                sh = 14
            ee = u - T_HITL
            if 0 <= ee < 0.15:                                        # image figée à 2 tons
                g = img.convert("L").point(lambda v: 255 if v > 95 else 0)
                tint = aura or (255, 230, 120)
                img = Image.merge("RGB", tuple(g.point(lambda v, c=c: v * c / 255) for c in tint))
                if ee < 1 / FPS:
                    for _ in range(26):
                        debris.append([fist_x + rnd.uniform(-30, 30), GROUND - 8, rnd.uniform(-200, 900),
                                       -rnd.uniform(300, 1100), t, rnd.uniform(8, 17), 1.6])
            elif 0.15 <= ee < 0.6:
                k = (ee - 0.15) / 0.45
                ex = explo[min(len(explo) - 1, int(k * len(explo)))]
                img.paste(ex, (int(fist_x - ex.width / 2), int(fist_y - ex.height / 2)), ex)
                rr = ring[min(len(ring) - 1, int(k * len(ring)))]
                img.paste(rr, (int(fist_x - rr.width / 2), int(fist_y - rr.height / 2)), rr)
                sh = 26 * (1 - k)
            d = ImageDraw.Draw(img, "RGBA")
            keep = []
            for db in debris:
                a = t - db[4]
                if a < db[6]:
                    x, y = db[0] + db[2] * a, db[1] + db[3] * a + 1100 * a * a
                    if y < GROUND + 4:
                        s = db[5]
                        d.polygon([(x - s, y), (x - s * .3, y - s), (x + s, y - s * .4), (x + s * .6, y + s * .7)],
                                  fill=(110, 85, 60))
                        keep.append(db)
            debris[:] = keep
            if u < 1.6:                                               # nom de la forme
                s_ = 1 + 0.35 * max(0.0, 1 - u / 0.15)
                img = hud.label(img, (W / 2, 640), long_, int(84 * s_), fill=hair if ri else (255, 255, 255), angle=-3)
            if T_CUT - 0.12 <= u:
                d = ImageDraw.Draw(img, "RGBA")
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(255 * (u - (T_CUT - 0.12)) / 0.12)))
            dist_txt = fmt(0.0) if u < T_HITL else fmt((km or 99999) * 0.0001 * (u - T_HITL))
        elif not ending:
            # ------------------------------------------------ voyage de la balle
            k = min(1.0, (u - T_CUT) / (T_RES - T_CUT))
            ke = ease(k)
            if scene == "kame":
                img = ground_bg.copy()
                d = ImageDraw.Draw(img, "RGBA")
                d.rectangle((0, 1180, W, H), fill=(40, 120, 210))
                for j in range(12):
                    x = (j * 160 - k * 900) % (W + 160) - 80
                    d.arc((x, 1260 + (j % 3) * 70, x + 110, 1300 + (j % 3) * 70), 200, 340, fill=(170, 215, 255), width=4)
                img.paste(kame, (620, 1180 - 300), kame)
                land = 0.8
                kk = min(1.0, k / land)
                bx, by = -60 + (560 + 60) * kk, 1240 - 900 * math.sin(math.pi * kk) * (1 - kk * 0.3)
                if k < land:
                    rb = ball_s.rotate(-k * 900, resample=Image.BICUBIC)
                    img.paste(rb, (int(bx - rb.width / 2), int(by - rb.height / 2)), rb)
                else:
                    a_ = (k - land) / (1 - land)
                    for j in range(7):
                        an = math.pi + j * math.pi / 6
                        d.ellipse((560 + math.cos(an) * 90 * a_ - 16, 1240 + math.sin(an) * 160 * a_ - 16,
                                   560 + math.cos(an) * 90 * a_ + 16, 1240 + math.sin(an) * 160 * a_ + 16),
                                  fill=(230, 245, 255, int(255 * (1 - a_ * 0.7))))
                cur = km * min(1.0, k / land)
            elif scene == "earth":
                img = sp1.copy()
                ec = (W / 2, H * 0.58)
                img.paste(eimg, (int(ec[0] - eimg.width / 2), int(ec[1] - eimg.height / 2)), eimg)
                d = ImageDraw.Draw(img, "RGBA")
                for j in range(40):
                    kj = max(0.0, ke - j * 0.006)
                    ang = math.radians(200 - 360 * kj)
                    x, y = ec[0] + math.cos(ang) * 410, ec[1] - math.sin(ang) * 410
                    a_ = 1 - j / 40
                    d.ellipse((x - 12 * a_, y - 12 * a_, x + 12 * a_, y + 12 * a_), fill=(255, 210, 60, int(230 * a_)))
                ang = math.radians(200 - 360 * ke)
                x, y = ec[0] + math.cos(ang) * 410, ec[1] - math.sin(ang) * 410
                img.paste(ball_s, (int(x - ball_s.width / 2), int(y - ball_s.height / 2)), ball_s)
                cur = km * ke
            elif scene in ("moon", "sun", "beerus"):
                img = (sp2 if scene == "beerus" else sp1).copy()
                hitk = 0.7
                if scene == "moon":
                    img.paste(e_small, (60, 1250), e_small)
                    tx, ty, spr = 760, 860, moon
                elif scene == "sun":
                    img.paste(e_small, (40, 1500), e_small)
                    img.paste(moon_sprite(40), (230, 1380), moon_sprite(40))
                    tx, ty, spr = 840, 820, sun
                else:
                    tx, ty, spr = 640, 1200, planet
                img.paste(spr, (int(tx - spr.width / 2), int(ty - spr.height / 2)), spr)
                d = ImageDraw.Draw(img, "RGBA")
                sx0, sy0 = 150, 1450
                kk = min(1.0, k / hitk)
                bx, by = sx0 + (tx - sx0) * ease(kk), sy0 + (ty - sy0) * ease(kk)
                if k < hitk:
                    for j in range(16):
                        q = max(0.0, ease(kk) - j * 0.012)
                        x, y = sx0 + (tx - sx0) * q, sy0 + (ty - sy0) * q
                        a_ = 1 - j / 16
                        d.ellipse((x - 14 * a_, y - 14 * a_, x + 14 * a_, y + 14 * a_), fill=aura + (int(220 * a_),))
                    img.paste(ball_s, (int(bx - ball_s.width / 2), int(by - ball_s.height / 2)), ball_s)
                else:
                    a_ = (k - hitk) / (1 - hitk)
                    ix, iy = tx - (tx - sx0) * 0.25 * (210 if scene != "sun" else 300) / math.hypot(tx - sx0, ty - sy0), \
                        ty - (ty - sy0) * 0.25 * (210 if scene != "sun" else 300) / math.hypot(tx - sx0, ty - sy0)
                    if scene == "moon":
                        d.ellipse((ix - 70, iy - 50, ix + 70, iy + 50), fill=(120, 120, 115))
                        d.ellipse((ix - 50, iy - 34, ix + 50, iy + 34), fill=(90, 90, 88))
                    if a_ < 0.6:
                        ex = explo[min(len(explo) - 1, int(a_ / 0.6 * len(explo)))]
                        img.paste(ex, (int(ix - ex.width / 2), int(iy - ex.height / 2)), ex)
                        sh = 18 * (1 - a_ / 0.6)
                    d = ImageDraw.Draw(img, "RGBA")
                    if scene == "sun" and a_ < 0.3:
                        d.rectangle((0, 0, W, H), fill=(255, 220, 150, int(220 * (1 - a_ / 0.3))))
                    if scene == "beerus" and a_ > 0.25:                # Beerus se réveille
                        b_ = min(1.0, (a_ - 0.25) / 0.2)
                        bw = bim.resize((int(bim.width * b_ + 1), int(bim.height * b_ + 1)))
                        img.paste(bw, (int(tx + 110 - bw.width / 2), int(ty - 185 - bw.height)), bw)
                        if a_ > 0.4:
                            d = ImageDraw.Draw(img, "RGBA")
                            bx2, by2 = 330, 600
                            d.rounded_rectangle((bx2 - 290, by2 - 66, bx2 + 290, by2 + 66), 30, fill=(255, 255, 255, 245),
                                                outline=(30, 10, 40), width=6)
                            d.polygon([(bx2 + 200, by2 + 40), (bx2 + 330, by2 + 90), (bx2 + 250, by2 + 10)], fill=(255, 255, 255))
                            d.text((bx2, by2), "WHO DID THAT?!", font=hud.font("luckiest-guy.woff2", 64),
                                   fill=(150, 40, 200), anchor="mm")
                cur = None if scene == "beerus" else km * min(1.0, k / hitk) ** 2
            dist_txt = fmt(cur) if cur is not None else ("".join(rnd.choice("0123456789") for _ in range(7)) + " KM"
                                                         if k < 0.7 else "???")
            if u < T_CUT + 0.15:
                d = ImageDraw.Draw(img, "RGBA")
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(255 * (1 - (u - T_CUT) / 0.15))))
            if u >= T_RES - 0.05:                                     # résultat
                results[ri] = km
                a_ = u - (T_RES - 0.05)
                s_ = 1 + 0.4 * max(0.0, 1 - a_ / 0.15)
                img = hud.label(img, (W / 2, 1490 if scene == "beerus" else 640), label, int(86 * s_), fill=hair if ri else (255, 255, 255), angle=3)
        else:
            img = sp2.copy()
        # ------------------------------------------------ titre, distance, classement
        base = img.convert("RGBA")
        L = Image.new("RGBA", base.size, (0, 0, 0, 0))
        hud.text3d(L, (W / 2, 110), "EVERY GOKU FORM", hud.font("luckiest-guy.woff2", 104), (255, 255, 255),
                   side=(30, 60, 140), depth=10, outline=(20, 20, 50), ow=6)
        hud.text3d(L, (W / 2, 215), "HITS THE BALL", hud.font("luckiest-guy.woff2", 84), (255, 214, 50),
                   side=(150, 70, 10), depth=8, outline=(40, 15, 5), ow=5)
        L = L.rotate(2, resample=Image.BICUBIC, center=(W / 2, 160))
        base.alpha_composite(L)
        d = ImageDraw.Draw(base)
        if not ending:
            d.rounded_rectangle((W / 2 - 260, 300, W / 2 + 260, 420), 36, fill=(20, 22, 40, 225), outline=(255, 255, 255), width=5)
            d.text((W / 2, 362), dist_txt, font=hud.font("luckiest-guy.woff2", 70), fill=hair if ri else (255, 255, 255),
                   anchor="mm")
        # classement (5 cartes en bas)
        cw = (W - 80) / len(FORMS)
        y0 = 1560 if not ending else 900
        for j, f in enumerate(FORMS):
            x0 = 40 + j * cw
            cur_card = (j == ri and not ending)
            col = f[2] if j else (235, 235, 240)
            d.rounded_rectangle((x0 + 6, y0, x0 + cw - 6, y0 + 170), 22,
                                fill=(20, 22, 40, 235), outline=col if cur_card or ending else (90, 90, 110), width=6 if cur_card else 3)
            d.ellipse((x0 + cw / 2 - 22, y0 + 18, x0 + cw / 2 + 22, y0 + 62), fill=col, outline=(255, 255, 255), width=3)
            d.text((x0 + cw / 2, y0 + 92), f[0], font=hud.font("luckiest-guy.woff2", 36), fill=(255, 255, 255), anchor="mm")
            val = fmt(f[4]) if (results[j] is not None or (j == 4 and ri == 4 and u >= T_RES - 0.05) or ending) else "—"
            if j == 4 and (ending or (ri == 4 and u >= T_RES)):
                val = "???"
            d.text((x0 + cw / 2, y0 + 138), val, font=hud.font("luckiest-guy.woff2", 26 if len(val) > 8 else 32),
                   fill=col, anchor="mm")
        if ending:
            a_ = t - RD * len(FORMS)
            s_ = 1 + 0.3 * max(0.0, 1 - a_ / 0.15)
            img = hud.label(base.convert("RGB"), (W / 2, 640), "WHO'S NEXT?", int(110 * s_), fill=(255, 214, 50), angle=-3)
            rgba = img.convert("RGBA")
            render.draw_rich(rgba, (W / 2, 1140), "Which form should hit it next? 👇", hud.font("luckiest-guy.woff2", 52),
                             (255, 255, 255), anchor="ma", stroke_width=5, stroke_fill=(20, 20, 50))
            img = rgba.convert("RGB")
        else:
            img = base.convert("RGB")
        if sh:
            dx, dy = rnd.randint(-int(sh), int(sh)), rnd.randint(-int(sh), int(sh))
            bgf = Image.new("RGB", (W, H), (0, 0, 0))
            bgf.paste(img, (dx, dy))
            img = bgf
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()
    # ------------------------------------------------ son
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
    S = lambda fam, seed=0: domain.sfx(fam, mode="anime", seed=seed, franchise="dragon ball")  # noqa: E731
    for ri in range(len(FORMS)):
        t0 = ri * RD
        if ri:
            put(t0, S("transform", ri), 0.8)
        put(t0 + T_PUNCH + 0.9, S("teleport", ri), 0.4)
        put(t0 + T_HITL, S("hit", ri), 1.0)
        put(t0 + T_HITL + 0.15, S("bomb", ri), 0.9)
        put(t0 + T_CUT, S("beam", ri), 0.4)
        put(t0 + T_CUT + (T_RES - T_CUT) * 0.7, S("ko", ri), 0.7)
        put(t0 + T_RES, S("hit", 10 + ri), 0.5)
    put(RD * len(FORMS), S("ko", 9), 0.6)
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
