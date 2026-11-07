"""Séquence de 10 s imitée de la vidéo de référence (« Goku ALL Transformations », à partir de 1:49) :
salto + coup de pied → réception en garde → Kaioken (éclairs rouges, aura de flammes qui grandit, corps rougi) →
rush dans l'aura → garde basse → Kamehameha (fond assombri, rayons qui tournent, boule qui grossit) → tir géant →
flash blanc. Goku Pivot + animation Mixamo (salto) + poses du moteur. python3 kaioken.py doc.json dossier_dae sortie.mp4
"""
import json
import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "punch"))
sys.path.insert(0, str(HERE.parents[1]))
import dae  # noqa: E402
import hud  # noqa: E402
import pivot_render as pr  # noqa: E402
import stickanim as sa  # noqa: E402

W, H, FPS = 1080, 1920, 30
GY = 1250
SCALE = 2.6
doc = json.load(open(sys.argv[1]))
D = sys.argv[2]
OUT = sys.argv[3]
g = pr.PivotActor(doc, 0, 0, pr.ROLES_PIVOT_GOKU, scale=SCALE)
J = g._joints({}, angles=g.rest_ang)
R = pr.ROLES_PIVOT_GOKU
LEG = sum(math.dist(J[R[k]][0], J[R[k]][max(J[R[k]])]) for k in ("thigh_f", "shin_f")) * SCALE
rnd = random.Random(7)

# ---------------------------------------------------------------- mouvements
flip = dae.load(f"{D}/mx_flipkick/mx_flipkick.dae", fps=FPS)
FLIP_RATE = 1.15
T0_FLIP = 0.0
CUT = 34                                                 # image du salto où on quitte Mixamo (encore en l'air, avant
                                                         # que l'acteur se retourne : sinon tête à droite / corps à gauche)
T_CUT = CUT / FPS / FLIP_RATE
T_LAND = T_CUT + 0.32                                    # chute contrôlée jusqu'au sol, réception accroupie
T_POW = T_LAND + 0.35                                    # début du Kaioken
T_AURA = T_POW + 0.45
T_DASH = T_POW + 1.55
T_STOP = T_DASH + 0.55
T_KAME = T_STOP + 0.45
T_FIRE = T_KAME + 2.8
T_FLASH = T_FIRE + 1.35
T_END = T_FLASH + 1.0


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def back_out(u, s=1.6):
    u = max(0.0, min(1.0, u)) - 1
    return u * u * ((s + 1) * u + s) + 1


fx0 = flip[0][1]
fxs = [x for _, x, _, _ in flip]
FLIP_K = 130 / max(1e-6, (max(fxs) - min(fxs)) * LEG)    # le salto avance de 380 px au plus


# salto placé par les HANCHES (pas par le point le plus bas : à l'envers c'est la tête → saut d'image)
_c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
HIP0_PX = GY + 8 - g.draw(_c, flip[0][0], 300, 0, ground=GY + 8, record=False)["y"]
HIPK = HIP0_PX / max(1e-6, flip.hip[0])
Y_CROUCH = g.draw(_c, sa.P["crouch"], 300, 0, ground=GY + 8, record=False)["y"]
FLIPY = [GY + 8 - h * HIPK for h in flip.hip]


# charge du Kamehameha DEVANT lui (mains en coupe devant la taille, buste droit) au lieu des mains derrière la hanche
KAME_FRONT = dict(sa.P["kame_charge"], hip=94, spine=95, chest=97, neck=92, head=86,
                  uarm_f=300, farm_f=35, uarm_b=308, farm_b=40)


