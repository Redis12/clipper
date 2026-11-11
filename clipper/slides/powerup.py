"""Vidéo « Power Up » (idée de l'utilisateur, inspirée d'une vidéo virale « Can Fibonacci pay off the US National
Debt in under 60 seconds? ») : dans une boîte carrée, une petite balle (le héros, ex. Kid Goku) et une grosse
(le boss, ex. Goku SSJ God) rebondissent. À chaque choc le héros inflige des dégâts qui grossissent de façon
exponentielle ; à intervalles réguliers il se TRANSFORME (formes du dossier library/_fusion/<Perso>/) et le
multiplicateur augmente. Compte à rebours dans le titre (« in under 60 Seconds ») : le dernier coup tombe pile à
0 seconde → le boss explose.

Pourquoi ça marche (analyse de la vidéo virale) : compte à rebours = on reste jusqu'au bout ; croissance
exponentielle = « jamais… attends, si ! » ; un seul événement répété (choc + nombre qui flotte + son) = hypnotique ;
fin pile à 0 s ; ~62 s (> 1 min, monétisation TikTok).

Physique et dégâts sont calculés AVANT le rendu (simulation déterministe par graine) : on cherche une graine dont
le dernier choc tombe juste avant la fin, puis on règle la croissance pour que les PV du boss tombent pile à ce coup.
"""
from __future__ import annotations

import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import config, db
from ..util import log, require_bin
from . import fusion, render

HERO_COL, BOSS_COL = (70, 220, 120), (235, 60, 70)


def pcfg() -> dict:
    return config.get()["slides"].get("powerup", {})


# --------------------------------------------------------------------------- simulation

def simulate(seed: int, seconds: float, S: float, n_forms: int, dt: float = 1 / 240) -> dict:
    """Deux balles dans une boîte S×S (coordonnées 0..S). Le héros accélère et grossit un peu à chaque
    transformation (instants fixes). Rend les positions par pas de 1/30 s et la liste des chocs."""
    rnd = random.Random(seed)
    RB = S * 0.20
    r0 = S * 0.085
    tf = [seconds * (j + 1) / n_forms for j in range(n_forms - 1)]       # instants des transformations
    bx, by = rnd.uniform(RB, S - RB), rnd.uniform(RB, S - RB)
    a = rnd.uniform(0, 2 * math.pi)
    bvx, bvy = math.cos(a) * S * 0.16, math.sin(a) * S * 0.16
    while True:
        hx, hy = rnd.uniform(r0, S - r0), rnd.uniform(r0, S - r0)
        if math.hypot(hx - bx, hy - by) > RB + r0 + S * 0.08:
            break
    a = rnd.uniform(0, 2 * math.pi)
    hv = S * 0.85
    hvx, hvy = math.cos(a) * hv, math.sin(a) * hv
    t, form, cool = 0.0, 0, 0.0
    hits, frames = [], []
    next_frame = 0.0
    mB, mH = 12.0, 1.0
    end = seconds + 2.5
    while t < end:
        while form < len(tf) and t >= tf[form]:                          # transformation : plus vite
            form += 1
            sp = math.hypot(hvx, hvy) or 1
            k = 1.12
            hvx, hvy = hvx / sp * sp * k, hvy / sp * sp * k
        r = r0 * (1 + 0.06 * form)
        bx += bvx * dt
        by += bvy * dt
        hx += hvx * dt
        hy += hvy * dt
        if bx < RB or bx > S - RB:
            bvx = -bvx
            bx = min(max(bx, RB), S - RB)
        if by < RB or by > S - RB:
            bvy = -bvy
            by = min(max(by, RB), S - RB)
        if hx < r or hx > S - r:
            hvx = -hvx
            hx = min(max(hx, r), S - r)
        if hy < r or hy > S - r:
            hvy = -hvy
            hy = min(max(hy, r), S - r)
        dx, dy = hx - bx, hy - by
        d = math.hypot(dx, dy)
        cool = max(0.0, cool - dt)
        if 0 < d < RB + r:
            nx, ny = dx / d, dy / d
            rel = (hvx - bvx) * nx + (hvy - bvy) * ny
            if rel < 0:                                                   # choc élastique (masses inégales)
                j = -2 * rel / (1 / mH + 1 / mB)
                hvx += j / mH * nx
                hvy += j / mH * ny
                bvx -= j / mB * nx
                bvy -= j / mB * ny
                if cool <= 0 and t <= seconds:
                    hits.append((t, bx + nx * RB, by + ny * RB))
                    cool = 0.12
            push = RB + r - d
            hx += nx * push * 0.9
            hy += ny * push * 0.9
            bx -= nx * push * 0.1
            by -= ny * push * 0.1
        bs = math.hypot(bvx, bvy)                                         # le boss garde sa vitesse
        if bs > 0:
            bvx, bvy = bvx / bs * S * 0.16, bvy / bs * S * 0.16
        hs = math.hypot(hvx, hvy)
        want = hv * 1.12 ** form
        if hs > 0:
            hvx, hvy = hvx / hs * want, hvy / hs * want
        if t >= next_frame:
            frames.append((bx, by, hx, hy, r, form))
            next_frame += 1 / 30
        t += dt
    return {"hits": hits, "frames": frames, "RB": RB, "tf": tf, "seconds": seconds}


