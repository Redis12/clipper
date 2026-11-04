"""Domain War #6 — Luffy vs Kaido, v4 (retours de l'utilisateur, 04/11 1h18) :
Luffy = ICÔNE (base → Gear 4 → Gear 5) avec bras élastiques ; Kaido = sprites (humain → hybride → dragon) ;
Zoro = sprite MUGEN qui vient aider ; voix du jeu MUGEN (Luffy, Zoro) ; les poings passent DEVANT Kaido.

python tools/pixel/luffy_vs_kaido_v4.py <sortie.mp4>
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import luffy_vs_kaido as base  # noqa: E402
from luffy_vs_kaido import (W, H, FPS, LIB, KS, SFX, TITLE, GX0, GY0, CELL, NX, NY, scale, paste_c, whiten,  # noqa: E402
                            finish, lerp, smooth, render, vfxgen, Fight, cine_frames)
from clipper.slides import faces  # noqa: E402

LX, LY = 270, 1000          # centre de l'icône de Luffy
KX0, KY0 = 790, 980         # Kaido
FUS = LIB / "_fusion/Luffy"

# ------------------------------------------------------------------ timeline (s)
T_FIGHT = 1.6
T_PISTOL = 2.0
T_TRANS = 2.9            # Kaido : humain → hybride (3,2) → dragon (3,7)
T_BREATH1 = 4.4
T_GAT = 5.9
T_BAGUA = 7.5
T_G4 = 8.7               # Luffy passe en Gear 4
T_KKG = 9.4
T_FLY = 11.0
T_BREATH2 = 12.3
T_DOWN = 14.3
T_DRUMS = 15.4
T_CINE = 21.0
T_G5 = 27.0
T_WHIP = 27.8
T_BOLT2 = 29.6
T_GRAB = 30.5
T_ZORO = 31.8
T_SANZEN = 33.4
T_GIANT = 35.4
T_BAJRANG = 37.8
T_WIN = 42.4
DUR = 44.2

KEYS = [(0, .5), (T_PISTOL + .2, .55), (T_BREATH1 + .5, .55), (T_BREATH1 + 1.4, .44), (T_GAT + 1.3, .52),
        (T_BAGUA + 1.0, .42), (T_KKG + .9, .42), (T_KKG + 1.4, .56), (T_FLY + 1.2, .45), (T_BREATH2 + 1.9, .2),
        (T_DOWN + .5, .08), (T_G5 + .4, .08), (T_WHIP + .9, .2), (T_BOLT2 + .8, .14), (T_GRAB + .9, .26),
        (T_SANZEN + 1.0, .4), (T_GIANT + 1.4, .6), (T_BAJRANG + 1.6, .66), (T_BAJRANG + 2.4, 1.0), (DUR, 1.0)]
HITS_K = [(T_PISTOL + .2, 1.0)] + [(T_GAT + .1 + i * .08, .35) for i in range(15)] + [
    (T_KKG + 1.0, 2.2), (T_WHIP + .5, 1.8), (T_GRAB + .7, 1.6), (T_SANZEN + .55, 2.0), (T_GIANT + .45, 1.4),
    (T_GIANT + 1.0, 1.6), (T_BAJRANG + 1.5, 3.0)]
HITS_L = [(T_BREATH1 + .6, 1.0), (T_BAGUA + .3, 1.0), (T_BREATH2 + .7, 1.3), (T_BREATH2 + 1.4, 1.8),
          (T_BOLT2 + .4, .8)]
DMG = {T_PISTOL + .2: ("K", "-5%"), T_KKG + 1.0: ("K", "-14%"), T_WHIP + .5: ("K", "-12%"), T_GRAB + .7: ("K", "-6%"),
       T_SANZEN + .55: ("K", "-14%"), T_GIANT + .45: ("K", "-10%"), T_GIANT + 1.0: ("K", "-10%"),
       T_BAJRANG + 1.5: ("K", "-34%"), T_BREATH1 + .6: ("L", "-11%"), T_BAGUA + .3: ("L", "-10%"),
       T_BREATH2 + .7: ("L", "-14%"), T_BREATH2 + 1.4: ("L", "-12%")}


def recent(hits, t, win=0.5):
    best = None
    for th, f in hits:
        if 0 <= t - th < win:
            best = (t - th, f)
    return best


def ease_punch(a, out=0.16, hold=0.10, back=0.18):
    if a < 0 or a > out + hold + back:
        return None
    if a < out:
        return 1 - (1 - a / out) ** 3, False
    if a < out + hold:
        return 1.0, True
    return 1 - ((a - out - hold) / back) ** 2, False


# ------------------------------------------------------------------ assets

def icon(path: Path, size=190, ring=(230, 60, 60)) -> Image.Image:
    im = Image.open(path).convert("RGB")
    sq = faces.head_square(im, path).resize((size, size), Image.LANCZOS).convert("RGBA")
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    sq.putalpha(m)
    out = Image.new("RGBA", (size + 24, size + 24), (0, 0, 0, 0))
    ImageDraw.Draw(out).ellipse((0, 0, size + 23, size + 23), fill=ring + (255,))
    out.alpha_composite(sq, (12, 12))
    return out


def load():
    S = base.load_sprites()
    S["ic_base"] = icon(FUS / "2 Base Luffy.jpg")
    S["ic_g4"] = icon(FUS / "4 Gear 4 BoundMan.jpg", ring=(160, 20, 30))
    S["ic_g5"] = icon(FUS / "6 Gear 5.jpg", ring=(255, 255, 255))
    S["ic_dead"] = S["ic_base"].convert("LA").convert("RGBA")
    k = KS
    S["k_human"] = scale(Image.open(k / "kaido_human.png").convert("RGBA"), 3.6)
    S["k_hybrid"] = scale(Image.open(k / "kaido_hybrid.png").convert("RGBA"), 3.4)
    S["k_human"] = ImageOps.mirror(S["k_human"])
    S["k_hybrid"] = ImageOps.mirror(S["k_hybrid"])
    S["fist_white"] = whiten(S["kkg"]).copy()
    S["bajrang"] = scale(S["kkg"], 2.3)
    return S


# ------------------------------------------------------------------ sons

def sounds(S):
    out = []
    s = lambda t, n, v=1.0: out.append((t, SFX / n, v))
    tmp = Path("/tmp/mugen_snd")
    tmp.mkdir(exist_ok=True)

    def m(ch, key, t, g, n, v=1.0):
        w = S[ch].sounds.get((g, n))
        if w:
            f = tmp / f"{key}_{g}_{n}.wav"
            f.write_bytes(w)
            out.append((t, f, v))
    s(0.1, "Whoosh hit.mp3"); s(0.33, "big punch.mp3", 0.7)
    m("mL", "L", T_PISTOL - .1, 0, 9, 1.2); s(T_PISTOL, "luffys arm stretch.mp3"); s(T_PISTOL + .2, "fist.mp3")
    s(T_TRANS, "Terror.mp3", 0.9); s(T_TRANS + .8, "Big explosion.mp3", 0.6)
    s(T_BREATH1 + .3, "explosion with debris.mp3", 0.8)
    m("mL", "L", T_GAT - .1, 0, 3, 1.2); s(T_GAT, "consecutive attacks.mp3")
    s(T_BAGUA, "explosion.mp3", 0.8)
    s(T_G4, "Armament Haki (Busoshoku Haki ) v1.mp3"); m("mL", "L", T_G4 + .2, 4, 18)
    m("mL", "L", T_KKG, 0, 11, 1.2); m("mL", "L", T_KKG + .3, 4, 21); s(T_KKG + .95, "big punch.mp3")
    s(T_KKG + 1.0, "Big explosion.mp3", 0.8)
    s(T_FLY, "Terror.mp3", 0.5)
    s(T_BREATH2 + .6, "explosion with debris.mp3"); s(T_BREATH2 + 1.3, "explosion with debris.mp3")
    s(T_DOWN, "at death's door.mp3")
    out.append((T_DRUMS, LIB / "_sounds/domain/Gear 5 drums.mp3", 1.1))
    s(T_G5 - .4, "conqueror's haki (Haoshoku Haki) v2.mp3", 0.8)
    m("mL", "L", T_WHIP, 0, 12, 1.2); s(T_WHIP + .5, "big punch.mp3")
    s(T_BOLT2, "explosion with debris.mp3", 0.7); s(T_GRAB + .2, "WTF sound v3 (most popular).mp3", 0.8)
    s(T_ZORO, "Zoro's run gait.mp3", 0.8)
    m("mZ", "Z", T_SANZEN - .2, 0, 3, 1.3); s(T_SANZEN + .5, "big sword cutting.mp3")
    m("mL", "L", T_GIANT, 0, 13, 1.2); s(T_GIANT + .45, "big punch.mp3"); s(T_GIANT + 1.0, "Big explosion.mp3", 0.6)
    s(T_BAJRANG, "conqueror's Haki (Haoshoku Haki) v1.mp3", 0.6); m("mL", "L", T_BAJRANG + .2, 0, 17, 1.2)
    s(T_BAJRANG + 1.5, "big punch.mp3"); s(T_BAJRANG + 1.6, "Big explosion.mp3"); s(T_BAJRANG + 2.0, "explosion with debris.mp3")
    return out


# ------------------------------------------------------------------ rendu

def kaido_pose(S, t):
    """Sprite de Kaido + position (x, y centre) selon le moment."""
    bob = math.sin(t * 3) * 18
    if t < T_TRANS + .3:
        im = S["k_human"]
        sq = 1 + 0.02 * math.sin(t * 5)                       # respiration
        return im.resize((im.width, int(im.height * sq)), Image.NEAREST), KX0, KY0 + 30
    if t < T_TRANS + .8:
        return S["k_hybrid"], KX0, KY0 + 20
    if T_BREATH1 <= t < T_BREATH1 + 1.5 or T_BREATH2 <= t < T_BREATH2 + 2.0:
        a = t - (T_BREATH1 if t < T_BREATH2 else T_BREATH2)
        fr = S["k_breath"][min(4, int(a / .45 * 5))] if a < .45 else S["k_breath"][5 + int(a * 12) % 4]
        return fr, KX0 - (fr.width - S["k_breath"][0].width) / 2, KY0 + bob
    if T_FLY <= t < T_BREATH2:
        a = t - T_FLY
        fr = S["k_fly"][int(a * 10) % len(S["k_fly"])]
        w = smooth(a / .45) * smooth((T_BREATH2 - t) / .45)
        return fr, lerp(KX0, 540 + math.cos(a * 2.2 + 1.0) * 270, w), lerp(KY0, 980 + math.sin(a * 2.6) * 330, w)
    return S["k_idle"][int(t * 8) % len(S["k_idle"])], KX0, KY0 + bob


def render_frame(F, S, t, cine):
    energy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shake = 0
    if t < T_FIGHT:                                              # accroche
        img = Image.new("RGBA", (W, H), (12, 10, 22, 255))
        d = ImageDraw.Draw(img)
        d.polygon(((0, 0), (W * .62, 0), (W * .38, H), (0, H)), fill=(120, 24, 24))
        d.polygon(((W * .62, 0), (W, 0), (W, H), (W * .38, H)), fill=(54, 28, 96))
        a = smooth(t / .3)
        paste_c(img, scale(S["ic_base"], 1.4), 270 - (1 - a) * 300, 980)
        paste_c(img, scale(S["k_human"], 1.15), 790 + (1 - a) * 300, 960)
        d = ImageDraw.Draw(img)
        d.text((W / 2, 140), TITLE, font=F.mid, anchor="mm", fill=(255, 255, 255), stroke_width=6, stroke_fill=(0, 0, 0))
        d.text((W / 2, 300), "WHO WINS?", font=F.big, anchor="mm", fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0))
        d.text((W / 2, 980), "VS", font=render.font(200), anchor="mm", fill=(255, 215, 40), stroke_width=12, stroke_fill=(0, 0, 0))
        d.text((270, 1230), "LUFFY", font=F.mid, anchor="mm", fill=(255, 140, 140), stroke_width=7, stroke_fill=(0, 0, 0))
        d.text((790, 1230), "KAIDO", font=F.mid, anchor="mm", fill=(200, 170, 255), stroke_width=7, stroke_fill=(0, 0, 0))
        render.draw_rich(img, (W / 2, 1420), "Comment your pick 👇", render.font(62), (255, 255, 255), anchor="ma",
                         stroke_width=5, stroke_fill=(0, 0, 0))
        render.like_follow(img, W / 2, 1540, min(1.0, t / .4))
        return finish(img, energy, 14 if t < .12 else 0, t)
    if T_CINE <= t < T_G5:                                       # cinématique Gear 5
        img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        fr = cine[min(len(cine) - 1, int((t - T_CINE) * 24))]
        band = fr.resize((W, int(fr.height * W / fr.width)), Image.LANCZOS)
        img.alpha_composite(band, (0, int(H * .42 - band.height / 2)))
        d = ImageDraw.Draw(img)
        d.text((W / 2, H * .42 + band.height / 2 + 120), "GEAR 5", font=render.font(160), anchor="mm",
               fill=(255, 255, 255), stroke_width=10, stroke_fill=(0, 0, 0))
        if t < T_CINE + .15 or T_G5 - .15 < t:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, 220)))
        return finish(img, energy, 0, t)
    if t >= T_WIN:
        return winner(F, S, t)

    img = Image.new("RGBA", (W, H), (12, 10, 22, 255))
    dark = min(.78, (t - T_DOWN) / 1.0 * .78) if T_DOWN <= t < T_CINE else 0
    F.grid(img, t, dark)
    F.header(img)
    front = Image.new("RGBA", (W, H), (0, 0, 0, 0))             # bras, poings, Zoro : DEVANT Kaido
    lab = None
    gear5 = t >= T_G5
    hk, hl = recent(HITS_K, t, .5), recent(HITS_L, t, .5)
    kpose, kx, ky = kaido_pose(S, t)
    kx += 50 * hk[1] * math.exp(-hk[0] * 7) * (1 - math.exp(-hk[0] * 40)) if hk else 0
    lunge = 0                                                    # Luffy avance quand il frappe
    ic = S["ic_g5"] if gear5 else (S["ic_g4"] if T_G4 + .3 <= t < T_DOWN else S["ic_base"])
    LYc = LY + math.sin(t * 4) * 10
    hx, hy = kx - 170, ky - 10                                   # point d'impact sur Kaido

    def arm(q, ty, thick=1.0, wob=1.0, fist=None, tt=0):
        x1, y1 = LX + 90 + lunge, LYc
        x2, y2 = lerp(x1, hx, q), lerp(y1, ty, q)
        if fist is None:
            F.arm(front, x1, y1, x2, y2, t + tt, thick=thick, wob=wob)
        else:
            F.arm(front, x1, y1, x2 - fist.width * .35, y2, t + tt, thick=thick, wob=wob)
            paste_c(front, fist, x2, y2)

    # ---- Luffy
    e = ease_punch(t - T_PISTOL)
    if e:
        lunge = 30 * e[0]
        arm(e[0], hy)
        if e[1]:
            paste_c(energy, F.hit[int((t - T_PISTOL) * 30) % 10], hx, hy)
            shake = 12
        lab = ("LUFFY", "JET PISTOL", (255, 150, 150))
    if T_GAT <= t < T_GAT + 1.4:
        r2 = random.Random(7)
        lunge = 40
        for i in range(15):
            e = ease_punch(t - (T_GAT + i * .08), .07, .04, .09)
            ty = hy + r2.uniform(-120, 120)
            if e:
                arm(e[0], ty, .85, .4, tt=i)
                if e[1]:
                    paste_c(energy, F.hit[i % 10].resize((120, 120)), hx, ty)
                    shake = 6
        lab = ("LUFFY", "JET GATLING", (255, 150, 150))
    if T_G4 <= t < T_KKG:
        a = t - T_G4
        if a < .4:
            paste_c(energy, F.ring[min(9, int(a * 24))].resize((520, 520)), LX, LYc)
        lab = ("LUFFY", "GEAR 4 · BOUNDMAN", (255, 150, 150))
    if T_KKG <= t < T_KKG + 1.6:
        a = t - T_KKG
        lab = ("LUFFY", "KING KONG GUN", (255, 150, 150))
        if a < .7:                                              # le poing gonfle au-dessus de Luffy
            paste_c(front, scale(S["kkg"], .35 + .65 * smooth(a / .7)), LX + 40, LYc - 230)
            if int(a * 20) % 2 == 0:
                paste_c(energy, F.bolt_red[int(a * 24) % 10].resize((320, 320)), LX + 40, LYc - 230, .9)
        elif a < 1.0:
            q = smooth((a - .7) / .3)
            arm(q, hy, 2.0, .2, S["kkg"])
            paste_c(energy, F.bolt_red[int(a * 24) % 10].resize((380, 380)), lerp(LX, hx, q), hy, .8)
        else:
            b = a - 1.0
            if b < .3:
                arm(1.0 - b, hy, 2.0, .2, S["kkg"])
            paste_c(energy, F.expl[min(9, int(b * 16))].resize((640, 640)), hx + 60, hy)
            paste_c(energy, F.bolt_red[int(b * 24) % 10].resize((520, 520)), hx + 60, hy, max(0, 1 - b))
            shake = int(30 * max(0, 1 - b / .7))
    if gear5:
        if t < T_G5 + .6:
            paste_c(energy, F.ring[min(9, int((t - T_G5) * 18))].resize((700, 700)), LX, LYc)
            F.label(img, "LUFFY", "GEAR 5", (255, 255, 255), big=True, age=t - T_G5)
        e = ease_punch(t - T_WHIP - .2, .25, .2, .3)
        if T_WHIP <= t < T_WHIP + 1.2:
            lab = ("LUFFY", "GOMU GOMU NO DAWN WHIP", (255, 255, 255))
            if e:
                arm(e[0], hy, 1.6, 2.0, S["fist_white"])
                if e[1]:
                    paste_c(energy, F.hit[int(t * 30) % 10].resize((300, 300)), hx, hy)
                    shake = 14
        if T_BOLT2 <= t < T_GRAB:
            lab = ("KAIDO", "THUNDER BAGUA", (200, 170, 255))
            for k in range(2):
                b_ = S["k_bolt"][(int(t * 14) + k) % 7]
                paste_c(energy, b_, LX - 40 + k * 90, 300 + b_.height / 2)
        if T_GRAB <= t < T_GRAB + 1.2:                          # il attrape la foudre et la renvoie
            a = t - T_GRAB
            lab = ("LUFFY", "GRABS THE LIGHTNING!", (255, 255, 255))
            b_ = S["k_bolt"][int(t * 14) % 7]
            q = smooth((a - .4) / .3)
            bx, by = lerp(LX, hx, q), lerp(LYc - 200, hy, q)
            paste_c(energy, b_.rotate(-70 * q, expand=True), bx, by)
            if a > .7:
                paste_c(energy, F.expl[int(a * 24) % 10].resize((300, 300)), hx, hy)
                shake = 10
        if T_GIANT <= t < T_GIANT + 1.8:
            a = t - T_GIANT
            lab = ("LUFFY", "GOMU GOMU NO GIANT", (255, 255, 255))
            for k, t0 in enumerate((0, .55)):
                e = ease_punch(a - t0, .25, .2, .3)
                if e:
                    arm(e[0], hy + (-90 if k == 0 else 90), 2.4, .3, S["fist_white"], tt=k)
                    if e[1]:
                        paste_c(energy, F.expl[int(a * 24) % 10].resize((380, 380)), hx, hy)
                        shake = 12
        if T_BAJRANG <= t:
            a = t - T_BAJRANG
            F.label(img, "LUFFY", "BAJRANG GUN", (255, 255, 255), big=a < 1.2, age=a)
            fist = S["bajrang"]
            if a < 1.5:                                         # le poing géant gonfle derrière lui
                g = scale(fist, .3 + .7 * smooth(a / 1.4))
                paste_c(front, g, LX + 60 + 80 * smooth(a / 1.4), LYc - 260)
                shake = int(4 + 8 * a)
            elif a < 1.9:
                q = smooth((a - 1.5) / .4)
                arm(q, hy, 3.2, .1, fist)
            else:
                b = a - 1.9
                if b < .5:
                    arm(1.0, hy, 3.2, .1, fist)
                paste_c(energy, F.expl[min(9, int(b * 12))].resize((950, 950)), hx + 80, hy)
                paste_c(energy, F.bolt_red[int(b * 24) % 10].resize((700, 700)), hx + 80, hy, max(0, 1 - b))
                shake = int(36 * max(0, 1 - b))
                if b > .5:
                    kpose = None
            if a > 2.2:
                pop = 1 + .4 * max(0, 1 - (a - 2.2) / .2)
                ImageDraw.Draw(front).text((W / 2, 1150), "FINISH!", font=render.font(int(190 * pop)), anchor="mm",
                                           fill=(255, 225, 60), stroke_width=12, stroke_fill=(0, 0, 0))
    # ---- Kaido
    if T_TRANS <= t < T_TRANS + 1.0:
        a = t - T_TRANS
        lab = ("KAIDO", "TRANSFORMS!", (200, 170, 255))
        if .3 < a < .45 or .8 < a < .95:
            paste_c(energy, F.ring[int(a * 30) % 10].resize((700, 700)), KX0, KY0)
            shake = 16
    if T_BREATH1 + .4 <= t < T_BREATH1 + 1.5 or T_BREATH2 + .5 <= t < T_BREATH2 + 2.0:
        a = t - (T_BREATH1 if t < T_BREATH2 else T_BREATH2)
        paste_c(energy, F.expl[int(a * 24) % 10].resize((420, 420)), LX + 20, LYc, .9)
        shake = max(shake, 10)
        lab = ("KAIDO", "BORO BREATH", (200, 170, 255))
    if T_BAGUA <= t < T_BAGUA + 1.0:
        lab = ("KAIDO", "THUNDER BAGUA", (200, 170, 255))
        for k in range(3):
            bx = LX - 110 + k * 110
            b_ = S["k_bolt"][(int(t * 14) + k) % 7]
            paste_c(energy, b_, bx, 300 + b_.height / 2)
            paste_c(energy, F.expl[int(t * 24 + k * 3) % 10].resize((170, 170)), bx, 300 + b_.height)
        shake = 10
    if T_FLY <= t < T_BREATH2:
        lab = ("KAIDO", "DRAGON TWISTER", (200, 170, 255))
    # ---- Zoro (sprite MUGEN) : perdu sous l'arène, puis Sanzen Sekai
    if T_ZORO <= t < T_SANZEN + 1.3:
        Z = S["mZ"]
        if t < T_SANZEN:
            a = t - T_ZORO
            x = W + 60 - a * 380
            yb = GY0 + NY * CELL + 330
            Z.draw(front, 20, a, x, yb, scale=1.5, facing=-1, loop=True)
            render.draw_rich(front, (x - 40, yb - 330), "Where am I? 🗺️", render.font(46), (255, 255, 255),
                             anchor="ma", stroke_width=4, stroke_fill=(0, 0, 0))
        else:
            b = t - T_SANZEN
            act, tb = (3200, b) if b < .57 else (3201, b - .57)
            Z.draw(front, act, tb, kx - 260, ky + 260, scale=1.8, facing=1, loop=False)
            if b > .45:
                for k, sp in enumerate(S["slash"][:3]):
                    paste_c(energy, scale(sp, .9), kx - 40 + k * 30, ky - 40 + k * 40, max(0, 1 - (b - .45) * .9))
                shake = 12
            lab = ("ZORO", "SANZEN SEKAI", (130, 230, 130))

    # ---- dessin : Kaido, puis bras/poings/Zoro devant, puis l'icône de Luffy
    if kpose is not None:
        if hk:
            kpose = kpose.rotate(9 * hk[1] * math.exp(-hk[0] * 6) * math.sin(hk[0] * 25), expand=True,
                                 resample=Image.NEAREST)
            if hk[0] < .08:
                kpose = whiten(kpose)
        paste_c(img, kpose, kx, ky)
    img.alpha_composite(front)
    if T_DOWN <= t < T_G5:
        ic_ = S["ic_dead"]
        drop = smooth((t - T_DOWN) / .4) * 60
        img2 = ic_.rotate(-75 * smooth((t - T_DOWN) / .4), expand=True)
        paste_c(img, img2, LX, LY + drop)
        d = ImageDraw.Draw(img)
        if t < T_DRUMS:
            d.text((W / 2, 760), "LUFFY IS DOWN...", font=F.mid, anchor="mm", fill=(255, 255, 255), stroke_width=7,
                   stroke_fill=(0, 0, 0))
        else:
            a = t - T_DRUMS
            beat = (a % 1.08) / 1.08
            R = 140 + 240 * beat
            ImageDraw.Draw(energy).ellipse((LX - R, LY + 60 - R, LX + R, LY + 60 + R),
                                           outline=(255, 255, 255, int(220 * (1 - beat))), width=10)
            paste_c(img, scale(img2, 1 + .12 * (1 - beat)), LX, LY + drop)     # l'icône bat au rythme
            d.text((W / 2, 760), "DON DON DON...", font=F.mid, anchor="mm", fill=(255, 240, 200), stroke_width=7,
                   stroke_fill=(0, 0, 0))
    else:
        kxl = -int(40 * hl[1] * (1 - hl[0] / .5)) if hl else 0
        ii = whiten(ic) if hl and hl[0] < .08 else ic
        sc = 1 + .05 * math.sin(t * 6)
        paste_c(img, scale(ii, sc), LX + lunge + kxl, LYc)
    for th, (who, txt) in DMG.items():
        a_ = t - th
        if 0 <= a_ < .9:
            x_, y_ = (kx - 40, ky - 230) if who == "K" else (LX, LY - 200)
            ImageDraw.Draw(img).text((x_, y_ - a_ * 120), txt, font=render.font(int(70 * (1 + .3 * max(0, 1 - a_ / .15)))),
                                     anchor="mm", fill=(255, 70, 70) if who == "K" else (190, 150, 255),
                                     stroke_width=6, stroke_fill=(0, 0, 0))
    if lab and t < T_BAJRANG:
        F.label(img, *lab)
    if T_FIGHT <= t < T_FIGHT + .5:
        ImageDraw.Draw(img).text((W / 2, 900), "FIGHT!", font=render.font(int(170 * (1 + .3 * max(0, 1 - (t - T_FIGHT) / .15)))),
                                 anchor="mm", fill=(255, 225, 60), stroke_width=10, stroke_fill=(0, 0, 0))
    return finish(img, energy, shake, t)


def winner(F, S, t):
    img = Image.new("RGBA", (W, H), (60, 12, 12, 255))
    d = ImageDraw.Draw(img)
    for i in range(24):
        an = i / 24 * 2 * math.pi + t
        d.polygon(((W / 2, 900), (W / 2 + math.cos(an) * 1400, 900 + math.sin(an) * 1400),
                   (W / 2 + math.cos(an + .12) * 1400, 900 + math.sin(an + .12) * 1400)), fill=(110, 24, 24))
    paste_c(img, scale(S["ic_g5"], 2.0), W / 2, 900)
    d.text((W / 2, 420), "WINNER", font=render.font(170), anchor="mm", fill=(255, 225, 60), stroke_width=10, stroke_fill=(0, 0, 0))
    d.text((W / 2, 1220), "LUFFY", font=render.font(120), anchor="mm", fill=(255, 255, 255), stroke_width=8, stroke_fill=(0, 0, 0))
    render.draw_rich(img, (W / 2, 1380), "Who should fight next? Comment 👇", render.font(46), (255, 255, 255),
                     anchor="ma", stroke_width=5, stroke_fill=(0, 0, 0))
    return img.convert("RGB")


def main(out: Path):
    S = load()
    F = Fight(S)
    F.keys = KEYS
    cine = cine_frames()
    vid = out.with_suffix(".noaudio.mp4")
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                          "-pix_fmt", "yuv420p", str(vid)], stdin=subprocess.PIPE)
    for f in range(int(DUR * FPS)):
        p.stdin.write(render_frame(F, S, f / FPS, cine).tobytes())
    p.stdin.close()
    p.wait()
    args = ["ffmpeg", "-v", "error", "-y", "-i", str(vid)]
    filt, n = [], 0
    for t, path, v in sounds(S):
        if not Path(path).is_file():
            continue
        args += ["-i", str(path)]
        n += 1
        lim = 6.0 if "drums" in str(path) else 3
        fade = f",afade=t=out:st={lim - .5}:d=0.5" if "drums" in str(path) else ""
        filt.append(f"[{n}:a]atrim=0:{lim}{fade},volume={v},adelay={int(t * 1000)}|{int(t * 1000)}[a{n}]")
    filt.append("".join(f"[a{i}]" for i in range(1, n + 1)) + f"amix=inputs={n}:normalize=0,atrim=0:{DUR},loudnorm=I=-20:TP=-3[o]")
    args += ["-filter_complex", ";".join(filt), "-map", "0:v", "-map", "[o]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", str(out)]
    subprocess.run(args, check=True)
    vid.unlink(missing_ok=True)
    try:
        render.stamp_video(out)
    except Exception as e:
        print("filigrane ignoré :", e)
    print(out, DUR)


if __name__ == "__main__":
    main(Path(sys.argv[1]))