def state(t):
    """(pose, x écran, lift, rot, y des hanches ou None = posé au sol)"""
    X0 = 170
    if t < T_CUT:
        f = min(len(flip) - 1.0, t * FPS * FLIP_RATE)
        i = int(f)
        u = f - i
        j = min(i + 1, len(flip) - 1)
        pose = sa.lerp(flip[i][0], flip[j][0], u)
        x = X0 + ((flip[i][1] * (1 - u) + flip[j][1] * u) - fx0) * LEG * FLIP_K
        return pose, x, 0.0, 0.0, FLIPY[i] * (1 - u) + FLIPY[j] * u
    xc = X0 + (flip[CUT][1] - fx0) * LEG * FLIP_K
    xl = xc + 40
    if t < T_LAND:
        # fin du salto : le corps finit sa rotation et se pose accroupi, la hauteur retombe (chute)
        u = (t - T_CUT) / (T_LAND - T_CUT)
        land = dict(sa.P["crouch"])
        pose = sa.lerp(flip[CUT][0], land, ease(u))
        y = FLIPY[CUT] + (Y_CROUCH - FLIPY[CUT]) * (u * u)          # chute (accélère), finit pile accroupi au sol
        return pose, xc + 40 * u, 0.0, 0.0, y
    if t < T_POW:
        u = ease((t - T_LAND) / 0.3)
        return sa.lerp(sa.P["crouch"], sa.P["stance_low"], u), xl, 0.0, 0.0, None
    if t < T_DASH:
        # accroupi qui serre les poings → se redresse en criant (Kaioken)
        u = (t - T_POW) / (T_DASH - T_POW)
        if u < 0.3:
            pose = sa.lerp(sa.P["stance_low"], sa.P["crouch"], ease(u / 0.3))
        else:
            pose = sa.lerp(sa.P["crouch"], sa.P["power"], back_out((u - 0.3) / 0.25))
        sh = 6 * math.sin(t * 90) if u > 0.3 else 0
        return pose, xl + sh, 0.0, 0.0, None
    if t < T_STOP:
        # rush dans l'aura : penché vers l'avant, glisse vers la droite puis freine
        u = (t - T_DASH) / (T_STOP - T_DASH)
        pose = sa.lerp(sa.P["power"], sa.P["run_a"], ease(u / 0.25))
        x = xl + 140 * (1 - (1 - min(1, u)) ** 3)
        return pose, x, 30 * math.sin(math.pi * min(1, u)), -18 * (1 - u), None
    xs = xl + 140
    if t < T_KAME:
        u = ease((t - T_STOP) / (T_KAME - T_STOP))
        return sa.lerp(sa.P["run_a"], sa.P["stance_low"], u), xs, 0.0, 0.0, None
    if t < T_FIRE:
        u = ease((t - T_KAME) / 0.4)
        return sa.lerp(sa.P["stance_low"], KAME_FRONT, u), xs, 0.0, 0.0, None
    if t < T_FLASH + 0.4:
        u = back_out((t - T_FIRE) / 0.18)
        return sa.lerp(KAME_FRONT, sa.P["kame_fire"], u), xs, 0.0, 0.0, None
    u = ease((t - T_FLASH - 0.4) / 0.5)
    return sa.lerp(sa.P["kame_fire"], sa.P["stance"], u), xs, 0.0, 0.0, None


# ---------------------------------------------------------------- décor (à nous, inspiré : ciel pâle, sol bleuté)
from scene import make_bg  # noqa: E402


BG = make_bg(GY)


