"""« GOKU: 1 PUNCH VS 1000 NARUTO » (08/11, demandé : « les stickmen transformés en Naruto statique ») : chaque
stickman de la file = le Naruto Stick Nodes de l'utilisateur (naruto adult), une seule pose. Ce sont des clones
de l'ombre : touchés, ils volent puis disparaissent dans un « pouf » ; le dernier = le vrai Naruto.
python3 tools/punch/one_punch_naruto.py <sortie.mp4>

v2 (08/11) : Goku = mouvements découpés dans la vidéo de référence (tools/mocap/clips.py, retournés pour frapper
vers la droite), décor pixel-art du pack « Nature Landscapes » de l'utilisateur (landscape.PixelScene, nature_5).
python3 tools/punch/one_punch_line_v2.py <sortie.mp4>

« 1 PUNCH VS 1000 STICKMEN » en FILE INDIENNE (07/11, demandé par l'utilisateur) : les 1000 stickmen font la queue
devant Goku SSJ1 (stickman Stick Nodes), un seul coup → l'onde de choc remonte toute la file (la caméra la suit, le
compteur monte de plus en plus vite), elle meurt juste devant le dernier : 999/1000… il regarde autour de lui,
coupe sur Goku qui fait *flick*, la petite boule de ki arrive → 1000/1000 FLAWLESS.

python3 tools/punch/one_punch_line.py "library/_sticknodes/Goku SSJ1.json" <sortie.mp4>
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
from mugen_punch import F, GROUND, H, W, FPS, mountains  # noqa: E402
from one_punch import draw_stick, stick_pts  # noqa: E402
import hud  # noqa: E402
from stick_punch import GX, SCALE, T_CHARGE, T_HIT, T_SSJ, T_SWING, ease, pose_at  # noqa: E402
from clipper.slides import fusion, render, vfxgen  # noqa: E402
import landscape  # noqa: E402
sys.path.insert(0, str(ROOT / "tools" / "mocap"))
import clips  # noqa: E402

GROUND = 1580                              # sol plus bas : l'herbe du décor pixel-art remplit le bas de l'écran
GH = 470                                   # Goku debout (px)
SQ = 0.5                                   # fente : déplacement réduit (sinon Goku part du bord gauche)
CL, GF, INFO, CXC = {}, {}, {}, {}


def clip(name):
    """mouvement retourné : Goku regarde à droite (vers la file)."""
    if name not in CL:
        fr, ft = clips.load(name, GH, flip=True)
        CL[name], GF[name] = fr, ft[0]
        import json
        INFO[name] = json.load(open(clips.ROOT / name / "info.json"))
    return CL[name]


def cx_of(im):
    k = id(im)
    if k not in CXC:
        CXC[k] = float(np.nonzero(np.asarray(im)[..., 3] > 128)[1].mean())
    return CXC[k]


def vx(name, im):
    """centroïde dans le repère de la vidéo, retourné (x vers la droite = vers la file)."""
    k = GH / INFO[name]["goku_h"]
    w = INFO[name]["size"][0] * k
    return -(INFO[name]["x_in_video"] * k + w) + cx_of(im)


def place(name, im, anchor):
    """bord gauche à l'écran : centroïde = ancre + SQ × déplacement dans la vidéo (repère : garde_cavalier[0])."""
    g0 = clip("garde_cavalier")[0]
    return anchor + SQ * (vx(name, im) - vx("garde_cavalier", g0)) - cx_of(im)


def fr(name, i):
    c = clip(name)
    return c[max(0, min(len(c) - 1, i))]


NAR = {}
NH = 270                                   # taille d'un Naruto


def naruto_sprite():
    if "base" not in NAR:
        fig = sn.load(str(ROOT / "library/_sticknodes/Naruto/naruto adult.json"))
        im, _p, _o = sn.render(fig, scale=0.6)
        im = im.crop(im.getbbox())
        im = im.resize((round(im.width * NH / im.height), NH), Image.LANCZOS)
        NAR["base"] = im
    return NAR["base"]


def naruto(img, x, y, rot=0.0, scale=1.0, feet=True):
    """colle le Naruto : feet=True → pieds en y ; sinon centré en (x, y). rot en degrés (quantifié, en cache)."""
    q = int(round(rot / 10.0)) * 10 % 360
    sc = round(scale, 2)
    k = (q, sc)
    if k not in NAR:
        im = naruto_sprite()
        if sc != 1.0:
            im = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))), Image.LANCZOS)
        NAR[k] = im.rotate(q, expand=True, resample=Image.BICUBIC) if q else im
    im = NAR[k]
    if feet and not q:
        img.paste(im, (int(x - im.width / 2), int(y - im.height)), im)
    else:
        img.paste(im, (int(x - im.width / 2), int(y - im.height / 2)), im)


