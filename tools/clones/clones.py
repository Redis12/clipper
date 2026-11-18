"""Shadow Clone Multiplier (18/11) : « Can 1 Naruto become 10,000 clones in 60 seconds? ».

Un Naruto tombe dans une planche à clous coupée par des rangées de portes ×2 / ×3 / ×5 (vertes) et
CHIDORI ÷2 (rouges, Sasuke). Chaque clone qui passe une porte se multiplie (ou disparaît), ceux qui touchent le
fond remontent en haut (« pouf ») et repassent les portes → croissance exponentielle. Au-delà de MAX_VIS clones
visibles, chaque icône compte pour plusieurs (poids), le compteur reste exact. Formes de Naruto aux paliers
(Sage Mode, Kyûbi, Kurama, Six Paths, Baryon à 10 000). Compte à rebours de 60 s ; graine choisie pour une fin
serrée (réussite à la dernière seconde ou échec de peu).

python3 tools/clones/clones.py <sortie.mp4> [graine] [--fail]
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
BX0, BX1, BY0, BY1 = 70, 1010, 430, 1560          # planche
SECONDS = 60.0
END_S = 1.6
TARGET = 10_000
MAX_VIS = 650
R_BALL = 22
G = 1500.0
FONT = str(ROOT / "tools/money_sim/fonts/anton.woff2")
NF = L / "_fusion/Naruto"
FORMS = [(1, "KID NARUTO", NF / "1 Naruto Kid.jpg"), (100, "SAGE MODE", NF / "5 toad sage.webp"),
         (800, "NINE-TAILS CHAKRA MODE", NF / "6 KCM.jpg"), (2500, "KURAMA MODE", NF / "7 KURAMA MODE.jpg"),
         (5500, "SIX PATHS SAGE MODE", NF / "8 SIX PATH.jpg"), (TARGET, "BARYON MODE", NF / "9 Baryon Mode.jpg")]
SASUKE = L / "_fusion/Sasuke/4 Mangekyo.jpg"
SFX = L / "_sfx/Naruto SFX"
MUSIC = L / "_music/Naruto Shippuden OST 1 - Track 26 - Keisei Gyakuten ( Reverse Situation ).mp3"
ORANGE, RED, GREEN = (255, 150, 30), (235, 50, 60), (70, 220, 110)

# rangées de portes : y, liste de (largeur relative, multiplicateur ; 0 = Chidori ÷2)
GATES = [(600, [(1, 2), (1, 0), (1, 3), (1, 2)]),
         (900, [(1, 0), (1, 2), (1.2, 5), (1, 0), (1, 2)]),
         (1220, [(1, 3), (1, 0), (1, 2), (1, 0), (1, 3)])]


def F(sz):
    return ImageFont.truetype(FONT, sz)


def gate_zones():
    out = []
    for y, zs in GATES:
        tot = sum(w for w, _ in zs)
        x = BX0
        row = []
        for w, m in zs:
            x1 = x + (BX1 - BX0) * w / tot
            row.append((x, x1, m))
            x = x1
        out.append((y, row))
    return out


ZONES = gate_zones()


def pegs():
    pts = []
    for k, y in enumerate(range(520, 1500, 92)):
        if any(abs(y - gy) < 50 for gy, _ in GATES):
            continue
        off = 47 if k % 2 else 0
        for x in range(BX0 + 50 + off, BX1 - 30, 94):
            pts.append((x, y))
    return np.array(pts, float)


PEGS = pegs()


class Sim:
    def __init__(self, seed: int, luck: float = 1.0):
        self.rnd = np.random.default_rng(seed)
        self.luck = luck
        self.p = np.array([[W / 2 + self.rnd.normal(0, 20), BY0 + 40]])
        self.v = np.array([[self.rnd.normal(0, 60), 0.0]])
        self.w = np.array([1.0])                         # poids (clones représentés)
        self.flash = np.array([0.0])
        self.t = 0.0
        self.events = []                                 # (t, kind, x, y, value)
        self.total = 1.0
        self.hist = []

    def goal(self, t):
        """Courbe visée : luck > 1 = un peu en avance (réussite), < 1 = en retard (échec de peu)."""
        x = min(1.0, t / (SECONDS - 1.2))
        g = TARGET ** (x ** 0.6) * self.luck
        dip = 0.45 * math.exp(-((x - 0.74) / 0.05) ** 2)       # le gros Chidori : on recule
        return max(1.0, g * (1 - dip))

    def step(self, dt):
        self.t += dt
        n = len(self.p)
        if not n:
            return
        prev_y = self.p[:, 1].copy()
        self.v[:, 1] += G * dt
        self.v *= 0.999
        self.p += self.v * dt
        self.flash += dt
        # murs
        m = self.p[:, 0] < BX0 + R_BALL
        self.p[m, 0] = BX0 + R_BALL; self.v[m, 0] = np.abs(self.v[m, 0]) * 0.7
        m = self.p[:, 0] > BX1 - R_BALL
        self.p[m, 0] = BX1 - R_BALL; self.v[m, 0] = -np.abs(self.v[m, 0]) * 0.7
        # clous
        d = self.p[:, None, :] - PEGS[None, :, :]
        dd = np.sqrt((d ** 2).sum(2))
        hit = dd < (R_BALL + 7)
        if hit.any():
            bi, pi = np.nonzero(hit)
            nrm = d[bi, pi] / (dd[bi, pi][:, None] + 1e-6)
            vn = (self.v[bi] * nrm).sum(1)
            ok = vn < 0
            bi, nrm, vn = bi[ok], nrm[ok], vn[ok]
            self.v[bi] -= (1.55 * vn)[:, None] * nrm
            self.v[bi, 0] += self.rnd.normal(0, 35, len(bi))
            self.p[bi] += nrm * 2
        # pilotage discret : la courbe visée (10 000 pile à la fin, avec un creux vers 75 % du temps)
        ratio = self.total / max(1.0, self.goal(self.t))
        q = min(1.0, max(0.03, 0.35 / max(ratio, 1e-3) ** 2))
        chid_p = 0.15 if ratio < 0.9 else min(1.0, 0.6 * ratio)
        # portes
        new_p, new_v, new_w = [], [], []
        dead = np.zeros(len(self.p), bool)
        for gy, row in ZONES:
            cross = np.nonzero((prev_y < gy) & (self.p[:, 1] >= gy))[0]
            for i in cross:
                x = self.p[i, 0]
                mlt = next((m for x0, x1, m in row if x0 <= x < x1), 1)
                if mlt == 0:
                    if len(self.p) > 2 and self.rnd.random() < chid_p:
                        self.w[i] *= 0.5
                        if self.w[i] < 1 or self.rnd.random() < 0.5:
                            dead[i] = True
                        self.events.append((self.t, "chidori", x, gy, 0))
                    continue
                if self.rnd.random() > q:
                    continue
                # multiplication : on crée des clones (ou on alourdit si trop d'icônes à l'écran)
                extra = mlt - 1
                room = MAX_VIS - (len(self.p) + len(new_p))
                spawn = min(extra, max(0, room))
                if spawn < extra:
                    self.w[i] *= (extra - spawn + 1)
                for k in range(spawn):
                    ang = -math.pi / 2 + (k + 1 - spawn / 2) * 0.5 + self.rnd.normal(0, 0.2)
                    new_p.append(self.p[i] + [self.rnd.normal(0, 6), 4])
                    new_v.append([self.v[i, 0] + math.cos(ang) * 160, max(60, self.v[i, 1] * 0.5)])
                    new_w.append(self.w[i])
                self.flash[i] = 0
                self.events.append((self.t, "mult", x, gy, mlt))
        # chidori : on retire les morts
        keep = ~dead
        self.p, self.v, self.w, self.flash = self.p[keep], self.v[keep], self.w[keep], self.flash[keep]
        if new_p:
            self.p = np.vstack([self.p, new_p])
            self.v = np.vstack([self.v, new_v])
            self.w = np.concatenate([self.w, new_w])
            self.flash = np.concatenate([self.flash, np.zeros(len(new_p))])
        # le fond : retour en haut
        bot = np.nonzero(self.p[:, 1] > BY1 - R_BALL)[0]
        if len(bot):
            for i in bot[:6]:
                self.events.append((self.t, "warp", self.p[i, 0], BY1, 0))
            self.p[bot, 1] = BY0 + 30 + self.rnd.random(len(bot)) * 30
            self.p[bot, 0] = W / 2 + self.rnd.normal(0, 140, len(bot))
            self.v[bot] = np.column_stack([self.rnd.normal(0, 90, len(bot)), np.zeros(len(bot))])
            self.flash[bot] = 0
        # sécurité : jamais 0 clone
        if not len(self.p):
            self.p = np.array([[W / 2, BY0 + 40]]); self.v = np.array([[0.0, 0.0]])
            self.w = np.array([1.0]); self.flash = np.array([0.0])
        self.total = float(self.w.sum())
        self.hist.append(self.total)


def run(seed, luck):
    s = Sim(seed, luck)
    reach = None
    while s.t < SECONDS:
        s.step(1 / FPS)
        if reach is None and s.total >= TARGET:
            reach = s.t
    return reach, s.total


def pick(fail=False, tries=10):
    best = None
    for sd in range(1, tries + 1):
        for luck in ((0.9, 0.93, 0.96) if fail else (1.0, 1.03, 1.06)):
            reach, tot = run(sd, luck)
            if fail:
                ok = reach is None and 0.85 * TARGET <= tot < TARGET
                key = tot
            else:
                ok = reach is not None and SECONDS - 2.5 <= reach <= SECONDS - 0.2
                key = reach or 0
            if ok and (best is None or key > best[0]):
                best = (key, sd, luck, reach, tot)
    return best


# --------------------------------------------------------------------------- rendu

def background():
    yy, xx = np.mgrid[0:H, 0:W]
    px = np.zeros((H, W, 3), np.float32) + np.array([14, 8, 6], np.float32)
    for cx, cy, r, c in ((0.15, 0.1, 520, (170, 70, 10)), (0.9, 0.55, 560, (120, 30, 20)), (0.5, 1.0, 600, (190, 110, 20))):
        g = np.exp(-(((xx - cx * W) ** 2 + (yy - cy * H) ** 2) / (2 * r * r)))[..., None]
        px += g * np.array(c, np.float32) * 0.65
    bg = Image.fromarray(np.clip(px, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(bg, "RGBA")
    d.rectangle((BX0, BY0, BX1, BY1), fill=(10, 8, 12, 235))
    for x, y in PEGS:
        d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(200, 200, 215), outline=(60, 60, 70), width=2)
    fz = F(44)
    for gy, row in ZONES:
        for x0, x1, m in row:
            col = GREEN if m else RED
            d.rectangle((x0 + 3, gy - 30, x1 - 3, gy + 30), fill=col + (70,), outline=col + (255,), width=4)
            d.text(((x0 + x1) / 2, gy), f"×{m}" if m else "CHIDORI", font=fz if m else F(30), fill=(255, 255, 255),
                   anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0))
    d.rectangle((BX0 - 3, BY0 - 3, BX1 + 3, BY1 + 3), outline=ORANGE, width=5)
    return bg


def icon(path, r, col):
    return battle.avatar(str(path), 2 * r, col)


def text_c(d, xy, txt, f, fill, stroke=6):
    d.text(xy, txt, font=f, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=(0, 0, 0))


def form_at(total):
    k = 0
    for i, (th, _, _) in enumerate(FORMS):
        if total >= th:
            k = i
    return k


def render_video(seed, luck, out: Path):
    sim = Sim(seed, luck)
    bg = background()
    icons = [icon(p, R_BALL, ORANGE) for _, _, p in FORMS]
    big = [icon(p, 70, ORANGE) for _, _, p in FORMS]
    sas = icon(SASUKE, 46, RED)
    glow = Image.new("RGBA", (90, 90), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((20, 20, 70, 70), fill=ORANGE + (120,))
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    tmp = out.with_suffix(".raw.mp4")
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                           "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    form_t = {0: 0.0}
    reach = None
    smokes = []
    shown_sas = set()
    hero_big = icon(FORMS[0][2], 150, ORANGE)
    nframes = int(SECONDS * FPS)
    for fi in range(nframes):
        if fi:
            sim.step(1 / FPS)
        t = sim.t
        if reach is None and sim.total >= TARGET:
            reach = t
        fk = form_at(sim.total)
        if fk not in form_t:
            form_t[fk] = t
        im = bg.copy()
        d = ImageDraw.Draw(im, "RGBA")
        # titre + compte à rebours
        left = max(0.0, SECONDS - t)
        text_c(d, (W / 2, 95), "CAN 1 NARUTO BECOME", F(74), (255, 255, 255))
        text_c(d, (W / 2, 190), "10,000 CLONES", F(104), ORANGE, 7)
        col = (255, 70, 70) if left < 10 else (255, 255, 255)
        text_c(d, (W / 2, 290), f"IN {math.ceil(left)} SECONDS?", F(80 if left >= 10 else int(80 + 10 * (1 - left % 1))), col)
        # compteur + barre
        tot = int(min(sim.total, 999_999))
        text_c(d, (W / 2, 378), f"{tot:,} CLONE" + ("S" if tot > 1 else ""), F(64), (255, 230, 120), 5)
        # zones touchées : flash
        for (te, kind, x, y, m) in sim.events[-60:]:
            dt_ = t - te
            if kind == "mult" and 0 <= dt_ < 0.25:
                a = int(200 * (1 - dt_ / 0.25))
                d.text((x, y - 50 - 80 * dt_), f"×{m}", font=F(40), fill=(120, 255, 150, a), anchor="mm",
                       stroke_width=3, stroke_fill=(0, 0, 0, a))
            elif kind == "chidori" and 0 <= dt_ < 0.35:
                a = int(255 * (1 - dt_ / 0.35))
                for k in range(3):
                    xs = [x + random.Random(int(te * 1000) + k).uniform(-60, 60) for _ in range(5)]
                    pts = [(xs[j], y - 60 + 30 * j) for j in range(5)]
                    d.line(pts, fill=(150, 200, 255, a), width=4)
                zx = next(((x0 + x1) / 2 for gy_, row in ZONES if gy_ == y for x0, x1, m_ in row if x0 <= x < x1), x)
                key = (round(zx), y)
                if key not in shown_sas:
                    shown_sas.add(key)
                    im.paste(sas, (int(zx - 46), int(y - 125)), sas)
        shown_sas.clear()
        # clones
        ic = icons[fk]
        for i in range(len(sim.p)):
            x, y = sim.p[i]
            if sim.flash[i] < 0.15:
                im.paste(glow, (int(x - 45), int(y - 45)), glow)
            im.paste(ic, (int(x - R_BALL), int(y - R_BALL)), ic)
        # fumée « pouf » au retour en haut
        for (te, kind, x, y, m) in sim.events[-40:]:
            if kind == "warp" and 0 <= t - te < 0.3:
                k = (t - te) / 0.3
                rr = 16 + 30 * k
                d.ellipse((x - rr, y - 20 - rr, x + rr, y - 20 + rr), fill=(240, 240, 240, int(140 * (1 - k))))
        # changement de forme : bandeau
        tf = t - form_t[fk]
        if fk > 0 and tf < 1.3:
            k = min(1, tf / 0.15) * (1 if tf < 1.0 else (1.3 - tf) / 0.3)
            yb = BY0 + (BY1 - BY0) * 0.5
            d.rectangle((0, yb - 110, W, yb + 110), fill=(0, 0, 0, int(180 * k)))
            b = big[fk]
            im.paste(b, (W // 2 - 70, int(yb - 95)), b)
            d.text((W / 2, yb + 75), FORMS[fk][1] + "!", font=F(66), fill=ORANGE + (int(255 * k),), anchor="mm",
                   stroke_width=6, stroke_fill=(0, 0, 0, int(255 * k)))
        # accroche (1re seconde) : Naruto en grand + « KAGE BUNSHIN NO JUTSU! »
        if t < 1.3:
            k = 1 if t < 0.9 else (1.3 - t) / 0.4
            hb = hero_big if k >= 1 else hero_big.copy()
            if k < 1:
                hb.putalpha(hb.getchannel("A").point(lambda a: int(a * k)))
            im.paste(hb, (W // 2 - 150, BY0 + 140), hb)
            d.text((W / 2, BY0 + 500), "KAGE BUNSHIN", font=F(96), fill=ORANGE + (int(255 * k),), anchor="mm",
                   stroke_width=7, stroke_fill=(0, 0, 0, int(255 * k)))
            d.text((W / 2, BY0 + 600), "NO JUTSU!", font=F(96), fill=(255, 255, 255, int(255 * k)), anchor="mm",
                   stroke_width=7, stroke_fill=(0, 0, 0, int(255 * k)))
        # bas : forme actuelle
        d.text((W / 2, BY1 + 70), f"FORM: {FORMS[fk][1]}", font=F(48), fill=(255, 255, 255), anchor="mm",
               stroke_width=5, stroke_fill=(0, 0, 0))
        ff.stdin.write(im.tobytes())
        if reach is not None and t >= reach + 0.25:
            break
    win = reach is not None
    last = im.copy()
    for fi in range(int(END_S * FPS)):
        k = min(1, fi / 8)
        im = Image.blend(last, Image.new("RGB", (W, H), (0, 0, 0)), 0.72 * k)
        d = ImageDraw.Draw(im)
        if win:
            b = icon(FORMS[-1][2], int(200 * (0.6 + 0.4 * k)), ORANGE)
            im.paste(b, (W // 2 - b.width // 2, int(H * 0.45) - b.height // 2), b)
            text_c(d, (W / 2, H * 0.24), "10,000 CLONES!", F(118), ORANGE, 8)
            text_c(d, (W / 2, H * 0.62), f"IN {reach:.1f} SECONDS", F(70), (255, 255, 255), 6)
        else:
            text_c(d, (W / 2, H * 0.32), "TIME'S UP", F(130), (255, 70, 70), 8)
            text_c(d, (W / 2, H * 0.45), f"{int(sim.total):,} / 10,000", F(90), (255, 255, 255), 6)
            text_c(d, (W / 2, H * 0.55), f"{100 * sim.total / TARGET:.0f}% — SO CLOSE", F(64), ORANGE, 5)
        ff.stdin.write(im.tobytes())
    ff.stdin.close()
    ff.wait()
    dur = (fi + 1) / FPS + (sim.t + 1 / FPS)
    audio = soundtrack(sim, form_t, sim.t + END_S + 0.2, win)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, audio)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "192k", "-shortest", str(out)], check=True)
    tmp.unlink(); wav.unlink()
    render.stamp_video(out)
    return out, win, reach, sim.total


# --------------------------------------------------------------------------- son

RATE = fusion.RATE
PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28]


def tone(freq, dur, decay=10, harm=(1, 0.45, 0.2)):
    t = np.arange(int(dur * RATE)) / RATE
    x = sum(a * np.sin(2 * np.pi * freq * (i + 1) * t) for i, a in enumerate(harm))
    return (x * np.exp(-t * decay)).astype(np.float32)


def add(buf, snd, t, g):
    i = int(t * RATE)
    if i < 0 or i >= len(buf):
        return
    n = min(len(snd), len(buf) - i)
    buf[i:i + n] += snd[:n] * g


def sfx(name, a=0.0, d=None):
    p = next((f for f in SFX.iterdir() if name.lower() in f.name.lower()), None) if SFX.is_dir() else None
    s = fusion.load_sound(p) if p else np.zeros(10, np.float32)
    s = s[int(a * RATE):]
    return s[: int(d * RATE)] if d else s


def soundtrack(sim, form_t, total, win):
    buf = np.zeros(int(total * RATE) + RATE, np.float32)
    last = -1
    for (t, kind, x, y, m) in sim.events:
        if kind == "mult" and t - last > 0.05:
            lvl = min(len(PENTA) - 1, int(math.log10(max(1, sim.hist[min(len(sim.hist) - 1, int(t * FPS))])) * 3))
            add(buf, tone(392 * 2 ** (PENTA[lvl] / 12), 0.25, 12), t, 0.18)
            last = t
    lastc = -1
    chid = sfx("chidori", 0, 0.5)
    for (t, kind, x, y, m) in sim.events:
        if kind == "chidori" and t - lastc > 0.5:
            add(buf, chid, t, 0.35)
            lastc = t
    add(buf, sfx("kage bunshin"), 0.0, 0.9)
    for k, t in form_t.items():
        if k > 0:
            for j, n in enumerate((0, 4, 7, 12)):
                add(buf, tone(330 * 2 ** (n / 12), 0.7, 4), t + j * 0.05, 0.25)
    if win:
        add(buf, sfx("yoooo", 0, 2.0), sim.t + 0.1, 0.8)
    else:
        add(buf, tone(140, 1.2, 2, (1, 0.8, 0.5)), sim.t + 0.1, 0.4)
    if MUSIC.is_file():
        r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(MUSIC), "-t", str(total), "-ac", "1", "-ar", str(RATE),
                            "-f", "f32le", "-"], capture_output=True)
        mu = np.frombuffer(r.stdout, np.float32)
        add(buf, mu / (np.abs(mu).max() + 1e-6), 0, 0.2)
    return np.tanh(buf * 1.2) / math.tanh(1.2) * 0.5


if __name__ == "__main__":
    out = Path(sys.argv[1])
    fail = "--fail" in sys.argv
    args = [a for a in sys.argv[2:] if not a.startswith("--")]
    if args:
        seed, luck = int(args[0]), float(args[1]) if len(args) > 1 else 1.0
    else:
        b = pick(fail)
        print("choix", b)
        seed, luck = b[1], b[2]
    print(render_video(seed, luck, out))