# ---------------------------------------------------------------- effets
def flame_aura(lay, cx, foot, hgt, wid, t, alpha=1.0, stretch=0.0):
    """aura de flammes du Kaioken : goutte autour du corps, pointes qui montent (vers le haut, pas en étoile),
    remplissage rouge translucide, double contour rose/blanc. stretch > 0 = couchée vers l'arrière (rush)."""
    d = ImageDraw.Draw(lay)
    pts = []
    N = 44
    cy = foot - hgt * 0.45
    for i in range(N):
        a = i / N * 2 * math.pi
        sx, sy = math.sin(a), -math.cos(a)                   # sy = 1 en haut
        rx = wid / 2 * (1 - 0.25 * max(0.0, sy))               # se resserre vers le haut (forme de flamme)
        px = cx + sx * rx
        py = cy - sy * hgt * (0.45 if sy < 0 else 0.42)
        if sy > -0.1:                                          # pointes vers le haut
            up = (0.5 + sy) * hgt * (0.16 if i % 2 == 0 else 0.02)
            up *= 0.7 + 0.3 * math.sin(t * 21 + i * 1.9)
            py -= up
            px -= stretch * (0.2 + sy) * wid * 0.8              # couchée en arrière pendant le rush
        if sy > 0.92:                                          # pointe du sommet
            py -= hgt * 0.12
        pts.append((px, py))
    A = int(255 * alpha)
    d.polygon(pts, fill=(235, 50, 90, int(75 * alpha)))
    d.line(pts + pts[:1], fill=(255, 80, 130, int(235 * alpha)), width=8, joint="curve")
    d.line(pts + pts[:1], fill=(255, 230, 240, A), width=3, joint="curve")
    # flammèches intérieures qui montent
    for k in range(4):
        x = cx + (k - 1.5) * wid * 0.22
        h2 = hgt * (0.45 + 0.2 * math.sin(t * 17 + k * 2.1))
        d.line([(x, foot - 30), (x - 12, foot - h2 * 0.55), (x + 8, foot - h2)], fill=(255, 150, 180, int(140 * alpha)), width=4)


def red_sparks(lay, cx, cy, t, n=7, rad=170):
    d = ImageDraw.Draw(lay)
    r2 = random.Random(int(t * 30))
    for _ in range(n):
        a = r2.uniform(0, 2 * math.pi)
        x, y = cx + math.cos(a) * r2.uniform(40, rad), cy + math.sin(a) * r2.uniform(60, rad * 1.5)
        pts = [(x, y)]
        for _k in range(4):
            x += r2.uniform(-28, 28)
            y += r2.uniform(-28, 28)
            pts.append((x, y))
        d.line(pts, fill=(255, 60, 90, 230), width=4)
        d.line(pts, fill=(255, 220, 230, 255), width=1)


def kaio_tint(layer, amt):
    """corps rougi (Kaioken) : mélange vers le rouge en gardant l'ombrage."""
    if amt <= 0:
        return layer
    a = np.asarray(layer).astype(np.float32)
    lum = a[..., :3].mean(-1, keepdims=True) / 255
    red = np.concatenate([np.full_like(lum, 235), 70 * lum + 20, 90 * lum + 30], -1)
    k = amt * 0.55 * np.clip((lum - 0.18) / 0.25, 0, 1)        # les cheveux noirs restent noirs
    a[..., :3] = a[..., :3] * (1 - k) + red * k
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGBA")


def glow(lay, r=14, k=1.0):
    gl = lay.filter(ImageFilter.GaussianBlur(r))
    if k != 1:
        gl.putalpha(gl.getchannel("A").point(lambda v: min(255, int(v * k))))
    return gl


def kame_orb(lay, x, y, rad, t):
    d = ImageDraw.Draw(lay)
    for k, (c, f) in enumerate([((80, 200, 255, 90), 1.6), ((120, 225, 255, 170), 1.15), ((200, 245, 255, 230), 0.8),
                                ((255, 255, 255, 255), 0.5)]):
        r = rad * f * (1 + 0.05 * math.sin(t * 40 + k))
        d.ellipse((x - r, y - r, x + r, y + r), fill=c)


def light_rays(lay, x, y, t, a0, L=1100, alpha=1.0):
    d = ImageDraw.Draw(lay)
    for k in range(3):
        a = a0 + k * 2 * math.pi / 3
        ex, ey = x + math.cos(a) * L, y + math.sin(a) * L
        d.line((x, y, ex, ey), fill=(140, 235, 255, int(150 * alpha)), width=10)
        d.line((x, y, ex, ey), fill=(240, 255, 255, int(255 * alpha)), width=3)