def pick_seed(seconds: float, S: float, n_forms: int, tries: int = 400, rnd: random.Random | None = None):
    """Graine dont le dernier choc tombe dans la dernière demi-seconde (le coup final à « 0 Seconds »)."""
    rnd = rnd or random.Random()
    best = None
    for _ in range(tries):
        seed = rnd.randrange(1_000_000)
        sim = simulate(seed, seconds, S, n_forms, dt=1 / 120)
        hits = sim["hits"]
        if len(hits) < 40:
            continue
        gap = seconds - hits[-1][0]
        score = abs(gap - 0.25) + (0 if gap >= 0 else 9)
        if best is None or score < best[0]:
            best = (score, seed)
        if 0.05 <= gap <= 0.45:
            return seed
    return best[1] if best else rnd.randrange(1_000_000)


def damages(hit_times: list[float], tf: list[float], target: float) -> tuple[list[float], list[float], float]:
    """Dégâts de chaque coup : d0 = 1, puis ×r à chaque coup, r augmente à chaque transformation (r = 1 + a(f+1)).
    `a` est réglé pour que le total vaille ~`target`. PV du boss = total avant le dernier coup + 55 % du dernier
    (le dernier coup l'achève). Rend (dégâts, multiplicateur par coup, PV)."""
    def form_at(t):
        return sum(1 for x in tf if t >= x)

    def run(a):
        d, out, mults = 1.0, [], []
        for i, t in enumerate(hit_times):
            m = 1 + a * (form_at(t) + 1)
            if i:
                d *= m
            out.append(d)
            mults.append(m)
        return out, mults
    lo, hi = 1e-4, 2.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if sum(run(mid)[0]) < target:
            lo = mid
        else:
            hi = mid
    ds, mults = run((lo + hi) / 2)
    hp = sum(ds[:-1]) + 0.55 * ds[-1]
    return ds, mults, hp


# --------------------------------------------------------------------------- rendu

NAMES = [(1e33, "decillion"), (1e30, "nonillion"), (1e27, "octillion"), (1e24, "septillion"), (1e21, "sextillion"),
         (1e18, "quintillion"), (1e15, "quadrillion"), (1e12, "trillion"), (1e9, "billion"), (1e6, "million")]


def compact(x: float) -> str:
    """1 234 → « 1,234 » ; 17 160 000 000 000 → « 17.16 trillion »."""
    x = max(0.0, x)
    for v, n in NAMES:
        if x >= v:
            return f"{x / v:.2f} {n}"
    return f"{int(round(x)):,}"


def full(x: float) -> str:
    return f"{int(max(0.0, x)):,}"


def _rich_line(d: ImageDraw.ImageDraw, cx: float, y: float, parts: list, f, stroke: int):
    """Une ligne centrée faite de morceaux colorés : [(texte, couleur), …]."""
    widths = [render.text_width(d, t, f) for t, _ in parts]
    x = cx - sum(widths) / 2
    for (t, col), w in zip(parts, widths):
        d.text((x, y), t, font=f, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0))
        x += w