def poof(d, x, y, a):
    """nuage de fumée du clone de l'ombre qui disparaît (a = 0 → 1)."""
    al = int(230 * (1 - a))
    for j in range(7):
        an = j * 0.9
        r = 26 + 50 * a + 8 * (j % 3)
        cx_, cy_ = x + math.cos(an) * 34 * (0.4 + a), y + math.sin(an) * 26 * (0.4 + a)
        d.ellipse((cx_ - r, cy_ - r, cx_ + r, cy_ + r), fill=(245, 245, 250, al))


KI = {}
POOF_AT = 0.55                             # le clone touché disparaît après ce temps de vol


_SSJ = {}


def ssj(im):
    """cheveux noirs (et mèches fines autour) → jaune Super Saiyan."""
    k = id(im)
    if k not in _SSJ:
        from scipy import ndimage as ndi
        a = np.asarray(im).copy()
        c = a[..., :3].astype(int)
        core = (c.sum(2) < 170) & (np.abs(c[..., 2] - c[..., 0]) < 30) & (a[..., 3] > 0)
        zone = ndi.binary_dilation(core, iterations=max(8, im.height // 25))
        hair = core | ((c.sum(2) < 360) & (np.abs(c[..., 2] - c[..., 0]) < 45) & (a[..., 3] > 0) & zone)
        lum = np.minimum(c[..., 0][hair], 170) / 170.0
        a[..., 0][hair] = (255 - 30 * (1 - lum)).astype(np.uint8)
        a[..., 1][hair] = (220 - 50 * (1 - lum)).astype(np.uint8)
        a[..., 2][hair] = (70 - 30 * (1 - lum)).clip(0, 255).astype(np.uint8)
        _SSJ[k] = Image.fromarray(a)
    return _SSJ[k]


PUNCH_HIT = 1

N = 1000
GAP = 68                         # écart entre 2 stickmen de la file
SH = 165                         # taille d'un stickman
TP = 1.4                         # le coup arrive vite (demandé : « ça prend trop de temps »)
K = T_HIT / TP                   # l'animation de stick_punch est accélérée d'autant
FREEZE = 0.22
WA, WB = 500.0, 900.0            # onde : x = WB·a + WA·a² (accélère)
GRAV = 2000.0
DASH = 95
GSC = SCALE * 0.75               # Goku un peu plus petit (demandé)


SKIN = (250, 214, 178)
# petits clins d'œil dans la file (demandé : « des petites refs, c'est tout ») : index → type
EGGS = {}
EGG_COL = {"straw": (200, 40, 40), "band": (240, 120, 30), "bald": (240, 120, 30), "yamcha": (240, 120, 30)}


def draw_egg(d, kind, x, y, h, ph, rot, mode, hat=True):
    """Accessoire dessiné sur la tête d'un stickman (chapeau de paille, bandeau, crâne à points…)."""
    p = stick_pts(x, y, h, ph, rot, mode)
    hx, hy = p["head"]
    nx, ny = p["neck"]
    ang = math.atan2(hy - ny, hx - nx)                       # direction « haut » de la tête
    ux, uy = math.cos(ang), math.sin(ang)                    # vers le haut
    vx, vy = -uy, ux                                         # perpendiculaire
    r = h * 0.11
    def P(a, b):
        return (hx + ux * a * r + vx * b * r, hy + uy * a * r + vy * b * r)
    if kind == "straw" and hat:
        d.polygon([P(0.5, -2.1), P(0.9, -1.0), P(0.9, 1.0), P(0.5, 2.1), P(0.2, 0)], fill=(240, 205, 90))
        d.polygon([P(0.7, -0.9), P(1.7, -0.7), P(1.7, 0.7), P(0.7, 0.9)], fill=(240, 205, 90))
        d.polygon([P(0.75, -0.9), P(1.05, -0.85), P(1.05, 0.85), P(0.75, 0.9)], fill=(200, 30, 30))
    elif kind == "band":
        d.polygon([P(0.15, -1.05), P(0.55, -1.05), P(0.55, 1.05), P(0.15, 1.05)], fill=(30, 40, 110))
        d.polygon([P(0.18, -0.45), P(0.52, -0.45), P(0.52, 0.45), P(0.18, 0.45)], fill=(200, 205, 215))
        for b in (-1.0, 0.0, 1.0):                           # cheveux jaunes en pointes
            d.polygon([P(0.6, b - 0.55), P(1.55, b + 0.15), P(0.6, b + 0.55)], fill=(255, 210, 40))
    elif kind == "zoro":
        for b in (-0.9, -0.3, 0.3, 0.9):
            d.polygon([P(0.3, b - 0.45), P(1.35, b), P(0.3, b + 0.45)], fill=(60, 170, 70))
        hip = p["hip"]
        for k in range(3):                                   # 3 sabres à la ceinture
            d.line((hip[0] - 0.05 * h, hip[1] + k * 4, hip[0] + 0.45 * h, hip[1] - 0.12 * h + k * 7), fill=(30, 30, 30),
                   width=max(2, int(h * 0.03)))
    elif kind in ("bald", "yamcha"):
        d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=SKIN)
        if kind == "bald":
            for a, b in ((0.55, -0.35), (0.55, 0.0), (0.55, 0.35), (0.25, -0.2), (0.25, 0.15), (0.8, 0.0)):
                q = P(a, b)
                d.ellipse((q[0] - 2.5, q[1] - 2.5, q[0] + 2.5, q[1] + 2.5), fill=(90, 60, 50))
        else:
            for b in (-0.9, -0.3, 0.3, 0.9):                 # cheveux noirs
                d.polygon([P(0.4, b - 0.4), P(1.5, b + 0.5), P(0.4, b + 0.4)], fill=(25, 25, 30))


def yamcha_pose(d, x, h, col):
    """Le célèbre K.O. recroquevillé dans son cratère."""
    g = GROUND
    d.ellipse((x - h * 0.85, g - h * 0.12, x + h * 0.85, g + h * 0.22), fill=(150, 105, 70))
    d.ellipse((x - h * 0.7, g - h * 0.05, x + h * 0.7, g + h * 0.16), fill=(120, 82, 55))
    w = max(2, int(h * 0.075))
    hip, sh_ = (x + h * 0.15, g - h * 0.05), (x - h * 0.25, g - h * 0.1)
    d.line((hip, sh_), fill=col, width=w)
    d.line((hip, (x + h * 0.3, g - h * 0.32), (x + h * 0.05, g - h * 0.3)), fill=col, width=w, joint="curve")
    d.line((hip, (x + h * 0.4, g - h * 0.18), (x + h * 0.15, g - h * 0.2)), fill=col, width=w, joint="curve")
    d.line((sh_, (x - h * 0.15, g - h * 0.3)), fill=col, width=w)
    d.line((sh_, (x - h * 0.05, g - h * 0.02)), fill=col, width=w)
    r = h * 0.11
    hx, hy = x - h * 0.4, g - h * 0.09
    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=SKIN)
    for b in (-0.8, -0.2, 0.4):
        d.polygon([(hx - r * 0.4, hy - r * 0.3 + b * r), (hx - r * 1.5, hy + b * r + r * 0.4), (hx - r * 0.4, hy + b * r + r * 0.5)],
                  fill=(25, 25, 30))