def beam(lay, x0, y0, x1, th, t):
    d = ImageDraw.Draw(lay)
    for c, f in [((70, 200, 255, 170), 1.0), ((140, 230, 255, 230), 0.72), ((235, 252, 255, 255), 0.42)]:
        top, bot = [], []
        for k in range(0, 41):
            x = x0 + (x1 - x0) * k / 40
            w = th * f * (0.55 + 0.45 * min(1, k / 6)) * (1 + 0.06 * math.sin(t * 50 + k * 0.9))
            top.append((x, y0 - w))
            bot.append((x, y0 + w))
        d.polygon(top + bot[::-1], fill=c)
    kame_orb(lay, x0 + 10, y0, th * 0.62, t)


# ---------------------------------------------------------------- son
SR = 44100
try:
    from clipper.slides import sfxbank as sb
    SND = {k: sb.sound(f, "anime", s, m, "Dragon Ball") for k, (f, s, m) in {
        "whoosh": ("miss", 0, None), "land": ("hit", 1, None), "kaio": ("transform", 0, None),
        "dash": ("teleport", 2, None), "charge": ("powerup", 3, None), "beam": ("beam", 0, "Kamehameha"),
        "boom": ("ko", 1, None)}.items()}
except Exception as e:                                      # pas de banque : vidéo muette
    print("sons indisponibles :", e)
    SND = {}
CUES = [("whoosh", 0.25, 0.7), ("land", T_LAND - 0.05, 0.6), ("kaio", T_POW + 0.15, 1.0), ("dash", T_DASH, 0.8),
        ("charge", T_KAME + 0.1, 0.8), ("beam", T_FIRE - 0.15, 1.0), ("boom", T_FLASH - 0.05, 0.9)]


def write_audio(path):
    out = np.zeros(int((T_END + 1.5) * SR), np.float32)
    for k, t0, gain in CUES:
        x = SND.get(k)
        if x is None:
            continue
        x = np.asarray(x, np.float32)
        if x.ndim > 1:
            x = x.mean(1)
        i = int(t0 * SR)
        n = min(len(x), len(out) - i)
        out[i:i + n] += x[:n] * gain
    p = np.percentile(np.abs(out), 99.7) + 1e-6
    out = np.tanh(out / p * 0.75) * 0.6
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out[: int(T_END * SR)] * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- rendu
tmp = Path("/tmp/mixamo/kaioken")
tmp.mkdir(parents=True, exist_ok=True)
for f in tmp.glob("*.png"):
    f.unlink()