def generate(chain: str, boss: str, hero_name: str | None = None, boss_name: str | None = None,
             seconds: float = 60, out: Path | None = None, seed: int | None = None, sound: str | None = None,
             target: float | None = None, fail: bool = False, max_form: str | None = None,
             hakai: float | None = None, part: str | None = None) -> Path:
    """`chain` = dossier library/_fusion/<chain> (formes du héros, de la plus faible à la plus forte) ;
    `boss` = nom d'une forme de ce dossier (retirée des formes du héros) ou chemin d'une image."""
    from . import faces, fxengine, vfxgen, vfxpack  # noqa: F401
    c = pcfg()
    W, H = (int(v) for v in c.get("size", [1080, 1920]))
    fps = 30
    k = W / 1080
    tiers = fusion.tiers_from_chain(chain)
    norm = lambda s: "".join(ch for ch in s.lower() if ch.isalnum())   # noqa: E731
    boss_t = next((t for t in tiers if norm(t["name"]) == norm(boss)), None)
    if boss_t is None and Path(boss).is_file():
        boss_t = {"name": boss_name or Path(boss).stem, "image_path": boss}
    if boss_t is None:
        raise ValueError(f"Forme « {boss} » introuvable dans _fusion/{chain}")
    forms = [t for t in tiers if t is not boss_t and not t.get("easter")]    # l'easter egg (Zoro perdu) n'est pas une forme
    if max_form:                                         # forme max du héros (logique : pas de Rinnegan)
        cut = next((i for i, t in enumerate(forms) if norm(t["name"]) == norm(max_form)), None)
        if cut is not None:
            forms = forms[:cut + 1]
    if len(forms) < 2:
        raise ValueError("Il faut au moins 2 formes pour le héros")
    hero_name = hero_name or f"{forms[0]['name']}"
    boss_name = boss_name or f"{boss_t['name']} {chain}"
    S = W * 0.86
    seed = seed if seed is not None else pick_seed(seconds, S, len(forms))
    sim = simulate(seed, seconds, S, len(forms))
    hits = sim["hits"]
    target = float(target or c.get("target", 9.0e12))
    if hakai:                                            # « Part 2 » : le boss efface le héros (Hakai) à t = hakai
        fail = True
    stop_at = float(hakai) if hakai else seconds
    if fail:                                             # défaite : pas de coup après le chrono / le Hakai
        hits = [h for h in hits if h[0] <= stop_at - 0.05]
    ds, mults, HP = damages([h[0] for h in hits], sim["tf"], target)
    left_pct = 0.0
    if fail:                                             # le boss survit avec ~4 % de vie
        left_pct = float(pcfg().get("fail_left", 0.04)) if not hakai else 0.11
        HP = sum(ds) / (1 - left_pct)
    kill_t = hits[-1][0] if not fail else stop_at
    ox, oy = (W - S) / 2, H * 0.215

    # images
    hero_icons = {}

    def hero_icon(f, size):
        key = (f, size)
        if key not in hero_icons:
            hero_icons[key] = fusion.icon(forms[f].get("image_path"), size, HERO_COL)
        return hero_icons[key]
    RB = sim["RB"]
    boss_icon = fusion.icon(boss_t.get("image_path"), int(RB * 2), BOSS_COL)

    # fond : boîte façon papier quadrillé sombre
    bg = Image.new("RGBA", (W, H), (12, 14, 22, 255))
    bd = ImageDraw.Draw(bg)
    step = S / 24
    for i in range(25):
        bd.line((ox + i * step, oy, ox + i * step, oy + S), fill=(32, 36, 52), width=1)
        bd.line((ox, oy + i * step, ox + S, oy + i * step), fill=(32, 36, 52), width=1)
    frame_l = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(frame_l).rectangle((ox - 6 * k, oy - 6 * k, ox + S + 6 * k, oy + S + 6 * k),
                                      outline=(255, 205, 60, 255), width=int(8 * k))
    glow = frame_l.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(4)).resize((W, H))
    bg.alpha_composite(glow)
    bg.alpha_composite(frame_l)

    tf1 = render.font(int(64 * k))
    tf2 = render.font(int(64 * k))
    lf = render.font(int(34 * k))
    vf = render.font(int(62 * k))
    hpf = render.font(int(30 * k))
    ff = render.font(int(40 * k))
    parts = fxengine.Particles(seed)
    tex = fxengine.TexFX(seed)
    cam = fxengine.Camera()
    pack = vfxpack.available()
    explo = list(vfxpack.frames("explosion_dome", None, BOSS_COL)) if pack else []
    if not explo:
        explo = list(vfxgen.frames("explosion", 256, BOSS_COL))
    floats: list = []                                   # (t, x, y, texte)
    stage_ev: list = []                                 # (t, forme)
    ripples: list = []

    out = out or (config.data_dir() / "fusions" / f"powerup_{seed}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    hi = 0
    dealt = 0.0
    frame_n = 0
    stop_frames = 0
    kill_done = False
    hit_audio, form_audio = [], []
    end_frames = int(fps * 1.5)                 # vidIQ : un Short « se termine », pas d'écran qui traîne
    n_sim = len(sim["frames"])
    if fail:                                    # chrono à 0 : figé, « TIME'S UP! » puis « FAILED »
        n_sim = min(n_sim, int(stop_at * fps) + 1)
        end_frames = int(fps * ((2.6 if hakai else 1.3) + 1.8))
    try:
        for fi in range(n_sim + end_frames):
            t = fi / fps
            ended = fi >= n_sim
            bx, by, hx, hy, r, form = sim["frames"][min(fi, n_sim - 1)]
            if kill_done:
                form = len(forms) - 1
            while hi < len(hits) and hits[hi][0] <= t:            # chocs de cette image
                ht, cx_, cy_ = hits[hi]
                dealt += ds[hi]
                X, Y = ox + cx_, oy + cy_
                floats.append((ht, X, Y, f"-{compact(ds[hi]) if ds[hi] >= 1e6 else full(ds[hi])}"))
                parts.emit(X, Y, 10, speed=(200 * k, 600 * k), col=(160, 255, 190), life=(0.15, 0.35),
                           size=(2 * k, 4 * k))
                tex.spawn("circle_05", X, Y, RB * 0.25, 0.3, (200, 255, 220), size1=RB * 0.8, hot=0.7)
                hit_audio.append(ht)
                if hi == len(hits) - 1 and not fail:              # dernier coup : le boss explose
                    kill_done = True
                    stop_frames = 5
                    cam.punch(t, ox + bx, oy + by, 0.1, 0.6)
                    ripples.append((t, ox + bx, oy + by))
                    parts.emit(ox + bx, oy + by, 80, speed=(300 * k, 1300 * k), col=(255, 200, 150),
                               life=(0.3, 0.9), size=(3 * k, 7 * k))
                    parts.emit(ox + bx, oy + by, 30, speed=(150 * k, 600 * k), col=(110, 90, 90), life=(0.6, 1.2),
                               size=(6 * k, 12 * k), kind=fxengine.DEBRIS)
                    tex.spawn("star_09", ox + bx, oy + by, RB, 0.5, (255, 240, 220), size1=RB * 6, hot=1.0)
                else:
                    cam.punch(t, X, Y, 0.012, 0.18)
                hi += 1
            if fi > 0 and not ended and sim["frames"][fi - 1][5] != form and not kill_done:   # transformation
                stage_ev.append((t, form))
                form_audio.append(t)
                tex.spawn("star_09", ox + hx, oy + hy, r * 2, 0.35, (255, 250, 220), size1=r * 9, hot=1.0)
                parts.emit(ox + hx, oy + hy, 40, speed=(250 * k, 900 * k), col=(255, 230, 120), life=(0.2, 0.6),
                           size=(2 * k, 5 * k))
                ripples.append((t, ox + hx, oy + hy))
            parts.step(1 / fps)
            tex.step(1 / fps)

            img = bg.copy()
            d = ImageDraw.Draw(img)
            # titre : « Can Kid Goku beat SSJ God Goku in under / 37 Seconds »
            left = max(0, math.ceil(seconds - min(t, stop_at) - 1e-6)) if not kill_done else 0
            _rich_line(d, W / 2, H * 0.045, [("Can ", (255, 255, 255)), (hero_name, HERO_COL), (" beat", (255, 255, 255))],
                       tf1, int(4 * k))
            _rich_line(d, W / 2, H * 0.045 + 74 * k, [(boss_name, BOSS_COL), (" in under", (255, 255, 255))],
                       tf1, int(4 * k))
            pulse = 1 + (0.12 * max(0.0, 1 - (t % 1) / 0.25) if left <= 10 and not kill_done else 0)
            sf = render.font(int(76 * k * pulse))
            d.text((W / 2, H * 0.045 + 150 * k), f"{left} Seconds", font=sf, anchor="ma",
                   fill=(255, 80, 80) if left <= 10 else (255, 255, 255), stroke_width=int(4 * k),
                   stroke_fill=(0, 0, 0))
            if part:                                              # « PART 2 » : pilule rouge en haut à droite de la boîte
                pf_ = render.font(int(34 * k))
                tw_ = render.text_width(d, part.upper(), pf_) + 30 * k
                d.rounded_rectangle((ox + S - tw_, oy - 58 * k, ox + S, oy - 14 * k), radius=10 * k, fill=(235, 60, 70))
                d.text((ox + S - tw_ / 2, oy - 36 * k), part.upper(), font=pf_, anchor="mm", fill=(255, 255, 255))
            # boss
            if not kill_done:
                bim = boss_icon
                if floats and t - floats[-1][0] < 0.08:              # flash rouge quand il encaisse
                    bim = boss_icon.copy()
                    red = Image.new("RGBA", bim.size, (255, 40, 40, 255))
                    red.putalpha(bim.getchannel("A").point(lambda v: v // 2))
                    bim = Image.alpha_composite(bim, red)
                img.alpha_composite(bim, (int(ox + bx - RB), int(oy + by - RB)))
                hp_left = HP - dealt
                txt = full(hp_left) if hp_left < 1e15 else compact(hp_left)
                tw = render.text_width(d, txt, hpf) + 26 * k
                d.rounded_rectangle((ox + bx - tw / 2, oy + by + RB * 0.58, ox + bx + tw / 2, oy + by + RB * 0.58 + 46 * k),
                                    radius=8 * k, fill=(10, 10, 14), outline=(255, 205, 60), width=max(2, int(3 * k)))
                d.text((ox + bx, oy + by + RB * 0.58 + 23 * k), txt, font=hpf, anchor="mm", fill=(255, 60, 60))
                d.text((ox + bx, oy + by + RB * 0.58 - 6 * k), "POWER LEVEL", font=render.font(int(22 * k)),
                       anchor="md", fill=(255, 255, 255), stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            # héros + aura qui grandit avec les formes
            hs = int(r * 2)
            if form > 0:
                au = Image.new("RGBA", (hs * 3, hs * 3), (0, 0, 0, 0))
                ImageDraw.Draw(au).ellipse((hs * 0.6, hs * 0.6, hs * 2.4, hs * 2.4),
                                           fill=(255, 220, 90, int(60 + 18 * form)))
                au = au.filter(ImageFilter.GaussianBlur(hs * 0.3))
                img.alpha_composite(au, (int(ox + hx - au.width / 2), int(oy + hy - au.height / 2)))
            if not (hakai and ended):                             # Hakai : le héros est dessiné à part
                img.alpha_composite(hero_icon(form, hs), (int(ox + hx - hs / 2), int(oy + hy - hs / 2)))
            # textes qui flottent (« -1,597 »)
            keep = []
            for (ft, fx_, fy_, s_) in floats:
                a = (t - ft) / 0.8
                if a < 1:
                    keep.append((ft, fx_, fy_, s_))
                    al = int(255 * (1 - a))
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(lay).text((fx_, fy_ - 60 * k * a), s_, font=ff, anchor="mm",
                                             fill=(110, 255, 150, al), stroke_width=int(3 * k), stroke_fill=(0, 0, 0, al))
                    img.alpha_composite(lay)
            floats[:] = keep[-6:]
            # bandeau de transformation
            for st, f_ in stage_ev[-1:]:
                a = (t - st) / 1.1
                if 0 <= a < 1:
                    sc = 1 + 0.5 * max(0.0, 1 - a / 0.15)
                    bf = render.font(int(56 * k * sc))
                    d = ImageDraw.Draw(img)
                    d.text((W / 2, oy + S * 0.5), forms[f_]["name"].upper() + "!", font=bf, anchor="mm",
                           fill=(255, 220, 60), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            # explosion du boss
            if kill_done:
                kt = kill_t
                a = (t - kt) / 0.9
                if 0 <= a < 1 and explo:
                    f_ = explo[min(len(explo) - 1, int(a * len(explo)))]
                    sz = RB * 4.5
                    sc = sz / max(f_.width, f_.height)
                    im = f_.resize((int(f_.width * sc), int(f_.height * sc)),
                                   Image.NEAREST if f_.info.get("pixel") else Image.BILINEAR)
                    img.alpha_composite(im, (int(ox + bx - im.width / 2), int(oy + by - im.height * 0.7)))
            en = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            parts.draw(en, 1.0)
            tex.draw(en, glow=True)
            img = fxengine.bloom(img, en, 0.7)
            g = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            parts.draw(g, 1.0, kinds=(fxengine.DEBRIS, fxengine.SMOKE))
            img.alpha_composite(g)
            d = ImageDraw.Draw(img)
            # bas : dégâts totaux + multiplicateur
            yb = oy + S + 30 * k
            d.text((W / 2, yb), "TOTAL DAMAGE", font=lf, anchor="ma", fill=(255, 255, 255), stroke_width=int(3 * k),
                   stroke_fill=(0, 0, 0))
            d.text((W / 2, yb + 44 * k), compact(dealt), font=vf, anchor="ma", fill=(255, 214, 10),
                   stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            m_now = mults[max(0, hi - 1)] if hi else 1.0
            d.text((W / 2, yb + 126 * k), f"{forms[form]['name']}  ·  ×{m_now:.2f} per hit", font=lf, anchor="ma",
                   fill=HERO_COL, stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            if kill_done and t - kill_t > 0.25:                   # K.O. puis écran de fin
                a = min(1.0, (t - kill_t - 0.25) / 0.3)
                if t - kill_t > 1.4:
                    dim = Image.new("RGBA", (W, H), (0, 0, 0, int(200 * min(1.0, (t - kill_t - 1.4) / 0.4))))
                    img.alpha_composite(dim)
                    d = ImageDraw.Draw(img)
                    big = int(W * 0.46)
                    img.alpha_composite(hero_icon(len(forms) - 1, big), (int(W / 2 - big / 2), int(H * 0.36)))
                    d = ImageDraw.Draw(img)
                    d.text((W / 2, H * 0.31), f"{hero_name.upper()} DID IT", font=render.font(int(84 * k)),
                           anchor="mm", fill=HERO_COL, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                    render.draw_rich(img, (W / 2, H * 0.36 + big + 40 * k), "Who should he fight next? Comment 👇",
                                     render.font(int(46 * k)), (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
                    cta = (render.rcfg().get("end_cta") or "").strip()
                    if cta:
                        render.draw_rich(img, (W / 2, H * 0.36 + big + 130 * k), cta, render.font(int(48 * k)),
                                         render.rcfg()["accent_color"], "ma", int(3 * k), (0, 0, 0))
                else:
                    kf = render.font(int(180 * k * (1 + 0.4 * (1 - a))))
                    d.text((W / 2, oy + S / 2), "K.O.!", font=kf, anchor="mm", fill=(255, 214, 10),
                           stroke_width=int(8 * k), stroke_fill=(0, 0, 0))
            if fail and ended:                                    # défaite : TIME'S UP! / HAKAI puis FAILED
                e_ = t - stop_at
                T1 = 2.6 if hakai else 1.3
                if hakai and e_ < T1:                             # HAKAI : violet, le héros se désintègre
                    dk = Image.new("RGBA", (W, H), (40, 0, 60, int(150 * min(1.0, e_ / 0.3))))
                    img.alpha_composite(dk)
                    hs_ = int(r * 2)
                    au = Image.new("RGBA", (int(RB * 4), int(RB * 4)), (0, 0, 0, 0))
                    ImageDraw.Draw(au).ellipse((RB * 0.6, RB * 0.6, RB * 3.4, RB * 3.4),
                                               fill=(170, 60, 255, int(90 + 60 * math.sin(e_ * 12) ** 2)))
                    au = au.filter(ImageFilter.GaussianBlur(RB * 0.35))
                    img.alpha_composite(au, (int(ox + bx - au.width / 2), int(oy + by - au.height / 2)))
                    img.alpha_composite(boss_icon, (int(ox + bx - RB), int(oy + by - RB)))
                    q = max(0.0, (e_ - 0.7) / 1.4)                # le héros : violet puis s'efface en morceaux
                    hi_ = hero_icon(form, hs_).copy()
                    pur = Image.new("RGBA", hi_.size, (190, 90, 255, 255))
                    pur.putalpha(hi_.getchannel("A"))
                    hi_ = Image.blend(hi_, pur, min(1.0, e_ / 0.7) * 0.7)
                    if q > 0:
                        rq = random.Random(7)
                        import numpy as _np
                        a_ = _np.array(hi_.getchannel("A")).astype(_np.float32)
                        noise = _np.array([[rq.random() for _ in range(hs_)] for _ in range(hs_)], _np.float32)
                        a_[noise < q * 1.1] = 0
                        hi_.putalpha(Image.fromarray(a_.astype(_np.uint8)))
                        if int(e_ * fps) % 2 == 0 and q < 1:
                            parts.emit(ox + hx, oy + hy, 14, speed=(80 * k, 380 * k), col=(200, 120, 255),
                                       life=(0.4, 1.0), size=(3 * k, 7 * k), kind=fxengine.EMBER)
                    img.alpha_composite(hi_, (int(ox + hx - hs_ / 2), int(oy + hy - hs_ / 2)))
                    en_ = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    parts.draw(en_, 1.0)
                    img = fxengine.bloom(img, en_, 0.8)
                    d = ImageDraw.Draw(img)
                    if e_ > 0.25:
                        a = min(1.0, (e_ - 0.25) / 0.2)
                        kf = render.font(int(170 * k * (1 + 0.4 * (1 - a))))
                        d.text((W / 2, oy + S * 0.5), "HAKAI", font=kf, anchor="mm", fill=(190, 90, 255),
                               stroke_width=int(8 * k), stroke_fill=(0, 0, 0))
                elif not hakai and e_ < 1.3:
                    a = min(1.0, e_ / 0.25)
                    kf = render.font(int(150 * k * (1 + 0.4 * (1 - a))))
                    d.text((W / 2, oy + S / 2), "TIME'S UP!", font=kf, anchor="mm", fill=(255, 70, 70),
                           stroke_width=int(8 * k), stroke_fill=(0, 0, 0))
                else:
                    dim = Image.new("RGBA", (W, H), (0, 0, 0, int(210 * min(1.0, (e_ - T1) / 0.3))))
                    img.alpha_composite(dim)
                    d = ImageDraw.Draw(img)
                    big = int(W * 0.46)
                    img.alpha_composite(fusion.icon(boss_t.get("image_path"), big, BOSS_COL),
                                        (int(W / 2 - big / 2), int(H * 0.36)))
                    d = ImageDraw.Draw(img)
                    d.text((W / 2, H * 0.24), "FAILED", font=render.font(int(120 * k)), anchor="mm",
                           fill=(255, 60, 60), stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
                    d.text((W / 2, H * 0.31), f"{boss_name.upper()} USED HAKAI" if hakai else
                           f"{boss_name.upper()} SURVIVED · {round(left_pct * 100)}% LEFT",
                           font=render.font(int(54 * k)), anchor="mm", fill=(255, 255, 255),
                           stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                    render.draw_rich(img, (W / 2, H * 0.36 + big + 40 * k), "Should Goku get a Part 3? Comment 👇" if hakai
                                     else "Who could beat him? Comment 👇",
                                     render.font(int(46 * k)), (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
            keep_r = []
            for t0, rx, ry in ripples:
                a = t - t0
                if a < 0.42:
                    keep_r.append((t0, rx, ry))
                    img = fxengine.ripple(img, rx, ry, S / 24 * (1 + 22 * a), S / 24 * 0.9 * (1 - a / 0.42), S / 24 * 1.6)
            ripples[:] = keep_r
            shake = 16 * k * max(0.0, 1 - (t - kill_t) / 0.5) if kill_done and t >= kill_t else 0
            img = cam.apply(img, t, shake, seed=fi)
            rgb = img.convert("RGB")
            proc.stdin.write(rgb.tobytes())
            frame_n += 1
            if stop_frames:                                       # coup final : arrêt + 2 impact frames
                for j in range(stop_frames):
                    fr_ = fxengine.impact_frame(img, (255, 214, 10), invert=j == 1) if j < 2 else img
                    proc.stdin.write(fr_.convert("RGB").tobytes())
                    frame_n += 1
                stop_frames = 0
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué")
    finally:
        if proc.poll() is None:
            proc.kill()
    duration = frame_n / fps
    # son : coup à chaque choc (variantes qui tournent), montée en puissance aux transfos, explosion, tic-tac
    import numpy as np

    from . import domain
    rate = fusion.RATE
    n = int(duration * rate) + rate
    audio = np.zeros(n, dtype=np.float32)
    stop_shift = 5 / fps

    def put(tt, x, gain):
        i = int(tt * rate)
        if x is not None and 0 <= i < n:
            seg = x[: n - i]
            audio[i:i + len(seg)] += seg * gain
    try:
        from . import seo
        fr = seo.anime_of(hero_name) or seo.anime_of(chain)
        franchise = fr[0].lower() if fr else None
    except Exception:
        franchise = None

    def S_(fam, s=0):
        try:
            return domain.sfx(fam, mode="anime", seed=s, franchise=franchise)
        except Exception:
            return None
    hit_sounds = [S_("hit", i) for i in range(4)]
    custom = fusion.load_sound(sound) if sound else None
    for i, ht in enumerate(hit_audio if fail else hit_audio[:-1]):
        put(ht, custom if custom is not None else hit_sounds[i % 4], 0.45)
    if not fail:
        put(kill_t, S_("ko"), 1.0)
        put(kill_t + 0.05, S_("bomb", 3), 1.0)
    for ft in form_audio:
        put(ft, S_("powerup", 1), 0.8)
    tick = S_("tick")
    for s_ in range(10, 0, -1):                                    # tic-tac des 10 dernières secondes
        if seconds - s_ < stop_at:
            put(seconds - s_, tick, 0.5)
    if hakai:                                                      # Hakai : gong très grave + désintégration
        put(stop_at + 0.05, S_("summon"), 1.0)
        put(stop_at + 0.7, S_("vanish"), 0.8)
        put(stop_at + 2.6, S_("win"), 0.8)
    else:
        put(kill_t + (0 if fail else stop_shift + 1.4), S_("win"), 0.8)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1))
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"kind": "powerup", "title": f"Can {hero_name} beat {boss_name} in under {int(seconds)} seconds?"
            + (f" {part}" if part else ""),
            "hero": hero_name, "boss": boss_name, "names": [hero_name, boss_name], "seed": seed, "hits": len(hits),
            "forms": [f["name"] for f in forms], "result": "hakai" if hakai else ("fail" if fail else "win"), "part": part, "seconds": round(duration, 1), "timer": seconds, "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    _brand_video(out)
    log.info("power up : %s vs %s, %d coups, %.0f s → %s", hero_name, boss_name, len(hits), duration, out.name)
    return out


def _brand_video(out):
    """Filigrane anti-vol sur les NOUVELLES vidéos (depuis le 02/11 ; config `slides.render.video_watermark`)."""
    from . import render as _r
    if _r.rcfg().get("video_watermark", True):
        try:
            _r.stamp_video(out)
        except Exception as e:  # pas de badge, ffmpeg… : la vidéo reste sans filigrane
            log.info("filigrane vidéo : %s", e)
