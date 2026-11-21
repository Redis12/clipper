"""« Spiral Kamehameha » (21/11) : d'après une vidéo virale (balle qui roule dans une spirale néon, porte « xN » qui la
multiplie, chaque balle croque le disque au bout du sillon). Ici : Goku lance un Kamehameha par manche, la porte le
multiplie, chaque boule d'énergie croque un morceau du boss (image ronde) ; à chaque manche Goku passe à sa forme
suivante et la couleur du Kamehameha change. Fin quand le boss est entièrement effacé.

python3 tools/kame/spiral.py <sortie.mp4> [boss=library/_fusion/DB Super Villains/10 JIREN.jpg] [nom=JIREN]
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from clipper.slides import fusion, render  # noqa: E402

W, H, FPS = 1080, 1920, 30
L = ROOT / "library"
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")
MONT = str(ROOT / "tools/money_sim/fonts/mont800.woff2")
SFX = L / "_sfx/Dragon Ball SFX/Dragon Ball Z Sounds"

# formes de Goku : (image, nom affiché, couleur du Kamehameha, multiplicateur de la porte, durée de la manche)
FORMS = [
    ("Kid Goku.webp", "KID GOKU", (120, 200, 255), 2, 3.4),
    ("1 Base.png", "BASE GOKU", (60, 150, 255), 3, 3.9),
    ("Goku Kaioken.jpg", "KAIOKEN", (255, 60, 60), 4, 4.3),
    ("2 SSJ1.jpg", "SUPER SAIYAN", (255, 210, 40), 5, 4.6),
    ("3 SSJ2.jpg", "SUPER SAIYAN 2", (255, 235, 90), 6, 4.9),
    ("4 SSJ3.jpg", "SUPER SAIYAN 3", (255, 170, 20), 8, 5.2),
    ("6 SSJGOD.jpg", "SUPER SAIYAN GOD", (255, 40, 90), 10, 5.5),
    ("5 SSJBLUE.jpg", "SUPER SAIYAN BLUE", (40, 220, 255), 12, 5.8),
    ("7 ui.jpg", "ULTRA INSTINCT", (200, 215, 255), 15, 6.0),
    ("8 uimastered.jpg", "MASTERED ULTRA INSTINCT", (245, 245, 255), 20, 6.4),
]


def font(p, s):
    return ImageFont.truetype(p, int(s))


class Spiral:
    """Chemin en spirale d'Archimède, paramétré par la longueur d'arc."""

    def __init__(self, cx, cy, r0, b, rmin):
        self.cx, self.cy, self.r0, self.b = cx, cy, r0, b
        phis = np.linspace(0, (r0 - rmin) / b * 2 * math.pi, 20000)
        r = r0 - b * phis / (2 * math.pi)
        a = 5 * math.pi / 4 - phis                        # départ en haut à gauche, puis gauche → bas → droite → haut
        self.x = cx + r * np.cos(a)
        self.y = cy + r * np.sin(a)
        self.phi, self.r, self.a = phis, r, a
        seg = np.hypot(np.diff(self.x), np.diff(self.y))
        self.s = np.concatenate([[0], np.cumsum(seg)])
        self.L = float(self.s[-1])

    def at(self, s):
        s = min(max(s, 0.0), self.L)
        return float(np.interp(s, self.s, self.x)), float(np.interp(s, self.s, self.y))

    def s_of_phi(self, phi):
        return float(np.interp(phi, self.phi, self.s))

    def pts(self, s0, s1, step=6.0):
        n = max(2, int((s1 - s0) / step))
        return [self.at(s0 + (s1 - s0) * i / (n - 1)) for i in range(n)]

    def wall(self, off, phi_end=None):
        """Mur néon = la spirale décalée d'une demi-largeur de sillon vers l'extérieur."""
        ph = self.phi if phi_end is None else self.phi[self.phi <= phi_end]
        r = self.r0 + off - self.b * ph / (2 * math.pi)
        a = 5 * math.pi / 4 - ph
        k = max(1, len(ph) // 1500)
        return list(zip((self.cx + r * np.cos(a))[::k], (self.cy + r * np.sin(a))[::k]))


def tint_ball(r, col, white=0.55):
    """Boule d'énergie : halo de la couleur, cœur blanc."""
    S = int(r * 4)
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = S / 2
    d.ellipse((c - r * 1.7, c - r * 1.7, c + r * 1.7, c + r * 1.7), fill=col + (90,))
    im = im.filter(ImageFilter.GaussianBlur(r * 0.45))
    d = ImageDraw.Draw(im)
    d.ellipse((c - r, c - r, c + r, c + r), fill=col + (255,))
    d.ellipse((c - r * white, c - r * white, c + r * white, c + r * white), fill=(255, 255, 255, 255))
    d.ellipse((c - r * 0.75, c - r * 0.85, c - r * 0.2, c - r * 0.35), fill=(255, 255, 255, 160))
    return im


