"""Goku court de plus en plus vite, saute et s'envole sans s'arrêter (07/11, demandé : « ça doit être fluide »).
Animations Mixamo (course lente → rapide → sprint → saut depuis un sprint → vol) rejouées par le Goku Pivot,
fondus entre les clips (angles interpolés), vitesse du décor = vitesse réelle du clip (pas de pieds qui glissent),
caméra qui suit en défilement horizontal. python3 run_fly.py doc.json dossier_dae sortie.mp4
"""
import json
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parents[1] / "punch"))
import dae  # noqa: E402
import pivot_render as pr  # noqa: E402
import stickanim as sa  # noqa: E402
from mugen_punch import GROUND, mountains  # noqa: E402
from one_punch_line import desert_sky  # noqa: E402

W, H, FPS = 1080, 1920, 30
SCALE = 2.0
doc = json.load(open(sys.argv[1]))
D = sys.argv[2]
OUT = sys.argv[3]
g = pr.PivotActor(doc, 0, 0, pr.ROLES_PIVOT_GOKU, scale=SCALE)

# longueur de jambe de Goku en px (cuisse + tibia) pour convertir les déplacements Mixamo
J = g._joints({}, angles=g.rest_ang)
R = pr.ROLES_PIVOT_GOKU


def seglen(slot):
    p = J[slot]
    return math.dist(p[0], p[max(p)])


LEG = (seglen(R["thigh_f"]) + seglen(R["shin_f"])) * SCALE


class Clip:
    def __init__(self, name, loop):
        F = dae.load(f"{D}/{name}/{name}.dae", fps=120)
        if loop:
            F = F[:-1]                                   # dernière image = première (boucle)
        self.P = [f[0] for f in F]
        self.X = np.array([f[1] for f in F])
        self.L = np.array([f[2] for f in F])
        self.n = len(F)
        self.dur = self.n / 120
        self.loop = loop
        self.disp = (F[-1][1] - F[0][1]) * (self.n / (self.n - 1)) if loop else 0
        self.v = self.disp / self.dur if loop else 0     # longueurs de jambe / s

    def at(self, t):
        """pose, x (jambes), lift à l'instant t du clip (bouclé si loop)."""
        cyc = 0
        if self.loop:
            cyc, t = divmod(t, self.dur)
        f = min(self.n - 1.001, max(0.0, t * 120))
        i = int(f)
        u = f - i
        j = (i + 1) % self.n if self.loop else min(i + 1, self.n - 1)
        pose = sa.lerp(self.P[i], self.P[j], u)
        x = self.X[i] * (1 - u) + (self.X[j] + (self.disp if (self.loop and j < i) else 0)) * u + cyc * self.disp
        return pose, x, self.L[i] * (1 - u) + self.L[j] * u


