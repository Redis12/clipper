"""« Guess the character » façon Snake (13/11, d'après une vidéo « Guess the Anime » de l'utilisateur : une image
révélée seulement par des traînées de cases qui se promènent). Ici 2 serpents de cases (2 cases d'épaisseur) parcourent une
image cachée : seules les cases sous leur corps sont visibles ; une case qui arrive « pop » (grossit), la queue rétrécit.
Repères jaunes autour des têtes (comme la référence). Une barre de temps se vide ; à la fin du tour, toutes les cases
apparaissent en vague depuis la tête + nom du perso + « ding ». Difficulté qui monte (serpents plus courts).
python3 tools/edit/snakeguess.py sortie.mp4
"""
import math
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
from clipper.slides import render as R  # noqa: E402

LIB = ROOT / "library"
W, H, FPS = 1080, 1920, 30
ANTON = str(ROOT / "tools/money_sim/fonts/anton.woff2")
AREA, CELL = 960, 40                       # zone de l'image (px) et taille d'une case
N = AREA // CELL
AX, AY = (W - AREA) // 2, 330              # coin haut gauche de la zone
EXPLORE, REVEAL = 6.5, 1.7                 # durée d'un tour : recherche puis réponse

# (image, centre x du recadrage en fraction, nom, difficulté 1-5, longueur des serpents, cases par seconde)
SETS = {"mix": [
    (LIB / "Jujutsu Kaisen/Sukuna/sukuna.jpg", 0.58, "SUKUNA", 1, 44, 15),
    (LIB / "Naruto/Kakashi/Kakashi.jpg", 0.45, "KAKASHI", 2, 34, 15),
    (LIB / "Naruto/Itachi/Itachi.jpg", 0.55, "ITACHI", 3, 26, 16),
    (LIB / "Jujutsu Kaisen/Toji Fushiguro/toji.jpg", 0.62, "TOJI", 4, 20, 17),
    (LIB / "Death Note/L Lawliet/Lawliet.jpg", 0.5, "L LAWLIET", 5, 15, 18),
], "naruto": [                               # édition Naruto (13/11) : persos différents de la version mélangée
    (LIB / "Naruto/Jiraya/Jiraya.png", 0.5, "JIRAIYA", 1, 44, 15),
    (LIB / "Naruto/Orochimaru/Orochimaru.jpg", 0.5, "OROCHIMARU", 2, 34, 15),
    (LIB / "Naruto/Sasuke/Sasuke.jpg", 0.5, "SASUKE", 3, 26, 16),
    (LIB / "Naruto/Minato/Minato.jpg", 0.5, "MINATO", 4, 20, 17),
    (LIB / "Naruto/Teuchi/Teuchi.jpg", 0.5, "TEUCHI 🍜", 5, 15, 18),
], "jojo": [                                 # « Find the Joestar » (13/11) : les 7 JoJo de library/_fusion/JoJo
    (LIB / "_fusion/JoJo/3 JOTARO.jpg", (0.5, 0.45), "JOTARO", 1, 44, 15),
    (LIB / "_fusion/JoJo/5 GIORNO.jpg", 0.55, "GIORNO", 2, 34, 15),
    (LIB / "_fusion/JoJo/4 JOSUKE.jpg", (0.45, 0.35), "JOSUKE", 3, 26, 16),
    (LIB / "_fusion/JoJo/1 JONATHAN.jpg", 0.6, "JONATHAN", 4, 20, 17),
    (LIB / "_fusion/JoJo/7 JOHNNY.jpg", 0.5, "JOHNNY", 5, 15, 18),
]}
TITLES = {"mix": "GUESS THE CHARACTER", "naruto": "GUESS THE NARUTO CHARACTER", "jojo": "FIND THE JOESTAR"}
ROUNDS = SETS["mix"]
YEL = (255, 210, 40)


def square(path, cx):
    """carré de toute la petite dimension ; cx = centre x (fraction) ou (cx, cy)"""
    im = Image.open(path).convert("RGB")
    cx, cy = cx if isinstance(cx, tuple) else (cx, 0.5)
    s = min(im.size)
    x0 = int(min(im.width - s, max(0, im.width * cx - s / 2)))
    y0 = int(min(im.height - s, max(0, im.height * cy - s / 2)))
    return im.crop((x0, y0, x0 + s, y0 + s)).resize((AREA, AREA), Image.LANCZOS)


