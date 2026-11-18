"""Infection War (18/11, prototype) : « Can Jonathan stop DIO? ».

Des civils se promènent dans l'arène. Le méchant (DIO) les touche → zombies, qui contaminent à leur tour.
Le héros (Jonathan) touche les zombies → sauvés (dorés). Barre INFECTED / SAVED en haut, coups spéciaux
(Space Ripper Stingy Eyes = rayon qui infecte une ligne ; Sendo Hamon Overdrive = onde qui sauve), le camp qui
a le plus de civils à la fin gagne. Simulation déterministe par graine : `pick_seed` en simule plusieurs et garde
celle avec le plus de changements de leader et une fin serrée.

python3 tools/infect/infection.py <sortie.mp4> [graine]
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import battle, fusion, render  # noqa: E402

L = ROOT / "library"
W, H, FPS = 1080, 1920, 30
AX0, AY0, AS = 60, 430, 960                 # arène carrée
N_CIV = 130
SECONDS = 50.0
END_S = 1.6
FONT = str(ROOT / "tools/money_sim/fonts/anton.woff2")

VILLAIN = {"name": "DIO", "image": L / "_fusion/JoJo Villains/01 DIO P1.jpg", "col": (235, 45, 70),
           "special": "SPACE RIPPER STINGY EYES", "intro": L / "_sounds/jojo_villains/kono dio da.mp3",
           "intro_cut": (0.4, 1.3)}
HERO = {"name": "JONATHAN", "image": L / "_fusion/JoJo/1 JONATHAN.jpg", "col": (255, 200, 60),
        "special": "SENDO HAMON OVERDRIVE"}
MUSIC = L / "_music/JoJo Golden Wind (Il Vento d'Oro).mp3"

NEUTRAL, ZOMBIE, SAVED = 0, 1, 2


def F(sz):
    return ImageFont.truetype(FONT, sz)


# --------------------------------------------------------------------------- simulation

class Sim:
    def __init__(self, seed: int):
        self.rnd = random.Random(seed)
        r = np.random.default_rng(seed)
        self.p = np.column_stack([AX0 + 40 + r.random(N_CIV) * (AS - 80), AY0 + 40 + r.random(N_CIV) * (AS - 80)])
        ang = r.random(N_CIV) * 2 * math.pi
        self.v = np.column_stack([np.cos(ang), np.sin(ang)]) * 55
        self.state = np.zeros(N_CIV, int)
        self.flash = np.zeros(N_CIV)                      # temps depuis le dernier changement (pop)
        self.r_civ = 17
        self.R = 70
        self.balls = []
        for k, (x, y) in enumerate([(AX0 + 220, AY0 + 230), (AX0 + AS - 220, AY0 + AS - 230)]):
            a = self.rnd.uniform(0, 2 * math.pi)
            self.balls.append({"x": x, "y": y, "vx": math.cos(a) * 430, "vy": math.sin(a) * 430})
        self.t = 0.0
        self.events = []                                   # (t, kind, x, y)
        self.specials = []                                 # (t, camp, x, y, angle)
        self.next_special = [self.rnd.uniform(9, 13), self.rnd.uniform(14, 18)]

    def counts(self):
        return int((self.state == ZOMBIE).sum()), int((self.state == SAVED).sum())

    def _nearest(self, x, y, mask):
        idx = np.nonzero(mask)[0]
        if not len(idx):
            return None
        d = (self.p[idx, 0] - x) ** 2 + (self.p[idx, 1] - y) ** 2
        return self.p[idx[int(np.argmin(d))]]

    def step(self, dt):
        self.t += dt
        rnd = self.rnd
        # civils : marche au hasard ; les zombies vont vers le civil le plus proche
        jitter = np.random.default_rng(int(self.t * 1000)).normal(0, 1, (N_CIV, 2)) * 40 * dt
        self.v += jitter
        zi = np.nonzero(self.state == ZOMBIE)[0]
        targets = self.p[(self.state != ZOMBIE)]
        if len(zi) and len(targets):
            dvec = targets[None, :, :] - self.p[zi][:, None, :]
            dd = (dvec ** 2).sum(2)
            j = np.argmin(dd, 1)
            dm = dd[np.arange(len(zi)), j]
            vec = dvec[np.arange(len(zi)), j] / (np.sqrt(dm)[:, None] + 1e-6)
            ok = dm < 260 ** 2
            self.v[zi[ok]] += vec[ok] * 90 * dt
        sp = np.linalg.norm(self.v, axis=1, keepdims=True) + 1e-6
        cap = np.where(self.state[:, None] == ZOMBIE, 72, 58)
        self.v = self.v / sp * np.minimum(sp, cap)
        self.p += self.v * dt
        lo, hi = AX0 + self.r_civ, AX0 + AS - self.r_civ
        for k, (l, h) in enumerate([(lo, hi), (AY0 + self.r_civ, AY0 + AS - self.r_civ)]):
            m = self.p[:, k] < l
            self.p[m, k] = l
            self.v[m, k] = abs(self.v[m, k])
            m = self.p[:, k] > h
            self.p[m, k] = h
            self.v[m, k] = -abs(self.v[m, k])
        self.flash += dt
        # contagion : un zombie qui touche un civil neutre le contamine (pas les sauvés)
        if len(zi):
            neu = np.nonzero(self.state == NEUTRAL)[0]
            if len(neu):
                d = ((self.p[neu][:, None, :] - self.p[zi][None, :, :]) ** 2).sum(2)
                hit = neu[(d < (2 * self.r_civ) ** 2).any(1)]
                for i in hit:
                    if rnd.random() < 0.5 * dt * FPS * 0.35:
                        self._set(i, ZOMBIE, "spread")
        # les deux persos
        for k, b in enumerate(self.balls):
            want = (self.state != ZOMBIE) if k == 0 else (self.state == ZOMBIE)
            tgt = self._nearest(b["x"], b["y"], want)
            if tgt is not None:                           # légère attirance vers ses cibles
                dx, dy = tgt[0] - b["x"], tgt[1] - b["y"]
                dn = math.hypot(dx, dy) + 1e-6
                b["vx"] += dx / dn * 260 * dt
                b["vy"] += dy / dn * 260 * dt
            s = math.hypot(b["vx"], b["vy"])
            sp_ = 430 if k == 0 else 445
            b["vx"], b["vy"] = b["vx"] / s * sp_, b["vy"] / s * sp_
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            for ax, lo_, hi_ in (("x", AX0 + self.R, AX0 + AS - self.R), ("y", AY0 + self.R, AY0 + AS - self.R)):
                if b[ax] < lo_:
                    b[ax] = lo_
                    b["v" + ax] = abs(b["v" + ax])
                elif b[ax] > hi_:
                    b[ax] = hi_
                    b["v" + ax] = -abs(b["v" + ax])
            d2 = (self.p[:, 0] - b["x"]) ** 2 + (self.p[:, 1] - b["y"]) ** 2
            near = np.nonzero(d2 < (self.R + self.r_civ) ** 2)[0]
            for i in near:
                if k == 0 and self.state[i] != ZOMBIE:
                    self._set(i, ZOMBIE, "bite")
                elif k == 1 and self.state[i] == ZOMBIE:
                    self._set(i, SAVED, "save")
        # choc entre les deux persos : ils rebondissent
        a, c = self.balls
        dx, dy = c["x"] - a["x"], c["y"] - a["y"]
        dn = math.hypot(dx, dy)
        if dn < 2 * self.R:
            nx, ny = dx / (dn + 1e-6), dy / (dn + 1e-6)
            for bb, sgn in ((a, -1), (c, 1)):
                vn = bb["vx"] * nx + bb["vy"] * ny
                if vn * sgn < 0:
                    bb["vx"] -= 2 * vn * nx
                    bb["vy"] -= 2 * vn * ny
            over = 2 * self.R - dn
            a["x"] -= nx * over / 2; a["y"] -= ny * over / 2
            c["x"] += nx * over / 2; c["y"] += ny * over / 2
            if not self.events or self.events[-1][1] != "clash" or self.t - self.events[-1][0] > 0.4:
                self.events.append((self.t, "clash", (a["x"] + c["x"]) / 2, (a["y"] + c["y"]) / 2))
        # coups spéciaux : le camp qui est derrière sort le sien
        for k in (0, 1):
            if self.t >= self.next_special[k] and self.t < SECONDS - 6:
                z, s = self.counts()
                behind = (z < s) if k == 0 else (s < z)
                if behind or self.t >= self.next_special[k] + 5:
                    self._special(k)
                    self.next_special[k] = self.t + rnd.uniform(11, 15)

    def _set(self, i, st, kind):
        self.state[i] = st
        self.flash[i] = 0
        self.events.append((self.t, kind, float(self.p[i, 0]), float(self.p[i, 1])))

    def _special(self, k):
        b = self.balls[k]
        if k == 0:                                         # rayon des yeux : infecte une ligne
            tgt = self._nearest(b["x"], b["y"], self.state == SAVED)
            if tgt is None:
                tgt = self._nearest(b["x"], b["y"], self.state == NEUTRAL)
            ang = math.atan2(tgt[1] - b["y"], tgt[0] - b["x"]) if tgt is not None else 0
            ux, uy = math.cos(ang), math.sin(ang)
            rel = self.p - [b["x"], b["y"]]
            along = rel @ [ux, uy]
            perp = np.abs(rel @ [-uy, ux])
            hit = np.nonzero((along > 0) & (perp < 55) & (self.state != ZOMBIE))[0]
            for i in hit:
                self._set(i, ZOMBIE, "beam")
            self.specials.append((self.t, 0, b["x"], b["y"], ang))
        else:                                              # onde d'Hamon : sauve tout autour
            d2 = (self.p[:, 0] - b["x"]) ** 2 + (self.p[:, 1] - b["y"]) ** 2
            hit = np.nonzero((d2 < 270 ** 2) & (self.state == ZOMBIE))[0]
            for i in hit:
                self._set(i, SAVED, "wave")
            self.specials.append((self.t, 1, b["x"], b["y"], 0))


def score(seed):
    s = Sim(seed)
    lead, changes, hist = 0, 0, []
    while s.t < SECONDS:
        s.step(1 / FPS)
        z, v = s.counts()
        cur = 1 if v > z + 2 else (-1 if z > v + 2 else lead)
        if cur != lead and lead != 0:
            changes += 1
        lead = cur
        hist.append((z, v))
    z, v = hist[-1]
    return changes, abs(z - v), z, v


def pick_seed(tries=12, want=None):
    best = None
    for sd in range(1, tries + 1):
        ch, gap, z, v = score(sd)
        if want == "hero" and v <= z or want == "villain" and z <= v:
            continue
        if not 3 <= gap <= 14:
            continue
        key = (min(ch, 5), -gap)
        if best is None or key > best[0]:
            best = (key, sd, ch, gap, z, v)
    return best


# --------------------------------------------------------------------------- dessin

def civ_sprite(state, s=42):
    im = Image.new("RGBA", (s, s + 6), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if state == NEUTRAL:
        body, head, eye = (200, 200, 210), (236, 214, 190), (40, 40, 50)
    elif state == ZOMBIE:
        body, head, eye = (150, 30, 60), (130, 220, 110), (255, 30, 30)
    else:
        body, head, eye = (255, 190, 40), (255, 228, 150), (90, 60, 0)
    d.rounded_rectangle((s * 0.18, s * 0.45, s * 0.82, s + 4), radius=int(s * 0.25), fill=body, outline=(10, 10, 15), width=2)
    d.ellipse((s * 0.22, 1, s * 0.78, s * 0.56), fill=head, outline=(10, 10, 15), width=2)
    for ex in (0.38, 0.62):
        d.ellipse((s * ex - 2.5, s * 0.24, s * ex + 2.5, s * 0.33), fill=eye)
    if state == SAVED:
        d.arc((s * 0.18, -4, s * 0.82, 8), 200, 340, fill=(255, 255, 200), width=2)
    return im


def glow_sprite(col, s=60):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((s * 0.2, s * 0.2, s * 0.8, s * 0.8), fill=col + (150,))
    return im.filter(ImageFilter.GaussianBlur(s * 0.12))


def background():
    bg = Image.new("RGB", (W, H), (12, 6, 18))
    px = np.zeros((H, W, 3), np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    for cx, cy, r, c in ((0.1, 0.12, 520, (120, 20, 60)), (0.95, 0.5, 560, (90, 40, 160)), (0.4, 1.0, 520, (160, 110, 20))):
        g = np.exp(-(((xx - cx * W) ** 2 + (yy - cy * H) ** 2) / (2 * r * r)))[..., None]
        px += g * np.array(c, np.float32) * 0.7
    bg = Image.fromarray(np.clip(np.asarray(bg, np.float32) + px, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(bg)
    d.rectangle((AX0, AY0, AX0 + AS, AY0 + AS), fill=(10, 8, 16))
    for k in range(1, 16):
        x = AX0 + k * AS / 16
        d.line((x, AY0, x, AY0 + AS), fill=(36, 26, 48), width=1)
        d.line((AX0, AY0 + k * AS / 16, AX0 + AS, AY0 + k * AS / 16), fill=(36, 26, 48), width=1)
    d.rectangle((AX0 - 3, AY0 - 3, AX0 + AS + 3, AY0 + AS + 3), outline=(255, 200, 60), width=5)
    return bg


def text_c(d, xy, txt, f, fill, stroke=6):
    d.text(xy, txt, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0))


def draw_title(d, t_left):
    f1, f2 = F(84), F(108)
    w1, w2 = d.textlength("CAN ", font=f1), d.textlength(HERO["name"], font=f1)
    x0 = W / 2 - (w1 + w2) / 2
    d.text((x0, 120), "CAN ", font=f1, fill=(255, 255, 255), anchor="lm", stroke_width=6, stroke_fill=(0, 0, 0))
    d.text((x0 + w1, 120), HERO["name"], font=f1, fill=HERO["col"], anchor="lm", stroke_width=6, stroke_fill=(0, 0, 0))
    text_c(d, (W / 2, 225), f"STOP {VILLAIN['name']}?", f2, VILLAIN["col"], 7)


def draw_bar(d, z, s):
    x0, x1, y0, y1 = AX0, AX0 + AS, 300, 350
    n = N_CIV
    d.rounded_rectangle((x0, y0, x1, y1), radius=24, fill=(70, 70, 80), outline=(0, 0, 0), width=4)
    zw = (x1 - x0) * z / n
    sw = (x1 - x0) * s / n
    if zw > 8:
        d.rounded_rectangle((x0, y0, x0 + zw, y1), radius=24, fill=VILLAIN["col"])
    if sw > 8:
        d.rounded_rectangle((x1 - sw, y0, x1, y1), radius=24, fill=HERO["col"])
    d.rounded_rectangle((x0, y0, x1, y1), radius=24, outline=(0, 0, 0), width=4)
    f = F(46)
    d.text((x0 + 6, y1 + 34), f"INFECTED {z}", font=f, fill=VILLAIN["col"], anchor="lm", stroke_width=5, stroke_fill=(0, 0, 0))
    d.text((x1 - 6, y1 + 34), f"SAVED {s}", font=f, fill=HERO["col"], anchor="rm", stroke_width=5, stroke_fill=(0, 0, 0))


def banner(im, t, txt, sub, col):
    """Gros bandeau du coup spécial (0,9 s)."""
    if t < 0 or t > 0.9:
        return
    k = min(1, t / 0.12) * (1 if t < 0.7 else max(0, (0.9 - t) / 0.2))
    d = ImageDraw.Draw(im, "RGBA")
    y = AY0 + AS / 2
    d.rectangle((0, y - 95, W, y + 95), fill=(0, 0, 0, int(170 * k)))
    f, fs = F(int(92 * (0.85 + 0.15 * min(1, t / 0.12)))), F(48)
    d.text((W / 2, y - 20), txt, font=f, fill=col + (int(255 * k),), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0, int(255 * k)))
    d.text((W / 2, y + 55), sub, font=fs, fill=(255, 255, 255, int(255 * k)), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, int(255 * k)))


def render_video(seed: int, out: Path):
    sim = Sim(seed)
    bg = background()
    spr = {st: civ_sprite(st) for st in (NEUTRAL, ZOMBIE, SAVED)}
    glow = {ZOMBIE: glow_sprite(VILLAIN["col"]), SAVED: glow_sprite(HERO["col"])}
    av = [battle.avatar(str(VILLAIN["image"]), 2 * sim.R, VILLAIN["col"]), battle.avatar(str(HERO["image"]), 2 * sim.R, HERO["col"])]
    halo = [glow_sprite(VILLAIN["col"], 260), glow_sprite(HERO["col"], 260)]
    tmp = out.with_suffix(".raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    trails = [[], []]
    nframes = int(SECONDS * FPS)
    ring_fx = []                                           # (t, x, y, col)
    for fi in range(nframes):
        if fi:
            sim.step(1 / FPS)
        t = sim.t
        im = bg.copy()
        d = ImageDraw.Draw(im, "RGBA")
        z, s = sim.counts()
        draw_title(d, SECONDS - t)
        draw_bar(d, z, s)
        # civils
        for i in range(N_CIV):
            st = int(sim.state[i])
            x, y = sim.p[i]
            sc = 1.0
            if sim.flash[i] < 0.18 and st != NEUTRAL:
                sc = 1 + 0.6 * math.sin(sim.flash[i] / 0.18 * math.pi)
            if st in glow:
                g = glow[st]
                im.paste(g, (int(x - 30), int(y - 30)), g)
            sp = spr[st]
            if sc != 1.0:
                sp = sp.resize((int(sp.width * sc), int(sp.height * sc)))
            im.paste(sp, (int(x - sp.width / 2), int(y - sp.height / 2)), sp)
        # coups spéciaux
        for (ts, k, x, y, ang) in sim.specials:
            dt = t - ts
            if 0 <= dt < 0.6:
                if k == 0:
                    a = int(255 * (1 - dt / 0.6))
                    ex, ey = x + math.cos(ang) * 1500, y + math.sin(ang) * 1500
                    for w_, c in ((44, VILLAIN["col"] + (a // 2,)), (18, (255, 230, 230, a))):
                        d.line((x, y, ex, ey), fill=c, width=w_)
                else:
                    rr = 60 + 260 * min(1, dt / 0.35)
                    a = int(230 * (1 - dt / 0.6))
                    d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=HERO["col"] + (a,), width=14)
                    d.ellipse((x - rr * 0.7, y - rr * 0.7, x + rr * 0.7, y + rr * 0.7), outline=(255, 250, 200, a // 2), width=6)
        # persos + traînées
        for k, b in enumerate(sim.balls):
            trails[k].append((b["x"], b["y"]))
            trails[k] = trails[k][-8:]
            for j, (tx, ty) in enumerate(trails[k][:-1]):
                rr = sim.R * (0.35 + 0.08 * j)
                col = (VILLAIN if k == 0 else HERO)["col"]
                d.ellipse((tx - rr, ty - rr, tx + rr, ty + rr), fill=col + (25 + 10 * j,))
            hl = halo[k]
            im.paste(hl, (int(b["x"] - 130), int(b["y"] - 130)), hl)
            im.paste(av[k], (int(b["x"] - sim.R), int(b["y"] - sim.R)), av[k])
            nm = (VILLAIN if k == 0 else HERO)["name"]
            d.text((b["x"], b["y"] - sim.R - 22), nm, font=F(34), fill=(255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
        for (ts, k, x, y, ang) in sim.specials:
            info = VILLAIN if k == 0 else HERO
            banner(im, t - ts, info["special"], info["name"], info["col"])
        # dernières secondes : compte à rebours
        left = SECONDS - t
        if left <= 10:
            fz = F(int(70 + 20 * (1 - (left % 1))))
            d.text((W / 2, AY0 + AS + 90), f"{max(0, math.ceil(left))}", font=fz, fill=(255, 80, 80), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0))
        else:
            d.text((W / 2, AY0 + AS + 90), "WHO WINS? COMMENT", font=F(54), fill=(255, 255, 255), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))
        ff.stdin.write(im.tobytes())
    # écran final
    z, s = sim.counts()
    win = HERO if s > z else VILLAIN
    wk = 1 if s > z else 0
    last = bg.copy()
    for fi in range(int(END_S * FPS)):
        k = min(1, fi / 8)
        im = Image.blend(last, Image.new("RGB", (W, H), (0, 0, 0)), 0.7 * k)
        d = ImageDraw.Draw(im)
        big = battle.avatar(str(win["image"]), int(380 * (0.6 + 0.4 * k)), win["col"])
        im.paste(big, (W // 2 - big.width // 2, int(H * 0.42) - big.height // 2), big)
        text_c(d, (W / 2, H * 0.25), f"{win['name']} WINS", F(120), win["col"], 8)
        text_c(d, (W / 2, H * 0.58), f"{s} SAVED  ·  {z} INFECTED", F(60), (255, 255, 255), 5)
        ff.stdin.write(im.tobytes())
    ff.stdin.close()
    ff.wait()
    total = SECONDS + END_S
    audio = soundtrack(sim, total, wk)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, audio)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink()
    wav.unlink()
    render.stamp_video(out)
    return out, win["name"], z, s


# --------------------------------------------------------------------------- son

RATE = fusion.RATE
PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]


def tone(freq, dur, decay=10, harm=(1, 0.5, 0.25)):
    t = np.arange(int(dur * RATE)) / RATE
    x = sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harm))
    return (x * np.exp(-t * decay)).astype(np.float32)


def bite():
    t = np.arange(int(0.09 * RATE)) / RATE
    f = 220 * np.exp(-t * 18) + 70
    x = np.sin(2 * np.pi * np.cumsum(f) / RATE) * np.exp(-t * 30)
    x += np.random.default_rng(1).normal(0, 0.25, len(t)) * np.exp(-t * 60)
    return x.astype(np.float32)


def add(buf, snd, t, g):
    i = int(t * RATE)
    if i >= len(buf):
        return
    n = min(len(snd), len(buf) - i)
    buf[i:i + n] += snd[:n] * g


def soundtrack(sim, total, winner):
    buf = np.zeros(int(total * RATE) + RATE, np.float32)
    b = bite()
    last = {"bite": -1, "save": -1}
    combo, last_save = 0, -9
    for (t, kind, x, y) in sim.events:
        if kind in ("bite", "spread", "beam"):
            if t - last["bite"] > 0.07:
                add(buf, b, t, 0.35 if kind != "spread" else 0.18)
                last["bite"] = t
        elif kind in ("save", "wave"):
            if t - last["save"] > 0.06:
                combo = combo + 1 if t - last_save < 0.45 else 0
                last_save = t
                n = PENTA[min(combo, len(PENTA) - 1)]
                add(buf, tone(523.25 * 2 ** (n / 12), 0.35, 9), t, 0.22)
                last["save"] = t
        elif kind == "clash":
            add(buf, tone(90, 0.4, 7, (1, 0.6, 0.3)), t, 0.5)
    for (ts, k, x, y, ang) in sim.specials:
        if k == 0:
            t_ = np.arange(int(0.6 * RATE)) / RATE
            zap = np.sign(np.sin(2 * np.pi * (900 - 500 * t_) * t_)) * np.exp(-t_ * 4) * 0.25
            add(buf, zap.astype(np.float32), ts, 0.6)
        else:
            for j, n in enumerate((0, 4, 7, 12)):
                add(buf, tone(392 * 2 ** (n / 12), 0.6, 5), ts + j * 0.05, 0.25)
    if VILLAIN.get("intro") and Path(VILLAIN["intro"]).is_file():
        s = fusion.load_sound(VILLAIN["intro"])
        a, d = VILLAIN["intro_cut"]
        add(buf, s[int(a * RATE): int((a + d) * RATE)], 0.05, 0.7)
    for j, n in enumerate((0, 4, 7, 12, 16)):            # fanfare de fin
        add(buf, tone(392 * 2 ** (n / 12), 0.8, 3), SECONDS + j * 0.08, 0.25)
    if MUSIC.is_file():
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(MUSIC), "-t", str(total), "-ac", "1", "-ar", str(RATE),
                            "-f", "f32le", "-"], capture_output=True)
        m = np.frombuffer(r.stdout, np.float32)
        m = m / (np.abs(m).max() + 1e-6)
        add(buf, m, 0, 0.16)
    buf = np.tanh(buf * 1.2) / math.tanh(1.2) * 0.5
    return buf


if __name__ == "__main__":
    out = Path(sys.argv[1])
    if len(sys.argv) > 2:
        seed = int(sys.argv[2])
    else:
        best = pick_seed()
        seed = best[1]
        print("graine", best)
    print(render_video(seed, out))