slow, fast, sprint = Clip("mx_run_slow", True), Clip("mx_run_fast", True), Clip("mx_run_jump", False),
sprint = Clip("mx_sprint", True)
jump = Clip("mx_run_jump", False)
fly = Clip("mx_fly", False)
FLY_POSE = fly.P[len(fly.P) // 2]

# ---------------------------------------------------------------- scénario (temps réel, secondes)
# (début, fin, clip, cadence au début, cadence à la fin)
T_SLOW, T_FAST, T_SPRINT, T_JUMP = 0.0, 2.0, 3.8, 5.6
T_TAKE = T_JUMP + 0.30                                  # les pieds quittent le sol (image 5–6 du saut)
T_FLY = T_TAKE + 0.95                                   # fondu saut → vol terminé
T_END = T_FLY + 4.2
BL = 0.35                                               # durée des fondus entre courses


def rate_of(t):
    if t < T_FAST:
        return 0.95 + 0.25 * t / T_FAST
    if t < T_SPRINT:
        return 1.0 + 0.3 * (t - T_FAST) / (T_SPRINT - T_FAST)
    return 1.05 + 0.35 * min(1, (t - T_SPRINT) / (T_JUMP - T_SPRINT))


# phase de chaque clip intégrée dans le temps (cadence variable)
dt = 1 / FPS
N = int(T_END * FPS) + 1
ph = {"slow": 0.0, "fast": 0.0, "sprint": 0.0}
states = []
for k in range(N):
    t = k * dt
    r = rate_of(t)
    for c in ph:
        ph[c] += dt * r
    states.append((t, dict(ph), r))


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def run_pose(t, phs):
    """pose de course + vitesse (jambes/s) avec fondus slow→fast→sprint ; les phases sont calées pour que le pied
    d'appui soit le même au moment du fondu."""
    if t < T_FAST:
        p, _, _ = slow.at(phs["slow"])
        return p, slow.v
    if t < T_SPRINT:
        p2, _, _ = fast.at(phs["fast"])
        u = ease((t - T_FAST) / BL)
        p1, _, _ = slow.at(phs["slow"])
        return sa.lerp(p1, p2, u), slow.v * (1 - u) + fast.v * u
    p2, _, _ = sprint.at(phs["sprint"])
    u = ease((t - T_SPRINT) / BL)
    p1, _, _ = fast.at(phs["fast"])
    return sa.lerp(p1, p2, u), fast.v * (1 - u) + sprint.v * u


# caler les phases : chaque clip démarre au même « pas » que le précédent au moment du fondu
def match_phase(c_from, ph_from, c_to):
    pf, _, _ = c_from.at(ph_from)
    best, bt = 1e9, 0
    for i in range(c_to.n):
        q = c_to.P[i]
        d = sum(abs((pf[k] - q[k] + 180) % 360 - 180) for k in ("thigh_f", "thigh_b", "shin_f", "shin_b"))
        if d < best:
            best, bt = d, i / 120
    return bt


kf = int(T_FAST * FPS)
off_fast = match_phase(slow, states[kf][1]["slow"], fast) - states[kf][1]["fast"]
ks = int(T_SPRINT * FPS)
off_sprint = match_phase(fast, states[ks][1]["fast"] + off_fast, sprint) - states[ks][1]["sprint"]
kj = int(T_JUMP * FPS)
jump0 = match_phase(sprint, states[kj][1]["sprint"] + off_sprint, jump)
jump0 = min(jump0, 0.12)                                 # le saut commence dans sa course d'élan
for t, phs, r in states:
    phs["fast"] += off_fast
    phs["sprint"] += off_sprint

# ---------------------------------------------------------------- trajectoire
JR = 1.25                                                # cadence du saut
FLY_H = 640                                              # altitude de croisière (px)
traj = []
wx = 0.0
for k, (t, phs, r) in enumerate(states):
    lift = 0.0
    rot = 0.0
    if t < T_JUMP:
        pose, v = run_pose(t, phs)
        speed = v * r * LEG
    else:
        tj = jump0 + (t - T_JUMP) * JR
        pj, xj, lj = jump.at(tj)
        pr_, v = run_pose(t, phs)
        u0 = ease((t - T_JUMP) / 0.12)
        pose = sa.lerp(pr_, pj, u0)
        speed = sprint.v * 1.4 * LEG
        # montée : la hauteur du saut, puis une courbe qui continue de monter (il ne retombe jamais)
        ta = max(0.0, t - T_JUMP)
        hj = lj * LEG
        hf = FLY_H * (1 - math.exp(-max(0.0, t - T_TAKE) / 0.55))
        lift = max(hj, hj * (1 - ease((t - T_TAKE) / 0.4)) + hf) if t > T_TAKE else hj
        if t > T_TAKE:
            u0_ = max(0.0, min(1.0, (t - T_TAKE) / (T_FLY - T_TAKE)))
            u = math.sin(u0_ * math.pi / 2)                # bascule régulière, ralentit à la fin (pas d'à-coup)
            fi = int((t - T_TAKE) * 120) % len(fly.P)
            fp = sa.lerp(fly.P[fi], FLY_POSE, 0.6)
            pose = sa.lerp(pose, fp, u)
            rot = -10 * u * (1 - ease((t - T_FLY - 1.0) / 1.5))   # nez un peu vers le haut en décollant
            speed = LEG * sprint.v * (1.4 + 3.5 * ease((t - T_TAKE) / 2.2))
    wx += speed * dt
    traj.append((t, pose, wx, lift, rot, speed))

# ---------------------------------------------------------------- décor (parallaxe)
SKY = desert_sky().convert("RGBA")
def seamless(img):
    """bande de montagnes qui boucle sans raccord : on coupe les bords (pentes de départ/fin) et on recolle le miroir."""
    c = img.crop((300, 0, img.width - 300, img.height))
    out = Image.new("RGBA", (c.width * 2, c.height), (0, 0, 0, 0))
    out.alpha_composite(c, (0, 0))
    out.alpha_composite(c.transpose(Image.FLIP_LEFT_RIGHT), (c.width, 0))
    return out


FAR = seamless(mountains(1, (214, 150, 110, 255), 260, 1080, 420, W * 3))
NEAR = seamless(mountains(2, (176, 108, 72, 255), 150, 1190, 260, W * 3))
CLOUDS = SKY.crop((0, 0, W, GROUND - 250))


def tile(img, off):
    w = img.width
    off = int(off) % w
    out = Image.new("RGBA", (W, img.height), (0, 0, 0, 0))
    out.alpha_composite(img.crop((off, 0, min(w, off + W), img.height)), (0, 0))
    if off + W > w:
        out.alpha_composite(img.crop((0, 0, off + W - w, img.height)), (w - off, 0))
    return out


rnd = random.Random(3)
PEB = [(rnd.uniform(0, 4000), rnd.uniform(30, 520), rnd.uniform(18, 60)) for _ in range(70)]
dust = []                                                # [x_monde, y, r, age, vx, vy]


def ground_layer(img, camx, camy):
    d = ImageDraw.Draw(img)
    gy = GROUND + camy
    if gy > H:
        return
    d.rectangle((0, gy, W, H), fill=(222, 178, 120))
    d.rectangle((0, gy, W, gy + 6), fill=(196, 146, 96))
    for px, py, pw in PEB:
        x = (px - camx) % 4000 - 200
        if -100 < x < W + 100:
            d.ellipse((x, gy + py, x + pw, gy + py + pw * 0.35), fill=(196, 140, 96))


def speed_lines(img, amt, t, ycen):
    if amt <= 0:
        return
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    r2 = random.Random(int(t * 60))
    for _ in range(int(14 + 40 * amt)):
        y = r2.uniform(80, H - 80)
        if abs(y - ycen) < 140 and r2.random() < 0.6:
            continue
        x = r2.uniform(-200, W)
        L = r2.uniform(120, 420) * (0.6 + amt)
        d.line((x, y, x + L, y), fill=(255, 255, 255, int(90 + 110 * amt)), width=r2.choice((2, 3, 4)))
    img.alpha_composite(lay)


# ---------------------------------------------------------------- rendu
tmp = Path("/tmp/mixamo/runfly")
tmp.mkdir(parents=True, exist_ok=True)
for f in tmp.glob("*.png"):
    f.unlink()
SX = 430                                                 # place de Goku à l'écran
hist = []
took = False
for k, (t, pose, wx, lift, rot, speed) in enumerate(traj):
    camx = wx - SX
    camy = int(max(0.0, lift - 260) * 0.75)              # la caméra monte avec lui (le sol descend)
    img = Image.new("RGBA", (W, H))
    img.alpha_composite(SKY)
    img.alpha_composite(tile(FAR, camx * 0.15), (0, camy // 3))
    img.alpha_composite(tile(NEAR, camx * 0.35), (0, camy // 2))
    ground_layer(img, camx, camy)
    gy = GROUND + camy
    # poussière
    if t < T_TAKE and k % 3 == 0 and t > 1.0:
        dust.append([wx - 30, 6, 14 + 10 * (speed / LEG / 8), 0.0, -speed * 0.15, 40])
    if not took and t >= T_TAKE:
        took = True
        for i in range(26):
            a = math.radians(rnd.uniform(110, 250))
            sp = rnd.uniform(200, 700)
            dust.append([wx + rnd.uniform(-40, 40), 6, rnd.uniform(20, 50), 0.0, math.cos(a) * sp, abs(math.sin(a)) * sp * 0.5])
    dl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dl)
    for p in dust:
        p[3] += dt
        p[0] += p[4] * dt
        p[1] = max(0.0, p[1] + p[5] * dt)
        p[5] -= 300 * dt
        p[2] += 40 * dt
        al = max(0, 1 - p[3] / 0.7)
        x = p[0] - camx
        y = gy - p[1]
        if al > 0:
            dd.ellipse((x - p[2], y - p[2] * 0.6, x + p[2], y + p[2] * 0.6), fill=(235, 205, 160, int(170 * al)))
    dust[:] = [p for p in dust if p[3] < 0.7]
    img.alpha_composite(dl.filter(ImageFilter.GaussianBlur(3)))
    # lignes de vitesse : sprint puis vol
    amt = 0.0
    if t > T_SPRINT:
        amt = 0.25 * ease((t - T_SPRINT) / 1.2)
    if t > T_TAKE:
        amt = 0.25 + 0.75 * ease((t - T_TAKE) / 1.5)
    yy = gy - lift
    speed_lines(img, amt, t, yy - 200)
    # images rémanentes (échos) en vol
    flying = t > T_FLY - 0.15
    if flying:
        for j, (pp, rr, ll) in enumerate(hist[-4:][::-1]):
            back = (j + 1) * (speed * dt) * 1.6
            g.draw(img, pp, SX - back, 0, ground=gy, lift=ll, rot=rr, alpha=0.28 - 0.06 * j, tint=(255, 255, 255), record=False)
    shadow = gy + 6 if lift < 900 else None
    g.draw(img, pose, SX, 0, ground=gy + 8, lift=lift, rot=rot, shadow_y=shadow)
    hist.append((pose, rot, lift))
    img.convert("RGB").save(tmp / f"{k:05d}.png")
subprocess.run(["ffmpeg", "-v", "error", "-y", "-r", str(FPS), "-i", str(tmp / "%05d.png"), "-c:v", "libx264", "-pix_fmt",
                "yuv420p", "-crf", "20", OUT], check=True)
print(len(traj), round(T_END, 2), "LEG", round(LEG))
