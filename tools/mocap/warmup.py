"""Séquence « échauffement » imitée de la vidéo de référence (« Goku ALL Transformations », de 0:19 à 0:30) :
fondu depuis le noir → Goku tombe du ciel et se réceptionne → monte les genoux en avançant → regarde autour de lui →
fente d'étirement (jambe arrière tendue) → accroupi, se retourne → fente de l'autre côté → se relève, touche ses
pieds → garde de combat. Mixamo (réception, regard, accroupi, passage en garde, garde) + poses clés animées à la main
(genoux, fentes, toucher les pieds), enchaînées par fondus. python3 warmup.py doc.json dossier_dae sortie.mp4
"""
import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "punch"))
sys.path.insert(0, str(HERE.parents[1]))
import dae  # noqa: E402
import pivot_render as pr  # noqa: E402
import stickanim as sa  # noqa: E402
from scene import make_bg  # noqa: E402

W, H, FPS = 1080, 1920, 30
GY = 1250
SCALE = 2.6
doc = json.load(open(sys.argv[1]))
D = sys.argv[2]
OUT = sys.argv[3]
g = pr.PivotActor(doc, 0, 0, pr.ROLES_PIVOT_GOKU, scale=SCALE)
BG = make_bg(GY)


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def clip(name):
    return dae.load(f"{D}/{name}/{name}.dae", fps=FPS)


LAND, LOOK, SQUAT, TOF, IDLE = clip("mx_land"), clip("mx_look"), clip("mx_squat"), clip("mx_to_fight"), clip("mx_idle")

# ---------------------------------------------------------------- poses clés (0° = devant, 90° = haut)
STAND = dict(sa.P["idle"])
KNEE_A = dict(STAND, hip=92, spine=93, chest=94, thigh_f=8, shin_f=275, thigh_b=268, shin_b=268,
              uarm_f=235, farm_f=150, uarm_b=300, farm_b=40)
KNEE_B = dict(KNEE_A, thigh_f=268, shin_f=268, thigh_b=8, shin_b=275, uarm_f=300, farm_f=40, uarm_b=235, farm_b=150)
LUNGE = dict(STAND, hip=62, spine=58, chest=55, neck=52, head=50,
             thigh_f=330, shin_f=268, thigh_b=230, shin_b=224,
             uarm_f=292, farm_f=300, uarm_b=285, farm_b=305)
LUNGE_DEEP = dict(LUNGE, hip=54, spine=50, chest=47, neck=45, head=44, thigh_f=345, shin_f=268, thigh_b=216, shin_b=220)
TOE = dict(STAND, hip=25, spine=5, chest=345, neck=330, head=318,
           thigh_f=274, shin_f=270, thigh_b=266, shin_b=270,
           uarm_f=282, farm_f=276, uarm_b=278, farm_b=272)


def at(F, t):
    """pose interpolée d'un clip Mixamo à l'instant t (secondes du clip)."""
    f = max(0.0, min(len(F) - 1.001, t * FPS))
    i = int(f)
    return sa.lerp(F[i][0], F[i + 1][0], f - i)


def hip_at(F, t):
    f = max(0.0, min(len(F) - 1.001, t * FPS))
    i = int(f)
    return F.hip[i] * (1 - (f - i)) + F.hip[i + 1] * (f - i)


# ---------------------------------------------------------------- scénario
# chaque segment : (durée, fonction t_local → (pose, x, facing, y_hanches ou None))
XL, XM = 760, 430                                        # x de réception, x où il s'arrête
SEG = []


def seg(dur, f):
    SEG.append((dur, f))


# 1) chute du ciel + réception (clip Mixamo « Hard Landing » à partir de 0,35 s), placée par les hanches
_c = Image.new("RGBA", (W, H), (0, 0, 0, 0))
HIPK = (GY + 8 - g.draw(_c, LAND[-1][0], 300, 0, ground=GY + 8, record=False)["y"]) / max(1e-6, LAND.hip[-1])
L0, L1 = 0.35, 2.2


def s_land(t):
    tc = L0 + t
    y = GY + 8 - hip_at(LAND, tc) * HIPK
    drop = max(0.0, 1 - t / 0.42)
    y -= 1500 * drop * drop                               # arrive du haut de l'écran
    return at(LAND, tc), XL, 1, y


seg(L1 - L0, s_land)


# 2) monte les genoux en avançant vers la gauche (de dos à la caméra ? non : il recule, face à droite, comme la réf)
def s_knees(t):
    ph = t * 2.6 * 2 * math.pi
    u = 0.5 + 0.5 * math.sin(ph)
    pose = sa.lerp(KNEE_A, KNEE_B, ease(u))
    x = XL + (XM - XL) * ease(t / 1.15)
    return pose, x, 1, None


seg(1.15, s_knees)


# 3) debout, regarde autour de lui (clip « Looking Around », passage le plus vivant)
def s_look(t):
    return at(LOOK, 1.2 + t), XM, 1, None


seg(1.5, s_look)


# 4) fente : descend, petits rebonds d'étirement, remonte
def s_lunge(t, x0=XM):
    if t < 0.4:
        p = sa.lerp(STAND, LUNGE, ease(t / 0.4))
    elif t < 1.25:
        b = 0.5 - 0.5 * math.cos((t - 0.4) / 0.85 * 2 * math.pi * 2)
        p = sa.lerp(LUNGE, LUNGE_DEEP, b)
    else:
        p = LUNGE
    return p, x0, 1, None