class Snake:
    def __init__(self, rnd, length, start, d):
        self.rnd, self.L = rnd, length
        self.body = [start]                    # de la tête à la queue (cases du coin haut gauche du bloc 2×2)
        self.d = d

    def step(self, seen):
        x, y = self.body[0]
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        opts = []
        for d in dirs:
            if d == (-self.d[0], -self.d[1]):
                continue
            nx, ny = x + d[0], y + d[1]
            if not (0 <= nx < N - 1 and 0 <= ny < N - 1) or (nx, ny) in self.body[:6]:
                continue
            w = 3.0 if d == self.d else 1.0                     # tout droit plus souvent
            if d != self.d and self.rnd.random() < 0.35:          # « escalier » en diagonale comme la référence
                w *= 2.2
            w /= 1 + 0.6 * seen.get((nx, ny), 0)                   # va plutôt vers les zones pas encore vues
            w *= math.exp(-0.06 * math.hypot(nx - N / 2, ny - N / 2))  # et plutôt vers le centre (le visage)
            opts.append((w, d))
        if not opts:
            self.d = (-self.d[0], -self.d[1])
            self.body.reverse()
            return
        tot = sum(w for w, _ in opts)
        r = self.rnd.uniform(0, tot)
        for w, d in opts:
            r -= w
            if r <= 0:
                break
        self.d = d
        self.body.insert(0, (x + d[0], y + d[1]))
        seen[self.body[0]] = seen.get(self.body[0], 0) + 1
        del self.body[self.L:]


def text(img, s, y, size, col=(255, 255, 255), stroke=0, anchor="ma"):
    f = ImageFont.truetype(ANTON, size)
    R.draw_rich(img, (W / 2, y), s, f, col, anchor=anchor, stroke_width=stroke, stroke_fill=(0, 0, 0))