def desert_sky():
    """Ciel clair au-dessus d'un désert rocheux (autre terrain que « How far »)."""
    y = np.linspace(0, 1, H)[:, None, None]
    top, bot = np.array([70, 150, 230.]), np.array([255, 226, 170.])
    a = top * (1 - y ** 0.8) + bot * y ** 0.8
    im = Image.fromarray(a.repeat(W, 1).clip(0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(im)
    for cx_, cy_, w_ in ((160, 620, 300), (720, 760, 380), (420, 900, 260)):
        for j in range(4):
            d.ellipse((cx_ + j * w_ / 5 - w_ / 3, cy_ - 30 - (j % 2) * 26, cx_ + j * w_ / 5 + w_ / 3, cy_ + 30),
                      fill=(255, 255, 255, 230))
    return im


def wave_x(a):
    return WB * a + WA * a * a


def main():
    out = Path(sys.argv[1])
    for n_ in ("garde_cavalier", "coup_de_poing_fente", "retour_du_coup", "lancer_ki"):
        clip(n_)
    hit = clip("coup_de_poing_fente")[PUNCH_HIT]
    al_ = np.asarray(hit)[..., 3] > 128
    ys_, xs_ = np.nonzero(al_)
    fist_x = 560.0                                                     # poing tendu au moment du coup
    A = fist_x - (place("coup_de_poing_fente", hit, 0.0) + xs_.max())
    fist_y = GROUND - GF["coup_de_poing_fente"] + float(ys_[xs_ >= xs_.max() - 25].mean())
    X0 = fist_x + 50
    rnd = random.Random(5)
    pal = [(30, 30, 40)] * 5 + [(70, 70, 85)] * 2 + [(160, 40, 45), (40, 70, 160), (240, 240, 245)]
    men = [dict(x=X0 + i * GAP, col=rnd.choice(pal), ph=rnd.uniform(0, 6.3), hit=None) for i in range(N)]
    men[-1]["col"] = (30, 30, 40)
    for i_, k_ in EGGS.items():
        men[i_]["col"] = EGG_COL[k_]
        men[i_]["egg"] = k_

    hat = {}                                                          # chapeau de paille qui s'envole
    X_LAST = men[-1]["x"]
    # fin de l'onde : juste devant le dernier
    span = X_LAST - 30 - fist_x
    A_END = (-WB + math.sqrt(WB * WB + 4 * WA * span)) / (2 * WA)
    T_END = TP + FREEZE + A_END
    T_LOOK = T_END + 0.5
    T_CUT = T_LOOK + 1.9            # coupe sur Goku : *flick*
    T_BACK = T_CUT + 1.5            # retour sur le survivant, la boule arrive
    T_FLY = T_BACK + 0.35
    T_STAR = T_FLY + 0.9             # il devient une étoile qui scintille dans le ciel
    T_WIN = T_STAR + 0.35
    DUR = T_WIN + 3.0
    CAM_MAX = X_LAST - 640
    # nature_2 : grande prairie qui remplit tout le bas en vertical (nature_5 laissait un raccord visible)
    scene = landscape.PixelScene(W, H, GROUND, "nature_2", scale=6.8, oy=-278)
    confetti = []
    explo = list(vfxgen.frames("explosion", 620, (255, 210, 80)))
    ring = list(vfxgen.frames("ring", 900, (255, 240, 180)))
    bolt = list(vfxgen.frames("lightning", 260, (255, 240, 120)))
    fT, fS = F("anton.woff2", 112), F("mont900.woff2", 30)
    debris, launches, puffs = [], [], []
    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                             f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf",
                             "18", "-pix_fmt", "yuv420p", str(out.with_suffix(".video.mp4"))], stdin=subprocess.PIPE)
    cam = 0.0
    for fi in range(int(DUR * FPS)):
        t = fi / FPS
        a = t - TP - FREEZE                                            # temps depuis la fin de l'arrêt sur image
        wx = fist_x + wave_x(min(a, A_END)) if a >= 0 else -1e9
        if a >= 0 and t < T_END + 0.2:
            cam = max(cam, min(CAM_MAX, wx - 460))
        cut_goku = T_CUT <= t < T_BACK
        cx = 0.0 if cut_goku else cam
        # ------------------------------------------------ décor (parallaxe)
        img = scene.frame(cx)
        d = ImageDraw.Draw(img, "RGBA")
        mk = int(cx // 2000)                                           # bornes de distance
        for j in (mk, mk + 1):
            bx = j * 2000 + 600 - cx
            if j > 0 and -100 < bx < W + 100:
                d.rectangle((bx - 6, GROUND - 120, bx + 6, GROUND), fill=(240, 240, 240))
                d.rounded_rectangle((bx - 60, GROUND - 170, bx + 60, GROUND - 115), 8, fill=(255, 255, 255),
                                    outline=(40, 40, 50), width=4)
                d.text((bx, GROUND - 142), f"#{min(N, j * 50)}", font=F("anton.woff2", 36), fill=(40, 40, 50), anchor="mm")
        # ------------------------------------------------ Goku
        gt = t * K if t < TP else t - TP + T_HIT
        t_punch = TP - PUNCH_HIT / FPS
        g = clip("garde_cavalier")

        def garde(tt_, end):
            if end - tt_ <= 2 / FPS:                                    # images 8–9 : départ du coup
                return g[min(len(g) - 1, 8 + int((2 / FPS - (end - tt_)) * FPS))]
            i_ = int(tt_ * FPS * 0.5) % 14
            return g[i_ if i_ < 8 else 14 - i_]
        if cut_goku:                                                  # *flick* : garde → coup → boule de ki
            k = t - T_CUT
            # vrai geste de la vidéo (114,3 s) : mains ramenées à la hanche, puis poussée des 2 paumes
            if k < 0.6:
                i_ = min(12, int(k / 0.6 * 13))
            elif k < 0.75:
                i_ = 13 + int((k - 0.6) * FPS)
            else:
                i_ = min(22, 17 + int((k - 0.75) * FPS))
            name, gim = "lancer_ki", fr("lancer_ki", i_)
        elif t < t_punch:
            name, gim = "garde_cavalier", garde(t, t_punch)
        else:
            i_ = int((t - t_punch) * FPS)
            hold = int((1.4 + FREEZE) * FPS)                         # bras tendu pendant l'onde
            if i_ <= PUNCH_HIT:
                name, gim = "coup_de_poing_fente", fr("coup_de_poing_fente", i_)
            elif i_ < PUNCH_HIT + hold:
                name, gim = "coup_de_poing_fente", fr("coup_de_poing_fente", PUNCH_HIT)
            else:
                j_ = i_ - hold + 1
                if j_ < 10:
                    name, gim = "coup_de_poing_fente", fr("coup_de_poing_fente", j_)
                else:
                    name, gim = "retour_du_coup", fr("retour_du_coup", j_ - 10)
        gx_ = place(name, gim, A) + gim.width / 2
        goku_on = gx_ - cx > -500
        if goku_on:
            if gt >= T_SSJ:
                gim = ssj(gim)
            pim = gim
            px, py = int(place(name, gim, A) - cx), int(GROUND - GF[name])
            power = 0.0
            if T_SSJ <= gt and t < TP + 0.6:
                power = min(1.0, (gt - T_SSJ) / 0.6) * (1 if t < TP else max(0, 1 - (t - TP) / 0.6))
            if t >= TP + 0.6:
                power = 0.35
            if power > 0:
                au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ad = ImageDraw.Draw(au)
                ch_ = GH * 0.62
                gcx = px + cx_of(gim)
                for scl, col, al in ((1.25, (255, 225, 40), 150), (1.0, (255, 245, 150), 190), (0.7, (255, 255, 235), 170)):
                    ad.polygon(rig.aura_poly(gcx, GROUND - ch_ * 0.95, (110 + 30 * power) * scl, ch_ * scl,
                                             t * 1.3 + scl, n=30, seed=int(scl * 10)), fill=col + (int(al * power),))
                g_ = au.filter(ImageFilter.GaussianBlur(18))
                img.paste(g_, (0, 0), g_)
                img.paste(au, (0, 0), au)
                if fi % 3 == 0 and power > 0.5:
                    b = bolt[fi // 3 % len(bolt)]
                    img.paste(b, (int(gcx - b.width / 2 + rnd.uniform(-60, 60)), int(py + rnd.uniform(0, 200))), b)
            img.paste(pim, (px, py), pim)
            d = ImageDraw.Draw(img, "RGBA")
            if cut_goku:
                k = t - T_CUT
                ar_ = np.asarray(pim).astype(int)
                skin = (np.abs(ar_[..., :3] - np.array([250, 214, 182])).sum(2) < 70) & (ar_[..., 3] > 128)
                skin[: int(pim.height * 0.33)] = False                  # pas le visage
                skin[int(pim.height * 0.8):] = False
                hy_, hx_ = np.nonzero(skin)
                if k < 0.6:                                           # mains jointes à la hanche
                    sel = hx_ >= np.percentile(hx_, 60)
                    hx, hy = px + hx_[sel].mean(), py + hy_[sel].mean()
                else:                                                 # paumes poussées vers l'avant
                    j_ = hx_.argmax()
                    hx, hy = px + hx_[j_] + 10, py + hy_[j_]
                    if k >= 0.75 and "palm" not in KI:
                        KI["palm"] = (hx, hy)
                if k < 0.75:                                          # la boule de ki se charge dans la main
                    r = 8 + 30 * ease(k / 0.6)
                    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(gl).ellipse((hx - r * 2.2, hy - r * 2.2, hx + r * 2.2, hy + r * 2.2), fill=(255, 230, 90, 170))
                    gl = gl.filter(ImageFilter.GaussianBlur(16))
                    img.paste(gl, (0, 0), gl)
                    d = ImageDraw.Draw(img, "RGBA")
                    d.ellipse((hx - r, hy - r, hx + r, hy + r), fill=(255, 250, 210))
                    for j in range(5):                                # énergie qui converge
                        an = j * 1.26 + t * 9
                        rr = 120 * (1 - (k * 3 + j * 0.2) % 1)
                        d.line((hx + math.cos(an) * rr, hy + math.sin(an) * rr, hx + math.cos(an) * (rr + 30),
                                hy + math.sin(an) * (rr + 30)), fill=(255, 240, 150, 220), width=5)
                else:
                    kk = (k - 0.75) / 0.75
                    px0, fy0 = KI.get("palm", (hx, hy))
                    bx = px0 + kk * 1100
                    for j in range(8):
                        d.ellipse((bx - j * 40 - 30 + j * 3, fy0 - 30 + j * 3, bx - j * 40 + 30 - j * 3, fy0 + 30 - j * 3),
                                  fill=(255, 235, 110, 160 - j * 18))
                    d.ellipse((bx - 40, fy0 - 40, bx + 40, fy0 + 40), fill=(255, 240, 120, 140))
                    d.ellipse((bx - 22, fy0 - 22, bx + 22, fy0 + 22), fill=(255, 255, 235))
                    if kk < 0.6:
                        s_ = 1 + 0.5 * max(0.0, 1 - kk / 0.12)
                        img = hud.label(img, (px0 + 40, fy0 - 190), "HA!", int(120 * s_), fill=(255, 225, 50), angle=6)
                        d = ImageDraw.Draw(img, "RGBA")
        # ------------------------------------------------ la file
        march = max(0.0, 1.2 - t) * 260                                # elle arrive par la droite au début
        for i, m in enumerate(men):
            if m["hit"] is None and i < N - 1 and wx >= m["x"]:
                m["hit"] = t
                m["vx"] = rnd.uniform(200, 900)
                m["vy"] = -rnd.uniform(1300, 2500)
                m["spin"] = rnd.uniform(600, 1500) * rnd.choice((1, -1))
                if m.get("yam"):
                    m["vx"], m["vy"] = -120, -1500
                launches.append(t)
            if m["hit"] is None:
                x = m["x"] + march - cx
                if not -60 < x < W + 60:
                    continue
                look = 0.0
                if i == N - 1:
                    if T_FLY <= t:
                        continue
                    if T_END <= t < T_END + 0.6:
                        x += 5 * math.sin(t * 60)
                    if t >= T_LOOK:
                        look = math.sin((t - T_LOOK) * 3.4)
                bob = 6 * abs(math.sin(m["ph"] + t * 9)) if march > 0 else 0.0
                naruto(img, x, GROUND - bob)
            else:
                aa = (t - m["hit"]) * (0.45 if t < TP + FREEZE + 0.9 else 1.0)
                tl = 2 * -m["vy"] / GRAV
                if aa < tl:
                    x = m["x"] + m["vx"] * aa - cx
                    y = GROUND + m["vy"] * aa + 0.5 * GRAV * aa * aa
                    rot = m["spin"] * aa
                else:                                                   # retombé : couché
                    x, y, rot = m["x"] + m["vx"] * tl - cx, GROUND, 90
                ra = t - m["hit"]                                       # temps réel depuis le coup
                if -120 < x < W + 120 and y > -120:
                    if ra < POOF_AT:
                        naruto(img, x, y - NH / 2, rot, feet=False)
                    elif ra < POOF_AT + 0.35:                           # clone de l'ombre : pouf
                        poof(d, x, y - NH / 2, (ra - POOF_AT) / 0.35)
                if m.get("egg") == "straw":                           # le chapeau part tout seul et redescend en planant
                    ha = t - m["hit"]
                    hxw = m["x"] + 260 * ha
                    hyw = GROUND - SH - 900 * ha + 260 * ha * ha
                    hyw = min(hyw, GROUND - 12)
                    q = hxw - cx + 30 * math.sin(ha * 5)
                    if -100 < q < W + 100:
                        draw_egg(d, "straw", q, hyw + SH, SH, 0, 25 * math.sin(ha * 5), "stand")
        # Zoro, perdu tout au bout de la file (il n'était même pas dans la queue)
        if t >= T_END - 0.6:
            zx = X_LAST + 250 + 30 * math.sin((t - T_END) * 0.8) - cx
            if -80 < zx < W + 80:
                draw_stick(d, zx, GROUND, SH, 0, 0, "stand", (40, 120, 50), look=math.sin(t * 2.3))
                draw_egg(d, "zoro", zx, GROUND, SH, 0, 0, "stand")
                if t >= T_END + 0.6:
                    d.text((zx, GROUND - SH - 60), "?", font=hud.font("luckiest-guy.woff2", 60), fill=(120, 230, 120),
                           anchor="mm", stroke_width=5, stroke_fill=(20, 40, 20))
        # le dernier s'envole
        if t >= T_FLY:
            m = men[-1]
            aa = t - T_FLY
            if t < T_STAR:                                            # il file vers le ciel en rapetissant
                k = ease(aa / (T_STAR - T_FLY))
                sx0, sy0 = m["x"] - cx, GROUND
                tx, ty = W * 0.78, 560
                x = sx0 + (tx - sx0) * k
                y = sy0 + (ty - sy0) * k - 260 * math.sin(math.pi * k)
                naruto(img, x, y - NH * (1 - k) * 0.5, 1300 * aa, scale=1 - 0.9 * k, feet=False)
            elif t < T_STAR + 0.9:                                    # ✦ scintillement « Team Rocket »
                k = (t - T_STAR) / 0.9
                r = 70 * math.sin(math.pi * min(1.0, k * 1.6)) + 8
                cxs, cys = W * 0.78, 560
                for an in (0, 90, 180, 270):
                    ra = math.radians(an + k * 90)
                    d.polygon([(cxs + math.cos(ra) * r, cys + math.sin(ra) * r), (cxs + math.cos(ra + .3) * r * .25,
                               cys + math.sin(ra + .3) * r * .25), (cxs, cys), (cxs + math.cos(ra - .3) * r * .25,
                               cys + math.sin(ra - .3) * r * .25)], fill=(255, 255, 255, 240))
                d.ellipse((cxs - r * .3, cys - r * .3, cxs + r * .3, cys + r * .3), fill=(255, 250, 200))
        if T_BACK <= t < T_FLY:                                        # la boule arrive de la gauche
            k = (t - T_BACK) / (T_FLY - T_BACK)
            bx, by = -40 + (men[-1]["x"] - cx + 40) * k, GROUND - SH * 0.55
            for j in range(6):
                d.line((bx - 60 - j * 30, by, bx - 30 - j * 30, by), fill=(255, 240, 150, 200 - j * 30), width=10)
            d.ellipse((bx - 30, by - 30, bx + 30, by + 30), fill=(255, 240, 120, 130))
            d.ellipse((bx - 16, by - 16, bx + 16, by + 16), fill=(255, 255, 230))
        # ------------------------------------------------ onde + impact
        ee = t - TP
        if 0 <= ee < FREEZE:
            g = img.convert("L").point(lambda v: 255 if v > 90 else 0)
            img = Image.merge("RGB", (g, g.point(lambda v: v * .85), g.point(lambda v: v * .3)))
            d = ImageDraw.Draw(img, "RGBA")
            if ee < 1 / FPS:
                for _ in range(30):
                    debris.append([fist_x + rnd.uniform(-30, 30), GROUND - 10, rnd.uniform(-100, 900),
                                   -rnd.uniform(300, 1100), t, rnd.uniform(8, 18), 1.8])
        if a >= 0 and t < T_END + 0.3:
            sx = wx - cx
            fade = 1.0 if t < T_END else max(0.0, 1 - (t - T_END) / 0.3)
            # nuages de poussière qui roulent derrière l'onde
            if fi % 2 == 0:
                for _ in range(2):
                    puffs.append([wx - rnd.uniform(0, 60), GROUND - rnd.uniform(0, 60), rnd.uniform(40, 80), t])
            # onde d'énergie : mur lumineux en croissant + halo flou + traînée au sol
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ld = ImageDraw.Draw(lay)
            hh = SH * 2.3
            for j, (wd, col, al) in enumerate(((150, (255, 200, 60), 150), (95, (255, 235, 130), 200), (45, (255, 255, 240), 255))):
                ld.ellipse((sx - wd, GROUND - hh, sx + wd * 0.35, GROUND + 40), fill=col + (int(al * fade),))
            ld.ellipse((sx - 260, GROUND - hh * 0.9, sx - 40, GROUND + 50), fill=(0, 0, 0, 0))   # creux du croissant
            for j in range(28):                                        # traînée au sol qui s'éteint
                x0_ = sx - 40 - j * 30
                ld.rectangle((x0_ - 30, GROUND - 14, x0_, GROUND + 10), fill=(255, 220, 110, int(200 * (1 - j / 28) * fade)))
            for _ in range(10):                                        # lignes de vitesse
                yy = GROUND - rnd.uniform(10, hh)
                ln = rnd.uniform(120, 420)
                ld.line((sx - 60 - ln, yy, sx - 60, yy), fill=(255, 250, 220, int(180 * fade)), width=rnd.randint(3, 7))
            glow = lay.filter(ImageFilter.GaussianBlur(22))
            img.paste(glow, (0, 0), glow)
            img.paste(lay, (0, 0), lay)
            d = ImageDraw.Draw(img, "RGBA")
            for _ in range(int(6 * fade)):                             # étincelles
                ang = rnd.uniform(-1.4, 0.4)
                ln = rnd.uniform(30, 90)
                x1, y1 = sx + rnd.uniform(-20, 30), GROUND - rnd.uniform(0, hh * 0.9)
                d.line((x1, y1, x1 + math.cos(ang) * ln, y1 + math.sin(ang) * ln), fill=(255, 255, 210), width=4)
            for _ in range(4):                                         # cailloux soulevés
                debris.append([wx + rnd.uniform(-20, 20), GROUND - 4, rnd.uniform(-200, 300), -rnd.uniform(400, 1000), t,
                               rnd.uniform(6, 13), 0.9])
        if puffs:
            keep_p = []
            for pf in puffs:
                aa = t - pf[3]
                if aa < 1.1:
                    r = pf[2] * (1 + aa * 2.2)
                    x, y = pf[0] - cx - aa * 60, pf[1] - aa * 70
                    if -r < x < W + r:
                        d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=(205, 165, 120, int(150 * (1 - aa / 1.1))))
                    keep_p.append(pf)
            puffs[:] = keep_p
        if 0 <= ee - FREEZE < 1.0:
            k = (ee - FREEZE) / 1.0
            ex = explo[min(len(explo) - 1, int(k * len(explo)))]
            img.paste(ex, (int(fist_x - cx - ex.width / 2), int(fist_y - ex.height / 2)), ex)
            rr_ = ring[min(len(ring) - 1, int(k * len(ring)))]
            img.paste(rr_, (int(fist_x - cx - rr_.width / 2), int(fist_y - rr_.height / 2)), rr_)
            d = ImageDraw.Draw(img, "RGBA")
            if k < 0.25:
                d.rectangle((0, 0, W, H), fill=(255, 255, 255, int(200 * (1 - k / 0.25))))
        keep = []
        for db in debris:
            aa = t - db[4]
            if aa < db[6]:
                x, y = db[0] + db[2] * aa - cx, db[1] + db[3] * aa + 1200 * aa * aa
                if y < GROUND + 4:
                    s = db[5]
                    d.polygon([(x - s, y), (x - s * .3, y - s), (x + s, y - s * .4), (x + s * .6, y + s * .7)], fill=(110, 85, 60))
                    keep.append(db)
        debris[:] = keep
        if T_SSJ <= gt < T_SSJ + 0.35:
            d.rectangle((0, 0, W, H), fill=(255, 245, 180, int(235 * (1 - (gt - T_SSJ) / 0.35))))
        # ------------------------------------------------ textes
        down = len(launches) + (1 if t >= T_FLY else 0)
        pulse = 1.1 if launches and t - launches[-1] < 0.05 and down < 999 else 1.0
        img = hud.draw(img, "a", down, pulse=pulse, title=("1 PUNCH", "VS 1000 NARUTO"))
        if T_END + 0.2 <= t < T_FLY and not cut_goku:
            img = hud.label(img, (W / 2, 580), "1 LEFT...", 104, fill=(255, 80, 80), angle=-3)
            m = men[-1]
            img = hud.label(img, (m["x"] - cx, GROUND - NH - 60), "!?" if t < T_LOOK + 0.8 else "?", 86,
                            fill=(255, 225, 50))
        d = ImageDraw.Draw(img, "RGBA")
        if t >= T_WIN:
            a_ = t - T_WIN
            rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))            # rayons qui tournent derrière le texte
            rd = ImageDraw.Draw(rays)
            for j in range(14):
                an = math.radians(j * 360 / 14 + a_ * 40)
                rd.polygon([(W / 2, 610), (W / 2 + math.cos(an - .09) * 1400, 610 + math.sin(an - .09) * 1400),
                            (W / 2 + math.cos(an + .09) * 1400, 610 + math.sin(an + .09) * 1400)],
                           fill=(255, 235, 120, int(90 * min(1.0, a_ / 0.3))))
            img.paste(rays, (0, 0), rays)
            d = ImageDraw.Draw(img, "RGBA")
            if not confetti:
                for _ in range(160):
                    confetti.append([rnd.uniform(0, W), rnd.uniform(-900, -20), rnd.uniform(-80, 80), rnd.uniform(250, 520),
                                     rnd.choice([(255, 80, 80), (255, 210, 60), (80, 200, 255), (120, 255, 140), (255, 120, 220)]),
                                     rnd.uniform(0, 6.3)])
            for c in confetti:
                x, y = c[0] + c[2] * a_ + 30 * math.sin(a_ * 4 + c[5]), c[1] + c[3] * a_
                w_ = 14 * abs(math.cos(a_ * 6 + c[5])) + 3
                d.rectangle((x - w_, y - 6, x + w_, y + 6), fill=c[4])
            s = 1 + 0.4 * max(0.0, 1 - a_ / 0.15) + 0.04 * math.sin(a_ * 6)
            img = hud.label(img, (W / 2, 610), "FLAWLESS", int(150 * s), fill=(255, 214, 50), angle=3)
            if a_ > 0.4:
                rgba = img.convert("RGBA")
                render.draw_rich(rgba, (W / 2, 735), "Who takes 10,000 next? Comment 👇", hud.font("luckiest-guy.woff2", 54),
                                 (255, 255, 255), anchor="ma", stroke_width=5, stroke_fill=(20, 20, 50))
                img = rgba.convert("RGB")
        # secousse
        sh = 0
        if T_CHARGE <= gt < T_HIT:
            sh = 4
        if 0 <= gt - T_SSJ < 0.45:
            sh = 16
        if 0 <= ee < 1.2:
            sh = 32 * (1 - ee / 1.2)
        elif a >= 0 and t < T_END:
            sh = 5
        if 0 <= t - T_FLY < 0.25:
            sh = 14
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
    for k in range(6):                                                 # la file qui arrive
        put(k * 0.3, S("hit", 20 + k % 4), 0.08)
    put(T_SSJ / K - 0.05, S("transform"), 0.9)
    put(T_SWING / K, S("teleport"), 0.5)
    put(TP, S("hit", 1), 1.0)
    put(TP + FREEZE, S("bomb", 2), 1.0)
    put(TP + FREEZE + 0.1, S("ko"), 0.6)
    for j in range(0, len(launches), 12):                              # un coup tous les 12 stickmen
        put(launches[j], S("hit", 30 + j % 6), 0.25)
    put(T_CUT + 0.2, S("shots", 3), 0.6)
    put(T_FLY, S("hit", 3), 1.0)
    put(T_STAR, S("teleport", 4), 0.5)
    put(T_WIN, S("ko", 1), 0.7)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.3)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".video.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out.with_suffix(".raw.mp4"))],
                   check=True)
    render.stamp_video(out.with_suffix(".raw.mp4"), out)
    print("OUT", out, round(DUR, 1), "down", len(launches) + 1, "wave", round(A_END, 1))


if __name__ == "__main__":
    main()