def note(f, rate, dur=0.18):
    t = np.arange(int(dur * rate)) / rate
    env = np.exp(-t * 22) * np.minimum(1, t / 0.002)
    x = np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 60) + 0.18 * np.sin(2 * np.pi * f * 2 * t)
    return (x * env).astype(np.float32)


def load(path, rate):
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(rate), "-"],
                             capture_output=True, check=True).stdout
        return np.frombuffer(raw, np.float32).copy()
    except Exception:
        return None


def main():
    out = Path(sys.argv[1])
    boss_path = Path(sys.argv[2]) if len(sys.argv) > 2 else L / "_fusion/DB Super Villains/10 JIREN.jpg"
    boss_name = sys.argv[3] if len(sys.argv) > 3 else "JIREN"
    rnd = random.Random(7)
    k = W / 1080
    CX, CY = W / 2, H * 0.535
    R = 430 * k                                           # rayon du boss
    b = 84 * k                                            # largeur du sillon
    br = 27 * k                                           # rayon d'une boule
    sp = Spiral(CX, CY, R + b * 0.5, b, b * 0.55)
    RD = R + b * 0.98                                     # le boss remplit jusqu'au mur extérieur : on le croque dès le début
    s_gate = sp.s_of_phi(math.pi * 1.25)                  # la porte : en bas, sur la 1re boucle
    s_eat0 = sp.s_of_phi(math.pi * 1.42)
    GOKU = (W * 0.13, H * 0.30)                           # Goku en haut à gauche, au-dessus de l'entrée
    entry = sp.at(0)

    # ---------------------------------------------------------------- planning (déterministe)
    M = sum(f[3] for f in FORMS)
    delta = (sp.L - s_eat0) / M                           # longueur croquée par boule : le dernier tombe pile au centre
    gap = 2 * br * 1.08                                   # écart entre 2 boules du train
    events = []                                           # (t, kind, data)
    balls = []                                            # (t_spawn_gate, t_eat, s_eat_end, form, v) pour chaque boule
    t = 0.25
    s_eat = s_eat0
    rounds = []
    for fi, (_img, _nm, col, mult, dur) in enumerate(FORMS):
        fly = 0.32
        # vitesse telle que la dernière boule mange à t + dur - 0.25
        travel = (s_eat + (mult - 1) * (gap + delta)) + mult * delta * 0.0
        v = travel / max(0.8, dur - fly - 0.35)
        t_launch = t
        t_path = t_launch + fly
        t_gate = t_path + s_gate / v
        rows = []
        for i in range(mult):
            ts = t_gate + i * gap / v                     # la boule i sort de la porte
            front = s_eat + i * delta
            te = ts + (front - s_gate) / v
            rows.append((ts, te, front + delta, fi, v, i))
        rounds.append(dict(fi=fi, t_launch=t_launch, t_path=t_path, t_gate=t_gate, v=v, rows=rows, mult=mult,
                           s_start=s_eat))
        balls += rows
        s_eat += mult * delta
        t = rows[-1][1] + 0.3
    t_end = t + 0.1
    total = t_end + 2.0
    eats = sorted((r[1], r[2], r[3], r[5]) for r in balls)          # (t, s_after, form, index dans la manche)
    print(f"durée {total:.1f} s, {M} boules, delta {delta:.0f}px, L {sp.L:.0f}px")

    # ---------------------------------------------------------------- calques fixes
    bg = Image.new("RGBA", (W, H), (6, 8, 22, 255))
    g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    for (x, y, rr, c) in [(0.2, 0.25, 420, (40, 80, 220)), (0.85, 0.7, 460, (120, 40, 200)), (0.5, 0.95, 380, (20, 120, 200))]:
        gd.ellipse((W * x - rr, H * y - rr, W * x + rr, H * y + rr), fill=c + (60,))
    bg.alpha_composite(g.filter(ImageFilter.GaussianBlur(160)))
    boss = Image.open(boss_path).convert("RGB")
    sq = min(boss.size)
    boss = boss.crop(((boss.width - sq) // 2, (boss.height - sq) // 2, (boss.width + sq) // 2, (boss.height + sq) // 2))
    boss = ImageEnhance.Brightness(boss.resize((int(2 * RD), int(2 * RD)), Image.LANCZOS)).enhance(1.12).convert("RGBA")
    bossarr = np.asarray(boss.convert("RGB"))
    disc = Image.new("L", boss.size, 0)
    ImageDraw.Draw(disc).ellipse((0, 0, boss.width - 1, boss.height - 1), fill=255)
    eaten = Image.new("L", boss.size, 0)
    ed = ImageDraw.Draw(eaten)
    bx0, by0 = int(CX - RD), int(CY - RD)
    # murs néon (toute la spirale, + l'anneau extérieur), en cache
    walls = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    wd = ImageDraw.Draw(walls)
    wpts = sp.wall(b * 0.5)
    NEON = (40, 230, 255)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).line(wpts, fill=NEON + (200,), width=int(22 * k), joint="curve")
    walls.alpha_composite(glow.filter(ImageFilter.GaussianBlur(14 * k)))
    wd.line(wpts, fill=NEON + (255,), width=int(9 * k), joint="curve")
    wd.line(wpts, fill=(210, 250, 255, 255), width=int(3 * k), joint="curve")
    fT, fS, fB = font(ANTON, 92 * k), font(MONT, 40 * k), font(ANTON, 64 * k)
    icons = [fusion.icon(str(L / "_fusion/Goku" / f[0]), int(190 * k), f[2]) for f in FORMS]
    ball_im = [tint_ball(br, f[2]) for f in FORMS]

    parts = []                                            # éclats : [x, y, vx, vy, t0, col, size]

    def carve(s0, s1):
        """Creuse le sillon avec des disques (une ligne épaisse de PIL laisse des fentes aux angles)."""
        rr = b * 0.53
        for (x, y) in sp.pts(s0, s1, step=4.0):
            ed.ellipse((x - bx0 - rr, y - by0 - rr, x - bx0 + rr, y - by0 + rr), fill=255)

    def disc_layer():
        """Le boss moins ce qui a été croqué, avec des bords brûlés qui rougeoient (lisible même sur une image sombre)."""
        m = Image.fromarray(np.minimum(np.asarray(disc, np.int16), 255 - np.asarray(eaten, np.int16)).astype(np.uint8))
        lay = boss.copy()
        lay.putalpha(m)
        edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(9)))
        hot = Image.new("RGBA", m.size, (255, 140, 30, 0))
        hot.putalpha(edge.filter(ImageFilter.GaussianBlur(5)).point(lambda v: min(255, v * 3)))
        lay.alpha_composite(hot)
        core = Image.new("RGBA", m.size, (255, 240, 200, 0))
        core.putalpha(ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(3))))
        lay.alpha_composite(core)
        return lay

    cur_disc = disc_layer()
    eat_i = 0
    s_cur = s_eat0
    carve(0, s_cur)
    cur_disc = disc_layer()

    proc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                             "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-pix_fmt", "yuv420p", str(out.with_suffix(".silent.mp4"))], stdin=subprocess.PIPE)
    nfr = int(total * FPS)
    title1, title2 = f"CAN GOKU'S KAMEHAMEHA", f"ERASE {boss_name}?"
    for fr in range(nfr):
        t = fr / FPS
        # ---- croquer ce qui doit l'être
        changed = False
        while eat_i < len(eats) and eats[eat_i][0] <= t:
            te, s_after, fi_, idx = eats[eat_i]
            carve(max(0, s_cur - 4), s_after)
            px, py = sp.at(s_after - delta * 0.5)
            for j in range(14):                           # éclats aux couleurs de l'image
                ix = int(min(max(px - bx0, 0), boss.width - 1))
                iy = int(min(max(py - by0, 0), boss.height - 1))
                c = tuple(int(v) for v in bossarr[iy, ix])
                an = rnd.uniform(0, 2 * math.pi)
                spd = rnd.uniform(200, 700) * k
                parts.append([px, py, math.cos(an) * spd, math.sin(an) * spd - 200 * k, te, c if j % 3 else FORMS[fi_][2],
                              rnd.uniform(5, 13) * k])
            s_cur = s_after
            eat_i += 1
            changed = True
        if eat_i >= len(eats) and t >= t_end and not getattr(main, "_cleared", False):
            ed.rectangle((0, 0, boss.width, boss.height), fill=255)
            main._cleared = True
            changed = True
        if changed:
            cur_disc = disc_layer()
        img = bg.copy()
        img.alpha_composite(cur_disc, (bx0, by0))
        img.alpha_composite(walls)
        d = ImageDraw.Draw(img)
        # ---- manche en cours
        rd = None
        for r_ in rounds:
            if r_["t_launch"] <= t:
                rd = r_
        fi = rd["fi"] if rd else 0
        # ---- boules
        for r_ in rounds:
            col = FORMS[r_["fi"]][2]
            v = r_["v"]
            if r_["t_launch"] <= t < r_["t_path"]:        # vol de la main de Goku à l'entrée
                q = (t - r_["t_launch"]) / (r_["t_path"] - r_["t_launch"])
                x = GOKU[0] + (entry[0] - GOKU[0]) * q
                y = GOKU[1] + (entry[1] - GOKU[1]) * q
                img.alpha_composite(ball_im[r_["fi"]], (int(x - br * 2), int(y - br * 2)))
            elif r_["t_path"] <= t < r_["t_gate"]:        # la 1re boule roule jusqu'à la porte
                x, y = sp.at((t - r_["t_path"]) * v)
                img.alpha_composite(ball_im[r_["fi"]], (int(x - br * 2), int(y - br * 2)))
            for (ts, te, _s, _f, _v, i) in r_["rows"]:
                if ts <= t < te:
                    s_ = s_gate + (t - ts) * v
                    for tr in (3, 2, 1):                  # traînée
                        xx, yy = sp.at(s_ - tr * v / FPS * 0.5)
                        rr = br * (1 - tr * 0.18)
                        d.ellipse((xx - rr, yy - rr, xx + rr, yy + rr), fill=col + (40 + 25 * (3 - tr),))
                    x, y = sp.at(s_)
                    img.alpha_composite(ball_im[r_["fi"]], (int(x - br * 2), int(y - br * 2)))
        d = ImageDraw.Draw(img, "RGBA")
        # ---- porte xN
        gx, gy = sp.at(s_gate)
        mult = rd["mult"] if rd else FORMS[0][3]
        pop = 1.0
        if rd and rd["t_gate"] <= t < rd["t_gate"] + 0.25:
            pop = 1.35 - (t - rd["t_gate"]) / 0.25 * 0.35
        gw, gh = 92 * k * pop, 50 * k * pop
        d.rounded_rectangle((gx - gw / 2, gy - gh / 2, gx + gw / 2, gy + gh / 2), radius=int(gh / 2), fill=(255, 255, 255),
                            outline=(20, 30, 60), width=int(4 * k))
        d.text((gx, gy), f"x{mult}", font=font(ANTON, 38 * k * pop), anchor="mm", fill=(20, 30, 60))
        # ---- éclats
        alive = []
        for p_ in parts:
            age = t - p_[4]
            if age < 0:
                alive.append(p_)
                continue
            if age > 0.9:
                continue
            x = p_[0] + p_[2] * age
            y = p_[1] + p_[3] * age + 900 * k * age * age
            s_ = p_[6] * (1 - age / 0.9)
            d.polygon([(x - s_, y), (x, y - s_), (x + s_, y), (x, y + s_)], fill=p_[5] + (255,))
            alive.append(p_)
        parts[:] = alive
        # ---- flash de l'impact
        for (te, _s, fi_, _i) in eats[max(0, eat_i - 3):eat_i]:
            age = t - te
            if 0 <= age < 0.15:
                px, py = sp.at(_s - delta)
                rr = br * (1.2 + 3 * age / 0.15)
                d.ellipse((px - rr, py - rr, px + rr, py + rr), outline=(255, 255, 255, int(255 * (1 - age / 0.15))),
                          width=int(6 * k))
        # ---- Goku (forme de la manche) + Kamehameha au lancer
        gs = int(190 * k)
        aura = Image.new("RGBA", (gs * 2, gs * 2), (0, 0, 0, 0))
        pul = 1 + 0.06 * math.sin(t * 12)
        ImageDraw.Draw(aura).ellipse((gs * (1 - 0.68 * pul), gs * (1 - 0.68 * pul), gs * (1 + 0.68 * pul), gs * (1 + 0.68 * pul)),
                                     fill=FORMS[fi][2] + (170,))
        img.alpha_composite(aura.filter(ImageFilter.GaussianBlur(26 * k)), (int(GOKU[0] - gs), int(GOKU[1] - gs)))
        sc = 1.0
        if rd and rd["t_launch"] <= t < rd["t_launch"] + 0.3 and rd["fi"] > 0:
            sc = 1.25 - (t - rd["t_launch"]) / 0.3 * 0.25   # pop à la transformation
        gsz = int(gs * sc)
        img.alpha_composite(icons[fi].resize((gsz, gsz), Image.LANCZOS), (int(GOKU[0] - gsz / 2), int(GOKU[1] - gsz / 2)))
        d = ImageDraw.Draw(img, "RGBA")
        if rd and rd["t_launch"] <= t < rd["t_launch"] + 0.45:      # le rayon part de Goku
            q = (t - rd["t_launch"]) / 0.45
            a_ = int(255 * (1 - q))
            hx, hy = GOKU[0] + 70 * k, GOKU[1] + 70 * k
            col = FORMS[fi][2]
            d.line((hx, hy, entry[0], entry[1]), fill=col + (a_,), width=int(34 * k * (1 - q * 0.5)))
            d.line((hx, hy, entry[0], entry[1]), fill=(255, 255, 255, a_), width=int(12 * k * (1 - q * 0.5)))
        # ---- textes
        d.text((W / 2, H * 0.075), title1, font=fT, anchor="mm", fill=(255, 255, 255), stroke_width=int(6 * k),
               stroke_fill=(0, 0, 0))
        d.text((W / 2, H * 0.075 + 100 * k), title2, font=fT, anchor="mm", fill=FORMS[fi][2], stroke_width=int(6 * k),
               stroke_fill=(0, 0, 0))
        hp = max(0.0, 1 - (s_cur - s_eat0) / (sp.L - s_eat0)) if not getattr(main, "_cleared", False) else 0.0
        bwid = 560 * k
        yb = H * 0.205
        d.text((W / 2, yb - 30 * k), f"{boss_name} HP  {hp * 100:.0f}%", font=font(ANTON, 44 * k), anchor="mm",
               fill=(255, 90, 90), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
        d.rounded_rectangle((W / 2 - bwid / 2, yb, W / 2 + bwid / 2, yb + 22 * k), radius=int(11 * k), fill=(40, 10, 20),
                            outline=(0, 0, 0), width=int(3 * k))
        if hp > 0:
            d.rounded_rectangle((W / 2 - bwid / 2 + 3, yb + 3, W / 2 - bwid / 2 + 3 + (bwid - 6) * hp, yb + 22 * k - 3),
                                radius=int(9 * k), fill=(255, 60, 70))
        fired = sum(1 for r_ in balls if r_[0] <= t)
        d.text((W / 2, H * 0.875), f"KAMEHAMEHAS: {fired}", font=font(ANTON, 56 * k), anchor="mm", fill=(255, 255, 255),
               stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
        if rd:                                            # nom de la forme sous Goku, gros au changement
            age = t - rd["t_launch"]
            nm = FORMS[fi][1]
            if age < 0.9 and fi > 0:
                s_ = 1 + 0.4 * max(0.0, 1 - age / 0.15)
                d.text((W / 2, H * 0.925), nm + "!", font=font(ANTON, 70 * k * s_), anchor="mm", fill=FORMS[fi][2],
                       stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
            else:
                d.text((W / 2, H * 0.925), nm, font=font(ANTON, 46 * k), anchor="mm", fill=FORMS[fi][2],
                       stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
        if t >= t_end:                                    # fin : effacé
            age = t - t_end
            fl = max(0.0, 1 - age / 0.35)
            if fl > 0:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(220 * fl))))
                d = ImageDraw.Draw(img, "RGBA")
            s_ = 1 + 0.5 * max(0.0, 1 - age / 0.2)
            d.text((W / 2, CY - 40 * k), f"{boss_name} ERASED", font=font(ANTON, 120 * k * s_), anchor="mm",
                   fill=(255, 214, 10), stroke_width=int(8 * k), stroke_fill=(0, 0, 0))
            render.draw_rich(img, (W / 2, CY + 70 * k), "Who should Goku erase next? 👇", font(MONT, 46 * k),
                             (255, 255, 255), "ma", int(4 * k), (0, 0, 0))
        proc.stdin.write(img.convert("RGB").tobytes())
    proc.stdin.close()
    proc.wait()

    # ---------------------------------------------------------------- son
    rate = 44100
    n = int(total * rate) + rate
    au = np.zeros(n, np.float32)

    def put(t0, x, gn):
        if x is None:
            return
        i = int(t0 * rate)
        if 0 <= i < n:
            seg = x[: n - i]
            au[i:i + len(seg)] += seg * gn
    kame = load(SFX / "Dragon Ball Xenoverse - Kamehameha Regular Sound Effect.mp3", rate)
    kame = kame[int(1.85 * rate):int(3.3 * rate)] if kame is not None else None
    if kame is not None:
        kame[-int(0.3 * rate):] *= np.linspace(1, 0, int(0.3 * rate))
    aura = load(SFX / "Voicy_Small Aura Burst (DBZ Sound Effect).mp3", rate)
    boom = load(SFX / "Voicy_DBZ Explosion Sound Effect 1.mp3", rate)
    if boom is not None:
        boom = boom[: int(2.5 * rate)]
        boom[-int(0.6 * rate):] *= np.linspace(1, 0, int(0.6 * rate))
    SCALE = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26, 28, 31, 33, 36, 38, 40, 43, 45]
    for r_ in rounds:
        put(r_["t_launch"], kame, 0.55)
        if r_["fi"] > 0:
            put(r_["t_launch"], aura, 0.5)
        put(r_["t_gate"], note(1046.5, rate, 0.35), 0.35)                    # « ding » de la porte
        for (ts, te, _s, fi_, _v, i) in r_["rows"]:
            semi = SCALE[min(i, len(SCALE) - 1)] + fi_ % 3
            put(te, note(392.0 * 2 ** (semi / 12), rate), 0.42)               # chaque croc = une note qui monte
            noise = np.random.RandomState(int(te * 100)).randn(int(0.05 * rate)).astype(np.float32)
            noise *= np.exp(-np.arange(len(noise)) / rate * 60)
            put(te, noise, 0.08)
    put(t_end, boom, 0.9)
    au = np.tanh(au * 1.2) * 0.8
    wav = out.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(rate)
        w_.writeframes((np.clip(au, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(out.with_suffix(".silent.mp4")), "-i", str(wav),
                    "-c:v", "copy", "-af", "loudnorm=I=-21:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    str(out)], check=True)
    render.stamp_video(out)
    print(out)


if __name__ == "__main__":
    main()