seg(1.35, s_lunge)


# 5) accroupi (clip « Air Squat ») ; il se retourne au fond de l'accroupi (pose symétrique : le demi-tour ne se voit pas)
def s_squat(t):
    fc = 1 if t < 0.45 else -1
    return at(SQUAT, 0.35 + t), XM - 30, fc, None


seg(0.95, s_squat)


# 6) fente de l'autre côté (regarde vers la gauche)
def s_lunge2(t):
    p, x, _, y = s_lunge(t, XM - 60)
    return p, x, -1, y


seg(1.35, s_lunge2)


# 7) se relève, se retourne (pendant qu'il est droit), touche ses pieds, remonte
def s_toe(t):
    fc = -1 if t < 0.25 else 1
    if t < 0.35:
        p = sa.lerp(LUNGE, STAND, ease(t / 0.35))
    elif t < 0.75:
        p = sa.lerp(STAND, TOE, ease((t - 0.35) / 0.4))
    elif t < 1.0:
        p = TOE
    else:
        p = sa.lerp(TOE, STAND, ease((t - 1.0) / 0.45))
    return p, XM - 40, fc, None


seg(1.45, s_toe)


# 8) passe en garde (clip « Standing Idle To Fight Idle ») puis garde qui respire (« Fighting Idle »)
def s_fight(t):
    if t < 1.0:
        return at(TOF, t), XM - 40, 1, None
    return at(IDLE, (t - 1.0) % (len(IDLE) / FPS - 0.05)), XM - 40, 1, None


seg(2.0, s_fight)

FADE_IN = 0.45
T0 = 0.5                                                 # écran vide avant l'arrivée (la réf en a 1,8 s)
BL = 0.18                                                # fondu entre deux segments
starts = []
acc = T0
for dur, f in SEG:
    starts.append(acc)
    acc += dur
T_END = acc


def state(t):
    if t < T0:
        return None
    k = max(i for i, s in enumerate(starts) if s <= t)
    dur, f = SEG[k]
    pose, x, fc, y = f(t - starts[k])
    # fondu avec la fin du segment précédent
    if k > 0 and t - starts[k] < BL:
        pd, xd, fcd, yd = SEG[k - 1][1](SEG[k - 1][0])
        u = ease((t - starts[k]) / BL)
        if fcd == fc:
            pose = sa.lerp(pd, pose, u)
        x = xd + (x - xd) * u
        if y is None and yd is not None:
            y = None if u > 0.5 else yd
    return pose, x, fc, y


# ---------------------------------------------------------------- son (léger : arrivée + réception)
SR = 44100
try:
    from clipper.slides import sfxbank as sb
    SND = {"whoosh": sb.sound("teleport", "anime", 2, None, "Dragon Ball"), "land": sb.sound("hit", "anime", 4, None, "Dragon Ball")}
except Exception as e:
    print("sons indisponibles :", e)
    SND = {}
T_LANDHIT = T0 + 0.42
CUES = [("whoosh", T0 - 0.05, 0.6), ("land", T_LANDHIT, 0.8)]


def write_audio(path):
    out = np.zeros(int((T_END + 1) * SR), np.float32)
    for k, t0, gain in CUES:
        x = SND.get(k)
        if x is None:
            continue
        x = np.asarray(x, np.float32)
        x = x.mean(1) if x.ndim > 1 else x
        i = int(t0 * SR)
        n = min(len(x), len(out) - i)
        out[i:i + n] += x[:n] * gain
    p = np.percentile(np.abs(out), 99.7) + 1e-6
    out = np.tanh(out / p * 0.75) * 0.5
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((out[: int(T_END * SR)] * 32767).astype(np.int16).tobytes())


# ---------------------------------------------------------------- rendu
tmp = Path("/tmp/mixamo/warmup")
tmp.mkdir(parents=True, exist_ok=True)
for f in tmp.glob("*.png"):
    f.unlink()
N = int(T_END * FPS)
hist = []
for k in range(N):
    t = k / FPS
    img = BG.copy()
    st = state(t)
    if st:
        pose, x, fc, y = st
        g.flip = fc < 0
        falling = t < T_LANDHIT
        if falling:                                       # traînée pendant la chute (comme la réf : flou de mouvement)
            for j, (hp, hx, hy) in enumerate(hist[-3:][::-1]):
                gh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                g.draw(gh, hp, hx, hy, record=False, alpha=0.3 - 0.08 * j)
                img.alpha_composite(gh)
        if y is None:
            g.draw(img, pose, x, 0, ground=GY + 8, shadow_y=GY + 6, record=False)
        else:
            g.draw(img, pose, x, y, shadow_y=GY + 6 if y > GY - 900 else None, record=False)
            hist.append((pose, x, y))
    if t < FADE_IN:
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - ease(t / FADE_IN))))))
    img.convert("RGB").save(tmp / f"{k:05d}.png")

wav = tmp / "a.wav"
write_audio(wav)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", str(FPS), "-i", str(tmp / "%05d.png"), "-i", str(wav),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest", OUT],
               check=True)
print(N, round(T_END, 2))