def render(out, seed=4, which="mix"):
    global ROUNDS
    ROUNDS = SETS[which]
    rnd = random.Random(seed)
    imgs = [square(p, cx) for p, cx, *_ in ROUNDS]
    tiles = [[[im.crop((i * CELL, j * CELL, (i + 1) * CELL, (j + 1) * CELL)) for j in range(N)] for i in range(N)]
             for im in imgs]
    T_R = EXPLORE + REVEAL
    END = 1.6
    total = len(ROUNDS) * T_R + END
    tmp = Path(tempfile.mkdtemp())
    notes, dings = [], []
    state = None
    PRE = 1.0                                                  # serpents déjà là à l'image 0 (accroche)
    for fi in range(int(total * FPS)):
        t = fi / FPS
        k = min(len(ROUNDS) - 1, int(t // T_R))
        tr = t - k * T_R
        img = Image.new("RGB", (W, H), (10, 10, 12))
        d = ImageDraw.Draw(img)
        if t >= len(ROUNDS) * T_R:                                    # écran de fin
            text(img, "HOW MANY", H * 0.36, 150, YEL)
            text(img, "DID YOU GET?", H * 0.36 + 170, 150, YEL)
            text(img, "Comment your score 👇", H * 0.36 + 380, 70)
            img.save(tmp / f"{fi:05d}.jpg", quality=92)
            continue
        _, _, name, diff, L, cps = ROUNDS[k]
        if state is None or state["k"] != k:
            seen = {}
            sn = [Snake(rnd, L, (rnd.randrange(2, N - 3), rnd.randrange(2, 6)), (1, 0)),
                  Snake(rnd, L, (rnd.randrange(2, N - 3), rnd.randrange(N - 6, N - 3)), (-1, 0))]
            state = {"k": k, "sn": sn, "seen": seen, "acc": 0.0, "born": {}, "dead": [], "steps": 0}
            for _ in range(int(PRE * cps)):                           # pré-simulation : déjà en mouvement
                for s in sn:
                    s.step(seen)
        st = state
        if tr < EXPLORE:
            st["acc"] += cps / FPS
            while st["acc"] >= 1:
                st["acc"] -= 1
                for s in st["sn"]:
                    tail = s.body[-1] if len(s.body) >= s.L else None
                    s.step(st["seen"])
                    st["born"][s.body[0]] = t
                    if tail and tail not in s.body:
                        st["dead"].append((tail, t))
                st["steps"] += 1
                if st["steps"] % 2 == 0:
                    notes.append((t, st["steps"] // 2))
        # cases visibles : blocs 2×2 sous chaque corps
        vis = {}
        for s in st["sn"]:
            for (x, y) in s.body:
                for c in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                    vis[c] = max(vis.get(c, -9), st["born"].get((x, y), -9))
        shrinking = [(c, t0) for c, t0 in st["dead"] if t - t0 < 0.12]
        st["dead"] = shrinking
        heads = [s.body[0] for s in st["sn"]]
        if tr >= EXPLORE:                                               # réponse : tout apparaît en vague
            q = tr - EXPLORE
            hx, hy = heads[0]
            for i in range(N):
                for j in range(N):
                    if (i, j) in vis:
                        continue
                    dist = math.hypot(i - hx, j - hy) / (N * 1.42)
                    a = (q - dist * 0.55) / 0.12
                    if a > 0:
                        vis[(i, j)] = t - min(1.0, a) * 0.1
            if abs(q) < 0.5 / FPS:
                dings.append(t)
        for (i, j), t0 in vis.items():
            p = min(1.0, max(0.0, (t - t0) / 0.1))
            sz = int(CELL * (0.55 + 0.45 * (1 - (1 - p) ** 3)))
            tile = tiles[k][i][j] if sz == CELL else tiles[k][i][j].resize((sz, sz), Image.BILINEAR)
            img.paste(tile, (AX + i * CELL + (CELL - sz) // 2, AY + j * CELL + (CELL - sz) // 2))
        for (i, j) in vis:                                              # liseré sur les bords du serpent
            x0_, y0_ = AX + i * CELL, AY + j * CELL
            for (di, dj, seg) in ((-1, 0, (x0_, y0_, x0_, y0_ + CELL)), (1, 0, (x0_ + CELL, y0_, x0_ + CELL, y0_ + CELL)),
                                  (0, -1, (x0_, y0_, x0_ + CELL, y0_)), (0, 1, (x0_, y0_ + CELL, x0_ + CELL, y0_ + CELL))):
                if (i + di, j + dj) not in vis:
                    d.line(seg, fill=(95, 95, 110), width=2)
        for (x, y), t0 in shrinking:                                     # queue qui rétrécit
            p = (t - t0) / 0.12
            for (i, j) in ((x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)):
                if (i, j) in vis:
                    continue
                sz = max(2, int(CELL * (1 - p)))
                img.paste(tiles[k][i][j].resize((sz, sz)), (AX + i * CELL + (CELL - sz) // 2, AY + j * CELL + (CELL - sz) // 2))
        if tr < EXPLORE:                                                 # repères jaunes autour des têtes
            for n_, (x, y) in enumerate(heads):
                cx, cy = AX + (x + 1) * CELL, AY + (y + 1) * CELL
                r = CELL * (1.25 + 0.12 * math.sin(t * 14 + n_))
                d.rectangle((cx - r, cy - r, cx + r, cy + r), outline=YEL, width=4)
                rr = random.Random(int(t * 8) * 7 + n_)
                for _ in range(3):
                    ox, oy = rr.uniform(-2.6, 2.6) * CELL, rr.uniform(-2.6, 2.6) * CELL
                    for b in range(rr.randint(2, 4)):
                        d.rectangle((cx + ox, cy + oy + b * 9, cx + ox + 26, cy + oy + b * 9 + 3), fill=YEL)
        # textes
        text(img, TITLES[which], 80, 96 if len(TITLES[which]) < 22 else 76)
        text(img, f"Round {k + 1}/{len(ROUNDS)} · Difficulty: " + "🔥" * diff, 210, 50, (230, 230, 230))
        # barre de temps
        bar_y = AY + AREA + 30
        left = max(0.0, 1 - tr / EXPLORE)
        d.rounded_rectangle((AX, bar_y, AX + AREA, bar_y + 18), 9, fill=(40, 40, 48))
        if left > 0:
            col = YEL if left > 0.3 else (255, 70, 60)
            d.rounded_rectangle((AX, bar_y, AX + int(AREA * left), bar_y + 18), 9, fill=col)
        if tr >= EXPLORE:
            q = tr - EXPLORE - 0.15
            if q > 0:
                sc = 1 + 0.25 * math.exp(-q * 9)
                text(img, name, bar_y + 45, int(120 * sc), YEL, stroke=6)
        else:
            text(img, "Who is it? 🤔", bar_y + 50, 66)
        img.save(tmp / f"{fi:05d}.jpg", quality=92)

    # --- audio : une petite note (marimba) tous les 2 pas, gamme pentatonique qui monte et redescend ; ding à la réponse
    sr = 44100
    mix = np.zeros(int((total + 1) * sr), np.float32)
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21]

    def put(t, s):
        a = int(t * sr)
        s = s[:max(0, len(mix) - a)]
        mix[a:a + len(s)] += s

    def note(f, dur=0.22, g=0.12):
        tt = np.arange(int(dur * sr)) / sr
        return (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 18) * g

    for t, n in notes:
        i = n % (2 * len(scale) - 2)
        i = i if i < len(scale) else 2 * len(scale) - 2 - i
        put(t, note(392 * 2 ** (scale[i] / 12)))
    for t in dings:
        for m, f in enumerate((1046.5, 1318.5, 1568.0)):
            put(t + m * 0.07, note(f, 0.9, 0.22))
    put(len(ROUNDS) * T_R, note(523.25, 1.2, 0.25) + note(659.25, 1.2, 0.2)[:int(1.2 * sr)])
    mix = np.tanh(mix * 1.2) * 0.85
    wav = tmp / "a.wav"
    with wave.open(str(wav), "wb") as w_:
        w_.setnchannels(1)
        w_.setsampwidth(2)
        w_.setframerate(sr)
        w_.writeframes((mix[:int(total * sr)] * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", str(tmp / "%05d.jpg"), "-i", str(wav),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    R.stamp_video(Path(out))
    print(out, round(total, 1), "s")


if __name__ == "__main__":
    render(sys.argv[1], which=sys.argv[2] if len(sys.argv) > 2 else "mix")