N = int(T_END * FPS)
hist = []
for k in range(N):
    t = k / FPS
    pose, x, lift, rot, yh = state(t)
    img = BG.copy()
    # Kaioken : intensité
    kaio = ease((t - T_AURA) / 0.5) if t > T_AURA else 0.0
    if t > T_FLASH + 0.4:
        kaio *= 1 - ease((t - T_FLASH - 0.4) / 0.6)
    charging = T_KAME + 0.3 < t < T_FLASH
    firing = T_FIRE <= t < T_FLASH + 0.15
    # assombrissement pendant la charge (comme la référence)
    if charging:
        dim = ease((t - T_KAME - 0.3) / 0.3) * (0.55 if not firing else 0.55 * (1 - ease((t - T_FIRE) / 0.25)))
        img.alpha_composite(Image.new("RGBA", (W, H), (40, 50, 70, int(255 * dim))))
    # Goku sur sa propre couche (pour le rougir), info = poings
    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if yh is None:
        info = g.draw(gl, pose, x, 0, ground=GY + 8, lift=lift, rot=rot, record=False)
    else:
        info = g.draw(gl, pose, x, yh, rot=rot, record=False)
    cx = (info["box"][0] + info["box"][2]) / 2
    top = info["box"][1]
    # aura derrière Goku
    if kaio > 0:
        hgt = (GY - top) * 1.3 * (0.55 + 0.45 * back_out(min(1, (t - T_AURA) / 0.35)))
        wid = min(460.0, (info["box"][2] - info["box"][0]) * 1.0 + 170)
        stretch = 0.0
        al = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        flame_aura(al, x, GY + 10 - lift, hgt, wid, t, kaio, stretch)
        img.alpha_composite(glow(al, 10, 0.8))
        img.alpha_composite(al)
    # images rémanentes pendant le rush
    if T_DASH <= t < T_STOP:
        for j, (hp, hx, hl, hr) in enumerate(hist[-4:][::-1]):
            ghost = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            g.draw(ghost, hp, hx, 0, ground=GY + 8, lift=hl, rot=hr, record=False, alpha=0.35 - 0.07 * j, tint=(255, 90, 120))
            img.alpha_composite(ghost)
    # Kamehameha : le rayon part de ses mains et passe DERRIÈRE lui (Goku reste devant)
    hands = ((info["fist"][0] + info["fist_b"][0]) / 2, (info["fist"][1] + info["fist_b"][1]) / 2)
    if firing:
        u = ease((t - T_FIRE) / 0.22)
        th = 190 * (0.4 + 0.6 * u) * (1 + 0.1 * math.sin(t * 30))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        beam(lay, hands[0] - 10, hands[1], hands[0] + 20 + (W + 200) * u, th, t)
        img.alpha_composite(glow(lay, 22, 1.4))
        img.alpha_composite(lay)
    img.alpha_composite(kaio_tint(gl, kaio))
    hist.append((pose, x, lift, rot))
    # éclairs rouges au début du Kaioken
    if T_POW + 0.1 < t < T_DASH:
        sp = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        red_sparks(sp, cx, (top + GY) / 2, t, n=5 if t < T_AURA else 8, rad=150)
        img.alpha_composite(glow(sp, 6, 1.2))
        img.alpha_composite(sp)
    # Kamehameha
    hands = ((info["fist"][0] + info["fist_b"][0]) / 2, (info["fist"][1] + info["fist_b"][1]) / 2)
    if charging and not firing:
        u = ease((t - T_KAME - 0.3) / (T_FIRE - T_KAME - 0.3))
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        light_rays(lay, hands[0], hands[1], t, t * 2.4, alpha=0.4 + 0.6 * u)
        kame_orb(lay, hands[0], hands[1], 14 + 30 * u, t)
        img.alpha_composite(glow(lay, 16, 1.3))
        img.alpha_composite(lay)
    # texte « KAIO-KEN! »
    if T_AURA - 0.05 < t < T_AURA + 1.0:
        u = (t - T_AURA + 0.05) / 0.25
        s = 1.0 + 0.6 * (1 - min(1, back_out(u)))
        al = 1 - ease((t - T_AURA - 0.75) / 0.25)
        tl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        hud.label(tl, (W / 2, 430), "KAIO-KEN!", int(118 * s), style="A", fill=(255, 70, 100))
        if al < 1:
            tl.putalpha(tl.getchannel("A").point(lambda v: int(v * al)))
        img.alpha_composite(tl)
    # tremblement pendant le tir
    if firing:
        dx, dy = rnd.uniform(-9, 9), rnd.uniform(-9, 9)
        img = img.transform(img.size, Image.AFFINE, (0.97, 0, dx + W * 0.015, 0, 0.97, dy + H * 0.015), resample=Image.BILINEAR)
    # flash blanc final
    if t >= T_FLASH - 0.1:
        u = ease((t - T_FLASH + 0.1) / 0.15) * (1 - ease((t - T_FLASH - 0.35) / 0.6))
        img.alpha_composite(Image.new("RGBA", (W, H), (235, 250, 255, int(255 * u))))
    img.convert("RGB").save(tmp / f"{k:05d}.png")

wav = tmp / "a.wav"
write_audio(wav)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", str(FPS), "-i", str(tmp / "%05d.png"), "-i", str(wav),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest", OUT],
               check=True)
print(N, round(T_END, 2), {k: (v is not None) for k, v in SND.items()})
