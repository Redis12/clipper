"""« Gauntlet » (04/11, idée de l'utilisateur : « Can Base Goku pass the One Piece gauntlet? ») : un héros trop fort
pour l'univers adverse enchaîne les K.O. SANS se transformer. Boîte quadrillée façon Power Up : le héros (petite
balle) rebondit et frappe l'adversaire du moment (grosse balle) ; chaque adversaire a plus de PV ; K.O. = explosion
+ « K.O.! », l'adversaire suivant tombe dans la boîte. Échelle des adversaires sous la boîte (barrés une fois battus).
Fin : « <HÉROS> CLEARED THE GAUNTLET » + « Who should he face next? Comment 👇 ».

`generate(hero={"name","image_path"}, foes=[{"name","image_path"}…], universe="One Piece")`."""
from __future__ import annotations

import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import config, db
from ..util import log, require_bin
from . import fusion, render, skits

W, H, FPS = 1080, 1920, 30
HERO_COL, BOSS_COL, YELLOW = (255, 150, 40), (235, 60, 70), (255, 214, 10)
STAGE_B, STAGE_H = (0.30, 0.36), (0.72, 0.76)              # sketches : place du boss / du héros (fractions de la boîte)


def simulate(seed: int, S: float, n_foes: int, hits_for, dt: float = 1 / 240, specials: list | None = None,
             lose_at: int | None = None, lose_after: float = 3.0):
    """Rend les positions image par image et les chocs. Le boss change après `hits_for(i)` coups (+ pause K.O.)."""
    rnd = random.Random(seed)
    rh = S * 0.075
    frames, hits, kos, events = [], [], [], []
    specials = specials or [None] * n_foes
    used = set()
    gag_until = 0.0
    phase_until = 0.0
    foe, got, t, next_frame, cool, pause = 0, 0, 0.0, 0.0, 0.0, 0.0

    def new_boss(i):
        RB = S * (0.15 + 0.07 * i / max(1, n_foes - 1))
        return RB, rnd.uniform(RB, S - RB), rnd.uniform(RB, S * 0.45), rnd.uniform(-1, 1) * S * 0.12, S * 0.05
    RB, bx, by, bvx, bvy = new_boss(0)
    if (specials[0] or {}).get("gag"):
        gag_until = float(specials[0].get("gag_s", 1.3))
        events.append(("gag", 0, 0.0, gag_until))
    hx, hy = S * 0.5, S * 0.85
    if (specials[0] or {}).get("stage"):                  # 20/11 : sketches, persos placés pour le gag
        bx, by, bvx = min(max(S * STAGE_B[0], RB), S - RB), min(max(S * STAGE_B[1], RB), S - RB), 0.0
        hx, hy = S * STAGE_H[0], S * STAGE_H[1]
    a = rnd.uniform(-2.4, -0.7)
    hv = S * 1.05
    hvx, hvy = math.cos(a) * hv, math.sin(a) * hv
    foe_t0 = 0.0
    meme = {}                                             # 09/11 : il rate (pet), « Nah, I'd win », il tombe
    while foe < n_foes:
        msp = specials[foe] or {}
        if msp.get("meme"):
            if "panel_at" in meme and "end" not in meme and t >= meme["panel_at"]:
                gag_until = t + float(msp.get("gag_s", 2.0))
                meme["end"] = gag_until
                events.append(("gag", foe, t, gag_until))
            if lose_at == foe and "end" in meme and t >= meme["end"]:
                events.append(("lose", foe, t, hx, hy))
                break
        elif lose_at is not None and foe == lose_at and t - foe_t0 >= lose_after:   # gauntlet inversé : il tombe
            events.append(("lose", foe, t, hx, hy))
            break
        if pause > 0:                                     # K.O. : tout s'arrête un instant
            pause -= dt
            if foe + 1 < n_foes and (specials[foe + 1] or {}).get("stage"):
                hx += (S * STAGE_H[0] - hx) * min(1.0, dt * 5)
                hy += (S * STAGE_H[1] - hy) * min(1.0, dt * 5)
            if pause <= 0:
                foe += 1
                if foe >= n_foes:
                    break
                RB, bx, by, bvx, bvy = new_boss(foe)
                got = 0
                foe_t0 = t
                sp = specials[foe] or {}
                if sp.get("stage"):
                    bx, by, bvx = min(max(S * STAGE_B[0], RB), S - RB), min(max(S * STAGE_B[1], RB), S - RB), 0.0
                    hx, hy = S * STAGE_H[0], S * STAGE_H[1]
                if sp.get("gag"):                         # gag au début (Sanji cuisine, Talk no Jutsu…)
                    gag_until = t + float(sp.get("gag_s", 1.3))
                    events.append(("gag", foe, t, gag_until))
                if math.hypot(hx - bx, hy - by) < RB + rh + 4:
                    hy = min(S - rh, by + RB + rh + 10)
        elif t < gag_until:
            sp = specials[foe] or {}                      # tout le monde attend la fin du gag
            if sp.get("auto_ko") and t + dt >= gag_until and ("auto", foe) not in used:
                used.add(("auto", foe))                   # 20/11 : le gag finit le combat (Zoro perdu, Goku à table…)
                if sp["auto_ko"] == "hit":
                    hx, hy = min(bx + RB + rh, S - rh), by
                    hits.append((t, bx + RB * 0.9, by, foe))
                if sp.get("hero_exit"):
                    hx = S * 1.35
                kos.append((t, bx, by, foe))
                pause = float(sp.get("ko_pause", 1.1))
        else:
            hx += hvx * dt
            hy += hvy * dt
            bx += bvx * dt
            by += bvy * dt
            for p, v, r in ((0, 0, rh), (1, 1, RB)):
                pass
            if hx < rh or hx > S - rh:
                hvx = -hvx
                hx = min(max(hx, rh), S - rh)
            if hy < rh or hy > S - rh:
                hvy = -hvy
                hy = min(max(hy, rh), S - rh)
            if bx < RB or bx > S - RB:
                bvx = -bvx
                bx = min(max(bx, RB), S - RB)
            if by < RB or by > S - RB:
                bvy = -bvy
                by = min(max(by, RB), S - RB)
            dx, dy = hx - bx, hy - by
            dist = math.hypot(dx, dy) or 1
            cool -= dt
            sp = specials[foe] or {}
            if dist < RB + rh and t >= phase_until and sp.get("tp") and ("tp", foe) not in used:
                used.add(("tp", foe))                     # Minato : Hiraishin, il disparaît et réapparaît plus loin
                ox_, oy_ = bx, by
                bx = S - bx if abs(S - 2 * bx) > RB * 2 else rnd.uniform(RB, S - RB)
                by = min(max(S - by, RB), S - RB)
                events.append(("tp", foe, t, ox_, oy_, bx, by))
                dx, dy = hx - bx, hy - by
                dist = math.hypot(dx, dy) or 1
            elif dist < RB + rh and sp.get("fake") and ("fake", foe) not in used:
                used.add(("fake", foe))                   # Itachi : genjutsu, il « meurt »… et revient derrière Goku
                gag_until = t + 1.3
                hv_ = math.hypot(hvx, hvy) or 1
                nbx = min(max(hx - hvx / hv_ * (RB + rh + 30), RB), S - RB)
                nby = min(max(hy - hvy / hv_ * (RB + rh + 30), RB), S - RB)
                events.append(("fake", foe, t, gag_until, bx, by))
                bx, by = nbx, nby
                hx, hy = hx + hvx / hv_ * 40, hy + hvy / hv_ * 40
                hx, hy = min(max(hx, rh), S - rh), min(max(hy, rh), S - rh)
                continue
            elif dist < RB + rh * 1.6 and sp.get("meme") and ("miss", foe) not in used and t - foe_t0 >= float(sp.get("miss_after", 0)):
                used.add(("miss", foe))                   # il passe juste à côté : MISS + pet
                phase_until = t + 0.6
                meme["panel_at"] = t + 0.6
                events.append(("miss", foe, t, phase_until))
            elif dist < RB + rh and sp.get("kamui") and ("kamui", foe) not in used:
                used.add(("kamui", foe))                  # Obito : Kamui, Goku passe à travers
                phase_until = t + 0.6
                events.append(("kamui", foe, t, phase_until))
            if dist < RB + rh and t < phase_until:
                pass
            elif dist < RB + rh:
                nx, ny = dx / dist, dy / dist
                hx, hy = bx + nx * (RB + rh + 0.5), by + ny * (RB + rh + 0.5)
                dot = hvx * nx + hvy * ny
                if dot < 0:
                    hvx -= 2 * dot * nx
                    hvy -= 2 * dot * ny
                    ang = math.atan2(hvy, hvx) + rnd.uniform(-0.25, 0.25)   # un peu de hasard : pas de boucle
                    hvx, hvy = math.cos(ang) * hv, math.sin(ang) * hv
                    bvx -= nx * S * 0.05
                    bvy -= ny * S * 0.05
                    spd = math.hypot(bvx, bvy) or 1
                    lim = S * 0.16
                    if spd > lim:
                        bvx, bvy = bvx / spd * lim, bvy / spd * lim
                if cool <= 0:
                    cool = 0.12
                    got += 1
                    hits.append((t, bx + nx * RB, by + ny * RB, foe))
                    if got >= hits_for(foe):
                        kos.append((t, bx, by, foe))
                        pause = float(sp.get("ko_pause", 1.1))
        t += dt
        if t >= next_frame:
            frames.append((bx, by, RB, hx, hy, rh, foe, pause > 0))
            next_frame += 1 / FPS
        if t > 300:
            break
    return {"frames": frames, "hits": hits, "kos": kos, "events": events}


def generate(hero: dict, foes: list[dict], universe: str = "One Piece", out: Path | None = None,
             seed: int | None = None, base_hits: int = 3, step_hits: int = 2, dmg: int = 9001,
             lose_at: int | None = None, lose_after: float = 3.0, title: tuple | None = None,
             lose_move: str | None = None, theme: dict | None = None, music: str | None = None,
             music_start: float = 0.0, music_gain: float = 0.35, lose_cta: str | None = None,
             lose_image: str | None = None, final_image: str | None = None, final_s: float = 1.8) -> Path:
    """theme (07/11, JJK) : hero / boss / accent (couleurs), bg (haut, bas), grid, font (police des titres)."""
    global HERO_COL, BOSS_COL, YELLOW
    saved = (HERO_COL, BOSS_COL, YELLOW)
    th = theme or {}
    HERO_COL, BOSS_COL, YELLOW = th.get("hero", HERO_COL), th.get("boss", BOSS_COL), th.get("accent", YELLOW)
    try:
        return _generate(hero, foes, universe, out, seed, base_hits, step_hits, dmg, lose_at, lose_after, title,
                         lose_move, th, music, music_start, music_gain, lose_cta, lose_image,
                         final_image, final_s)
    finally:
        HERO_COL, BOSS_COL, YELLOW = saved


def _generate(hero, foes, universe, out, seed, base_hits, step_hits, dmg, lose_at, lose_after, title, lose_move,
              th, music, music_start, music_gain, lose_cta=None, lose_image=None, final_image=None,
              final_s=1.8) -> Path:
    from PIL import ImageFont
    from . import fxengine, vfxgen
    tfont = (lambda sz: ImageFont.truetype(th["font"], sz)) if th.get("font") else render.font
    k = W / 1080
    n = len(foes)
    S = W * 0.86
    ox, oy = (W - S) / 2, H * 0.215
    hits_for = lambda i: (10 ** 6 if i == lose_at else int(foes[i].get("hits") or base_hits + step_hits * i))  # noqa: E731  « hits » par adversaire (boss finaux pas en un coup)
    seed = seed if seed is not None else random.randrange(1_000_000)
    specials = [{k_: v for k_, v in f.items() if k_ in ("gag", "gag_s", "tp", "kamui", "say", "fake", "meme", "miss_after",
                                                    "stage", "auto_ko", "hero_exit", "ko_pause")} or None for f in foes]
    sim = simulate(seed, S, n, hits_for, specials=specials, lose_at=lose_at, lose_after=lose_after)
    lost = next((e for e in sim["events"] if e[0] == "lose"), None)
    evs = sim["events"]
    gag_ev = {}
    for e in evs:
        if e[0] == "gag":
            gag_ev.setdefault(e[1], e)
    frames = sim["frames"]
    hit_by_frame: dict = {}
    for h in sim["hits"]:
        hit_by_frame.setdefault(int(h[0] * FPS), []).append(h)
    ko_by_frame = {int(x[0] * FPS): x for x in sim["kos"]}
    foe_icons = [fusion.icon(f["image_path"], 512, BOSS_COL) for f in foes]
    meme_icon = {i: fusion.icon(f["meme"], 512, BOSS_COL) for i, f in enumerate(foes) if f.get("meme")}
    meme_at = {e[1]: e[2] for e in sim["events"] if e[0] == "gag" and e[1] in meme_icon}
    def icon_of(i, t_):
        return meme_icon[i] if i in meme_icon and t_ >= meme_at.get(i, 1e9) else foe_icons[i]
    hero_icon = fusion.icon(hero["image_path"], 256, HERO_COL)
    small = [fusion.icon(f["image_path"], 96, (90, 90, 110)) for f in foes]
    if th.get("bg"):
        import numpy as np
        c0, c1 = (np.array(c, np.float32) for c in th["bg"])
        yy = np.linspace(0, 1, H)[:, None, None]
        grad = (c0 * (1 - yy) + c1 * yy).repeat(W, 1)
        bg = Image.fromarray(grad.clip(0, 255).astype(np.uint8)).convert("RGBA")
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for (gx, gy, gr, gc) in th.get("glows", []):
            gd.ellipse((gx * W - gr, gy * H - gr, gx * W + gr, gy * H + gr), fill=tuple(gc) + (110,))
        bg.alpha_composite(glow.filter(ImageFilter.GaussianBlur(120)))
    else:
        bg = Image.new("RGBA", (W, H), (12, 14, 22, 255))
    bd = ImageDraw.Draw(bg, "RGBA")
    stp = S / 24
    gcol = tuple(th.get("grid", (32, 36, 52)))
    if th.get("bg"):
        bd.rectangle((ox, oy, ox + S, oy + S), fill=(6, 4, 14, 170))
    for i in range(25):
        bd.line((ox + i * stp, oy, ox + i * stp, oy + S), fill=gcol, width=1)
        bd.line((ox, oy + i * stp, ox + S, oy + i * stp), fill=gcol, width=1)
    fl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(fl).rectangle((ox - 6 * k, oy - 6 * k, ox + S + 6 * k, oy + S + 6 * k), outline=YELLOW + (255,),
                                 width=int(8 * k))
    bg.alpha_composite(fl.resize((W // 4, H // 4)).filter(ImageFilter.GaussianBlur(4)).resize((W, H)))
    bg.alpha_composite(fl)
    tf = tfont(int((84 if th.get('font') else 62) * k))
    explo = list(vfxgen.frames("explosion", 256, BOSS_COL))
    parts = fxengine.Particles(seed)
    out = out or config.data_dir() / "fusions" / f"gauntlet_{seed}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp)], stdin=subprocess.PIPE)
    floats, ko_at, dealt = [], [], [0] * n
    panels: dict = {}
    by_ = [0.0]

    def banner(img_, text, age, col):
        if age > 1.0:
            return
        s_ = 1 + 0.35 * max(0.0, 1 - age / 0.15)
        yb_ = oy + 70 * k if by_[0] > S * 0.4 else oy + S - 70 * k      # loin du perso (pas sur son nom)
        ImageDraw.Draw(img_).text((W / 2, yb_), text, font=tfont(int(64 * k * s_)), anchor="mm",
                                  fill=col, stroke_width=int(6 * k), stroke_fill=(0, 0, 0))

    def bubble(img_, x, y, text):
        f_ = tfont(int(40 * k))
        dd = ImageDraw.Draw(img_)
        lines = render.wrap(text, f_, int(W * 0.6), dd) or [text]
        lh = int(48 * k)
        bw = max(render.text_width(dd, ln, f_) for ln in lines) + 50 * k
        bh = lh * len(lines) + 30 * k
        x0 = min(max(ox + 10 * k, x - bw / 2), ox + S - bw - 10 * k)
        y0 = max(oy + 120 * k, y - bh)
        dd.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=int(24 * k), fill=(255, 255, 255),
                             outline=(0, 0, 0), width=int(5 * k))
        tx = min(max(x, x0 + 30 * k), x0 + bw - 30 * k)
        dd.polygon([(tx - 18 * k, y0 + bh - 3), (tx + 18 * k, y0 + bh - 3), (tx, y0 + bh + 26 * k)], fill=(255, 255, 255))
        for i_, ln in enumerate(lines):
            render.draw_rich(img_, (x0 + bw / 2, y0 + 15 * k + i_ * lh), ln, f_, (20, 20, 20), "ma", 0, (0, 0, 0))
    hit_t, ko_t = [], []
    end_frames = int(FPS * (2.0 + (1.4 if lost else 0)))
    fin_frames = int(FPS * final_s) if final_image else 0
    fin_img = None
    if final_image:                                       # 20/11 : image finale plein écran APRÈS l'écran de fin (meme)
        src_ = Image.open(final_image).convert("RGB")
        sq = min(src_.size)
        src_ = src_.crop(((src_.width - sq) // 2, (src_.height - sq) // 2, (src_.width + sq) // 2,
                          (src_.height + sq) // 2)).resize((W, W), Image.LANCZOS)
        fin_img = Image.new("RGB", (W, H), (0, 0, 0))
        fin_img.paste(src_, (0, (H - W) // 2))
    try:
        for fi in range(len(frames) + end_frames + fin_frames):
            if fi >= len(frames) + end_frames:
                proc.stdin.write(fin_img.tobytes())
                continue
            t = fi / FPS
            ended = fi >= len(frames)
            bx, by, RB, hx, hy, rh, foe, paused = frames[min(fi, len(frames) - 1)]
            for h in hit_by_frame.get(fi, []):
                dealt[h[3]] += 1
                floats.append((t, ox + h[1], oy + h[2]))
                hit_t.append(t)
                parts.emit(ox + h[1], oy + h[2], 10, speed=(200 * k, 650 * k), col=(255, 220, 150), life=(0.15, 0.35),
                           size=(2 * k, 4 * k))
            if fi in ko_by_frame:
                x = ko_by_frame[fi]
                ko_at.append((t, ox + x[1], oy + x[2], x[3], RB))
                ko_t.append(t)
                parts.emit(ox + x[1], oy + x[2], 70, speed=(300 * k, 1200 * k), col=(255, 190, 140), life=(0.3, 0.9),
                           size=(3 * k, 7 * k))
            parts.step(1 / FPS)
            img = bg.copy()
            d = ImageDraw.Draw(img)
            # titre
            t1, t2 = title or (f"Can Base {hero['name']} beat", f"the {universe.upper()} GAUNTLET?")
            render.draw_rich(img, (W / 2, H * 0.04), t1, tf, (255, 255, 255), "ma",
                             int(4 * k), (0, 0, 0))
            d = ImageDraw.Draw(img)
            f2 = tfont(int((96 if th.get('font') else 70) * k))
            while f2.size > 30 and render.text_width(d, t2, f2) > W * 0.94:
                f2 = tfont(f2.size - 3)
            d.text((W / 2, H * 0.04 + (100 if th.get('font') else 76) * k), t2, font=f2,
                   anchor="ma", fill=tuple(th.get("title2", BOSS_COL)), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            kills = sum(1 for x in ko_at)
            d.text((W / 2, oy - 34 * k), f"KILLS {kills}/{n}", font=tfont(int(44 * k)), anchor="mm",
                   fill=YELLOW, stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            # adversaire du moment (pas pendant le K.O.)
            sk = foes[foe].get("skit") if not ended else None      # 20/11 : sketch de l'adversaire
            ge = gag_ev.get(foe)
            pz, sk_age, sk_dur = None, 0.0, 0.0
            if sk and ge and t >= ge[2]:
                sk_age, sk_dur = t - ge[2], ge[3] - ge[2]
                sctx = dict(k=k, S=S, ox=ox, oy=oy, fx=ox + bx, fy=oy + by, R=RB, hx=ox + hx, hy=oy + hy, rh=rh,
                            hs=rh * 2, font=tfont, foe=foes[foe])
                pz = skits.pose(sk, sk_age, sk_dur, sctx)
                sctx["pose"] = pz
            fpos = (ox + bx + (pz["fdx"] if pz else 0), oy + by + (pz["fdy"] if pz else 0))
            if not ended and (not paused or (pz and pz["keep"])) and not (pz and pz["fhide"]):
                gnow = [e for e in evs if e[0] in ("gag", "fake") and e[1] == foe and e[2] <= t < e[3]]
                fxk = foes[foe].get("fx")
                sc_, dx_ = 1.0, 0.0
                hide = False
                if gnow:
                    q = (t - gnow[0][2]) / max(0.1, gnow[0][3] - gnow[0][2])
                    if fxk == "inflate":                         # Gear 5 : gonfle comme un ballon
                        sc_ = 1 + 0.45 * math.sin(min(1.0, q) * math.pi / 2) + 0.05 * math.sin(t * 30)
                    elif fxk == "lost":                          # Zoro arrive par le mauvais côté
                        dx_ = (1 - min(1.0, q / 0.6)) * (S * 0.6)
                    if gnow[0][0] == "fake" and q < 0.5:
                        hide = True
                RBd = int(RB * 2 * sc_)
                ic = icon_of(foe, t).resize((RBd, RBd), Image.LANCZOS)
                dy_ = 0.0
                if pz:
                    dx_ += pz["fdx"]
                    dy_ = pz["fdy"]
                    if pz["fflip"]:
                        ic = ic.transpose(Image.FLIP_LEFT_RIGHT)
                    if pz["frot"]:
                        ic = ic.rotate(pz["frot"], resample=Image.BICUBIC)
                if hide:
                    ic.putalpha(0)
                if any(e[0] == "kamui" and e[1] == foe and e[2] <= t < e[3] for e in evs):
                    ic.putalpha(ic.getchannel("A").point(lambda v: v * 35 // 100))   # intangible
                if hit_by_frame.get(fi) or hit_by_frame.get(fi - 1):
                    red = Image.new("RGBA", ic.size, (255, 40, 40, 255))
                    red.putalpha(ic.getchannel("A").point(lambda v: v // 2))
                    ic = Image.alpha_composite(ic, red)
                img.alpha_composite(ic, (int(ox + bx + dx_ - RBd / 2), int(oy + by + dy_ - RBd / 2)))
                d = ImageDraw.Draw(img)
                hp = 1 - dealt[foe] / hits_for(foe)
                bw = RB * 1.6
                x0, y0 = ox + bx + dx_ - bw / 2, oy + by - RBd / 2 - 26 * k
                if y0 < oy + 50 * k:                              # trop haut (sous « KILLS ») : sous la balle
                    y0 = oy + by + RBd / 2 + 46 * k
                if paused:
                    hide = True
                if not hide:
                    d.rectangle((x0 - 3, y0 - 3, x0 + bw + 3, y0 + 16 * k + 3), fill=(0, 0, 0))
                    d.rectangle((x0, y0, x0 + bw * hp, y0 + 16 * k), fill=(235, 60, 70))
                if not hide:
                  d.text((ox + bx + dx_, y0 - 8 * k), foes[foe]["name"].upper(), font=tfont(int(30 * k)), anchor="md",
                       fill=(255, 255, 255), stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
            # héros
            hs = int(rh * 2)
            hx_s, hy_s = hx, hy
            if pz:
                hx, hy = hx + pz["hdx"], hy + pz["hdy"] + pz["hbob"]
            au = Image.new("RGBA", (hs * 3, hs * 3), (0, 0, 0, 0))
            ImageDraw.Draw(au).ellipse((hs * 0.7, hs * 0.7, hs * 2.3, hs * 2.3), fill=(255, 200, 80, 90))
            au = au.filter(ImageFilter.GaussianBlur(hs * 0.25))
            img.alpha_composite(au, (int(ox + hx - au.width / 2), int(oy + hy - au.height / 2)))
            if pz and pz["hscale"] != 1.0:
                hs = int(hs * pz["hscale"])
            img.alpha_composite(hero_icon.resize((hs, hs), Image.LANCZOS), (int(ox + hx - hs / 2), int(oy + hy - hs / 2)))
            hpos = (ox + hx, oy + hy)
            if pz:
                skits._goggles(img, ox + hx, oy + hy, hs, k, pz["goggles"])
                sctx.update(fx=fpos[0], fy=fpos[1], hx=ox + hx_s, hy=oy + hy_s)
                skits.draw(sk, sk_age, sk_dur, sctx, img)
                d = ImageDraw.Draw(img)
            hx, hy = hx_s, hy_s
            by_[0] = by
            for ev in evs:                                       # gags et pouvoirs (Hiraishin, Kamui, Talk no Jutsu…)
                kind, ef, t0 = ev[0], ev[1], ev[2]
                age = t - t0
                if kind == "tp" and 0 <= age < 0.9:              # image rémanente + éclair jaune
                    _, _, _, x0_, y0_, x1_, y1_ = ev
                    gh = foe_icons[ef].resize((int(RB * 2), int(RB * 2)))
                    gh.putalpha(gh.getchannel("A").point(lambda v: int(v * 0.5 * (1 - age / 0.9))))
                    img.alpha_composite(gh, (int(ox + x0_ - RB), int(oy + y0_ - RB)))
                    dl = ImageDraw.Draw(img)
                    if age < 0.25:
                        dl.line((ox + x0_, oy + y0_, ox + x1_, oy + y1_), fill=(255, 230, 90), width=int(14 * k))
                    banner(img, foes[ef].get("tp_name", "FLYING RAIJIN!"), age, (255, 225, 80))
                    if age < 0.6:
                        dl.text((ox + hx, oy + hy - 70 * k), "MISS!", font=tfont(int(44 * k)), anchor="mm",
                                fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                elif kind == "miss" and 0 <= age < 0.9 and foes[ef].get("miss_label"):
                    banner(img, foes[ef]["miss_label"], age, (255, 230, 90))   # 09/11 : par défaut aucun texte (le raté se voit)
                elif kind == "kamui" and 0 <= age < 1.1:
                    dl = ImageDraw.Draw(img)
                    for j in range(5):                           # tourbillon violet autour d'Obito
                        rr = RB * (1.05 + 0.12 * j)
                        a0 = (age * 520 + j * 70) % 360
                        dl.arc((ox + bx - rr, oy + by - rr, ox + bx + rr, oy + by + rr), a0, a0 + 200,
                               fill=(150, 80, 230), width=int(6 * k))
                    banner(img, foes[ef].get("kamui_name", "KAMUI!"), age, (175, 110, 255))
                    if age < 0.7:
                        dl.text((ox + hx, oy + hy - 70 * k), "MISS!", font=tfont(int(44 * k)), anchor="mm",
                                fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                elif kind == "fake" and t0 <= t < ev[3] + 0.4:   # genjutsu : corbeaux, écran rouge, il revient
                    q = age / (ev[3] - t0)
                    tint = Image.new("RGBA", (W, H), (140, 0, 0, int(110 * max(0.0, 1 - abs(q - 0.4) * 1.6))))
                    img.alpha_composite(tint)
                    dl = ImageDraw.Draw(img)
                    if q < 0.7:                                  # corbeaux qui s'envolent de l'ancienne place
                        rc = random.Random(ef)
                        for j in range(16):
                            ang = rc.uniform(0, 2 * math.pi)
                            dd_ = RB * (0.3 + 2.2 * q) * rc.uniform(0.6, 1.2)
                            cx_ = ox + ev[4] + math.cos(ang) * dd_
                            cy_ = oy + ev[5] + math.sin(ang) * dd_ - 60 * k * q
                            w_ = 22 * k
                            dl.polygon([(cx_ - w_, cy_), (cx_, cy_ - w_ * 0.4), (cx_ + w_, cy_), (cx_, cy_ + w_ * 0.25)],
                                       fill=(10, 10, 14))
                    if q < 0.45:
                        dl.text((ox + ev[4], oy + ev[5]), "K.O.?", font=tfont(int(90 * k)), anchor="mm",
                                fill=YELLOW, stroke_width=int(6 * k), stroke_fill=(0, 0, 0))
                    else:
                        banner(img, foes[ef].get("fake_label", "GENJUTSU!"), age - (ev[3] - t0) * 0.45, (230, 40, 40))
                        dl.text((ox + bx, max(oy + 40 * k, oy + by - RB - 70 * k)), "Behind you.", font=tfont(int(44 * k)), anchor="mm",
                                fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
                elif kind == "gag" and t0 <= t < ev[3] and foes[ef].get("fx") == "strings":
                    dl = ImageDraw.Draw(img)                     # Doflamingo : fils de marionnette qui ratent
                    q = age / (ev[3] - t0)
                    for j in range(6):
                        ex_ = ox + hx + (j - 2.5) * 30 * k + 60 * k * math.sin(j + t * 5)
                        ey_ = oy + hy - 80 * k
                        fx_ = ox + bx + (ex_ - ox - bx) * min(1.0, q * 1.5)
                        fy_ = oy + by + (ey_ - oy - by) * min(1.0, q * 1.5)
                        dl.line((ox + bx, oy + by, fx_, fy_), fill=(240, 240, 255), width=int(3 * k))
                    bubble(img, ox + bx, oy + by - RB - 40 * k, foes[ef].get("say", ""))
                    banner(img, foes[ef].get("gag_label", ""), age, (255, 150, 220))
                elif kind == "gag" and t0 <= t < ev[3] and foes[ef].get("panel"):
                    # case de manga plein écran (07/11 : « Nah, I'd win » de Gojo juste avant Sukuna)
                    pim = panels.get(ef)
                    if pim is None:
                        src = Image.open(foes[ef]["panel"]).convert("RGBA")
                        sc_ = min(W * 0.86 / src.width, H * 0.5 / src.height)
                        pim = panels[ef] = src.resize((int(src.width * sc_), int(src.height * sc_)), Image.LANCZOS)
                    dur_ = ev[3] - t0
                    fade = min(1.0, age / 0.12, max(0.0, (dur_ - age) / 0.2))
                    img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(190 * fade))))
                    pop = 1 + 0.18 * max(0.0, 1 - age / 0.18)
                    pz = pim.resize((int(pim.width * pop), int(pim.height * pop)))
                    if fade < 1:
                        pz.putalpha(pz.getchannel("A").point(lambda v, f_=fade: int(v * f_)))
                    fr_ = Image.new("RGBA", (pz.width + int(16 * k), pz.height + int(16 * k)), (255, 255, 255, int(255 * fade)))
                    img.alpha_composite(fr_, (int(W / 2 - fr_.width / 2), int(H * 0.47 - fr_.height / 2)))
                    img.alpha_composite(pz, (int(W / 2 - pz.width / 2), int(H * 0.47 - pz.height / 2)))
                    if foes[ef].get("gag_label"):
                        banner(img, foes[ef]["gag_label"], age, (255, 255, 255))
                elif kind == "gag" and t0 <= t < ev[3] and not foes[ef].get("skit"):   # bulle, texte qui s'écrit
                    say = foes[ef].get("say", "...")
                    nch = max(1, int(len(say) * min(1.0, age / max(0.3, (ev[3] - t0) * 0.7))))
                    bx_b = bx + (S * 0.6 * (1 - min(1.0, (age / (ev[3] - t0)) / 0.6)) if foes[ef].get("fx") == "lost" else 0)
                    bubble(img, ox + bx_b, oy + by - RB - 40 * k, say[:nch])
                    if foes[ef].get("gag_label"):
                        banner(img, foes[ef]["gag_label"], age, (255, 255, 255))
            # « -9,001 »
            keep = []
            for (ft, fx_, fy_) in floats:
                a = (t - ft) / 0.7
                if a < 1:
                    keep.append((ft, fx_, fy_))
                    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    al = int(255 * (1 - a))
                    ImageDraw.Draw(lay).text((fx_, fy_ - 60 * k * a), f"-{dmg:,}", font=tfont(int(38 * k)),
                                             anchor="mm", fill=(255, 230, 120, al), stroke_width=int(3 * k),
                                             stroke_fill=(0, 0, 0, al))
                    img.alpha_composite(lay)
            floats[:] = keep[-6:]
            # K.O. : explosion + texte
            for (kt, kx, ky, kf, kR) in ko_at[-1:]:
                fo_ = foes[kf]
                kp = max(0.9, float(fo_.get("ko_pause", 1.1)) - 0.1)
                a = (t - kt) / kp
                if 0 <= a < 1:
                    if fo_.get("ko_fx") == "volcano":
                        skits.volcano(img, a, dict(k=k, ox=ox, oy=oy, S=S), foe_icons[kf], kx, ky, kR)
                    elif fo_.get("ko_boom", True):
                        f_ = explo[min(len(explo) - 1, int(a * len(explo)))]
                        sz = int(kR * 4)
                        img.alpha_composite(f_.resize((sz, sz)), (int(kx - sz / 2), int(ky - sz / 2)))
                    d = ImageDraw.Draw(img)
                    a2 = a * kp / 0.9 - float(fo_.get("ko_text_at", 0)) / 0.9
                    if a2 >= 0:
                        s = 1 + 0.4 * max(0.0, 1 - a2 / 0.2)
                        kt_ = fo_.get("ko_text", "K.O.!")
                        kf_ = tfont(int(150 * k * s))
                        while kf_.size > 40 and render.text_width(d, kt_, kf_) > S * 0.94:
                            kf_ = tfont(kf_.size - 4)
                        ky_ = oy + S * float(fo_.get("ko_y", 0.5))
                        d.text((W / 2, ky_), kt_, font=kf_, anchor="mm",
                               fill=YELLOW, stroke_width=int(7 * k), stroke_fill=(0, 0, 0))
                        d.text((W / 2, ky_ + 110 * k), (fo_.get("ko_sub") or fo_["name"]).upper(), font=tfont(int(54 * k)),
                               anchor="mm", fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
            en = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            parts.draw(en, 1.0)
            img = fxengine.bloom(img, en, 0.7)
            d = ImageDraw.Draw(img)
            # échelle des adversaires sous la boîte
            yb = oy + S + 40 * k
            per_row = min(n, 6)
            sz = int(min(120 * k, (W * 0.9) / per_row - 14 * k))
            for i, sm in enumerate(small):
                row, col = divmod(i, per_row)
                cnt = min(per_row, n - row * per_row)
                x = W / 2 + (col - (cnt - 1) / 2) * (sz + 14 * k) - sz / 2
                y = yb + row * (sz + 20 * k)
                ic = sm.resize((sz, sz), Image.LANCZOS)
                done = any(kf == i for (_, _, _, kf, _) in ko_at)
                if done:
                    g = ic.convert("LA").convert("RGBA")
                    g.putalpha(ic.getchannel("A"))
                    ic = g
                img.alpha_composite(ic, (int(x), int(y)))
                d = ImageDraw.Draw(img)
                if done:
                    d.line((x + 10, y + 10, x + sz - 10, y + sz - 10), fill=(235, 50, 60), width=int(8 * k))
                    d.line((x + sz - 10, y + 10, x + 10, y + sz - 10), fill=(235, 50, 60), width=int(8 * k))
                elif i == foe and not ended:
                    d.ellipse((x - 4, y - 4, x + sz + 4, y + sz + 4), outline=YELLOW, width=int(5 * k))
            if pz is not None:                                    # sketch : effet plein écran, bulles, étiquette
                img = skits.post(sk, sk_age, sk_dur, img)
                for (a_, b_, who, txt) in foes[foe].get("lines", []):
                    if a_ <= sk_age < b_:
                        nch = max(1, int(len(txt) * min(1.0, (sk_age - a_) / max(0.25, (b_ - a_) * 0.45))))
                        if foe == 0 and a_ == 0:                  # 1re image : la phrase est déjà là
                            nch = len(txt)
                        if who == "hero":
                            bubble(img, hpos[0], hpos[1] - hs / 2 - 30 * k, txt[:nch])
                        else:
                            bubble(img, fpos[0], fpos[1] - RB - 40 * k, txt[:nch])
                lb_ = foes[foe].get("label")
                if lb_ and sk_age >= lb_[0]:
                    banner(img, lb_[1], sk_age - lb_[0], tuple(lb_[2]) if len(lb_) > 2 else (255, 255, 255))
            if ended and lost and t - len(frames) / FPS < 1.4:  # il tombe : écran rouge, icône grise qui tremble
                e = t - len(frames) / FPS
                img.alpha_composite(Image.new("RGBA", (W, H), (150, 0, 0, int(120 * min(1.0, e / 0.2)))))
                lb = frames[-1]                                   # le vainqueur reste à sa place
                bic = icon_of(lost[1], t).resize((int(lb[2] * 2), int(lb[2] * 2)), Image.LANCZOS)
                img.alpha_composite(bic, (int(ox + lb[0] - lb[2]), int(oy + lb[1] - lb[2])))
                hs = int(rh * 2)
                g = hero_icon.resize((hs, hs)).convert("LA").convert("RGBA")
                g.putalpha(hero_icon.resize((hs, hs)).getchannel("A"))
                sh_ = 10 * k * max(0.0, 1 - e / 0.8) * math.sin(e * 70)
                img.alpha_composite(g, (int(ox + lost[3] - hs / 2 + sh_), int(oy + lost[4] - hs / 2)))
                d = ImageDraw.Draw(img)
                banner(img, lose_move or f"{foes[lost[1]]['name'].upper()}!", e, (255, 60, 60))
                if foes[lost[1]].get("ora"):
                    skits.ora(img, e, ox + lost[3], oy + lost[4] - 60 * k, k, tfont, (ox, oy, ox + S, oy + S))
                    d = ImageDraw.Draw(img)
                d.text((ox + lost[3], oy + lost[4] - hs), "DOWN!", font=tfont(int(60 * k)), anchor="mm",
                       fill=(255, 255, 255), stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
            elif ended and lost:                                  # écran de défaite
                e = t - len(frames) / FPS - 1.4
                img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(205 * min(1.0, e / 0.3)))))
                big = int(W * 0.46)
                if lose_image:                                    # 20/11 : image finale au choix (Joseph furieux)
                    bigL = int(W * 0.66)
                    src_ = Image.open(lose_image).convert("RGB")
                    sq = min(src_.size)
                    src_ = src_.crop(((src_.width - sq) // 2, (src_.height - sq) // 2,
                                      (src_.width + sq) // 2, (src_.height + sq) // 2)).resize((bigL, bigL), Image.LANCZOS)
                    pop_ = 1 + 0.12 * max(0.0, 1 - e / 0.25)
                    bz = int(bigL * pop_)
                    src_ = src_.resize((bz, bz), Image.LANCZOS).convert("RGBA")
                    msk = Image.new("L", (bz, bz), 0)
                    ImageDraw.Draw(msk).rounded_rectangle((0, 0, bz, bz), radius=int(36 * k), fill=255)
                    src_.putalpha(msk)
                    gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                    ImageDraw.Draw(gl).rounded_rectangle((W / 2 - bz / 2 - 20 * k, H * 0.33 - 20 * k, W / 2 + bz / 2 + 20 * k,
                                                          H * 0.33 + bz + 20 * k), radius=int(50 * k), fill=(170, 90, 255, 200))
                    img.alpha_composite(gl.filter(ImageFilter.GaussianBlur(28 * k)))
                    img.alpha_composite(src_, (int(W / 2 - bz / 2), int(H * 0.33)))
                    big = bigL - int(H * 0.03)
                else:
                    img.alpha_composite(icon_of(lost[1], t).resize((big, big), Image.LANCZOS),
                                        (int(W / 2 - big / 2), int(H * 0.36)))
                d = ImageDraw.Draw(img)
                d.text((W / 2, H * 0.24), f"SURVIVED {lost[1]}/{n}", font=tfont(int(86 * k)), anchor="mm",
                       fill=YELLOW, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                d.text((W / 2, H * 0.24 + 92 * k), f"STOPPED BY {foes[lost[1]]['name'].upper()}",
                       font=tfont(int(58 * k)), anchor="mm", fill=(255, 80, 80), stroke_width=int(5 * k),
                       stroke_fill=(0, 0, 0))
                render.draw_rich(img, (W / 2, H * 0.36 + big + 40 * k), lose_cta or "Did he deserve to lose? Comment 👇",
                                 tfont(int(46 * k)), (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
            elif ended:                                           # écran de fin
                e = t - len(frames) / FPS
                dim = Image.new("RGBA", (W, H), (0, 0, 0, int(205 * min(1.0, e / 0.3))))
                img.alpha_composite(dim)
                big = int(W * 0.46)
                img.alpha_composite(hero_icon.resize((big, big), Image.LANCZOS), (int(W / 2 - big / 2), int(H * 0.36)))
                d = ImageDraw.Draw(img)
                d.text((W / 2, H * 0.27), f"{hero['name'].upper()} CLEARED", font=tfont(int(80 * k)), anchor="mm",
                       fill=HERO_COL, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                d.text((W / 2, H * 0.27 + 90 * k), "THE GAUNTLET", font=tfont(int(80 * k)), anchor="mm",
                       fill=YELLOW, stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
                render.draw_rich(img, (W / 2, H * 0.36 + big + 40 * k), "Who should he face next? Comment 👇",
                                 tfont(int(46 * k)), (255, 255, 255), "ma", int(3 * k), (0, 0, 0))
            proc.stdin.write(img.convert("RGB").tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué")
    finally:
        if proc.poll() is None:
            proc.kill()
    import numpy as np
    from . import domain
    dur = (len(frames) + end_frames + fin_frames) / FPS
    rate = fusion.RATE
    na = int(dur * rate) + rate
    audio = np.zeros(na, dtype=np.float32)

    def put(tt, x, g):
        i = int(tt * rate)
        if x is not None and 0 <= i < na:
            seg = x[: na - i]
            audio[i:i + len(seg)] += seg * g
    try:
        from . import seo
        fr = seo.anime_of(hero["name"])
        franchise = fr[0].lower() if fr else None
    except Exception:
        franchise = None
    hs_ = [domain.sfx("hit", mode="anime", seed=i, franchise=franchise) for i in range(4)]
    for i, tt in enumerate(hit_t):
        put(tt, hs_[i % 4], 0.3)
    for (tt, _x, _y, kf_, _r) in ko_at:
        if foes[kf_].get("ko_boom", True) or foes[kf_].get("ko_fx"):
            put(tt, domain.sfx("ko", mode="anime", franchise=franchise), 0.9)
            put(tt + 0.05, domain.sfx("bomb", mode="anime", seed=3, franchise=franchise), 0.8)
        else:
            put(tt, domain.sfx("ko", mode="anime", franchise=franchise), 0.5)
    def load_snd(p_):
        r_ = subprocess.run([ffmpeg, "-loglevel", "error", "-i", str(p_), "-f", "f32le", "-ac", "1", "-ar", str(rate), "-"],
                            capture_output=True)
        x_ = np.frombuffer(r_.stdout, np.float32).astype(np.float32)
        return x_ / (float(np.percentile(np.abs(x_), 99.9)) or 1.0) if len(x_) else None
    for ev in evs:
        if ev[0] in ("tp", "kamui", "fake"):
            put(ev[2], domain.sfx("vanish", mode="anime", franchise=franchise), 0.7)
        if ev[0] == "miss" and foes[ev[1]].get("miss_sound"):
            put(ev[2], load_snd(foes[ev[1]]["miss_sound"]), float(foes[ev[1]].get("miss_gain", 1.0)))
        if ev[0] == "gag" and ev[1] in meme_icon and foes[ev[1]].get("panel_sound"):
            put(ev[2], load_snd(foes[ev[1]]["panel_sound"]), 1.0)
    blip = None
    try:
        tt_ = np.arange(int(0.07 * rate)) / rate                 # « pop » de bulle
        blip = (np.sin(2 * np.pi * (700 + 900 * tt_ / 0.07) * tt_) * np.exp(-tt_ * 45)).astype(np.float32)
    except Exception:
        pass
    for fi_, fo_ in enumerate(foes):                             # 20/11 : sons des sketches
        ge_ = gag_ev.get(fi_)
        if not ge_:
            continue
        for (a_, _b, _w, _t) in fo_.get("lines", []):
            put(ge_[2] + a_, blip, 0.35)
        for wt in fo_.get("whoosh", []):
            put(ge_[2] + wt, domain.sfx("vanish", mode="anime", franchise=franchise), 0.6)
        for (st, sp_, g_, sd) in fo_.get("sounds", []):
            x_ = load_snd(sp_)
            if x_ is not None:
                x_ = x_[: int(sd * rate)].copy()
                fo = min(len(x_), int(0.15 * rate))
                if fo:
                    x_[-fo:] *= np.linspace(1, 0, fo)
                put(ge_[2] + st, x_, g_)
    if lost:
        if foes[lost[1]].get("ora"):
            for j in range(18):
                put(lost[2] + j * 0.055, hs_[j % 4], 0.45)
        put(lost[2], domain.sfx("ko", mode="anime", franchise=franchise), 1.0)
        put(lost[2] + 0.05, domain.sfx("bomb", mode="anime", seed=2, franchise=franchise), 0.8)
    put(len(frames) / FPS + (1.4 if lost else 0), domain.sfx("win"), 0.8)
    lvl = float(np.percentile(np.abs(audio), 99.7)) or 1.0
    audio = audio * min(1.0, 0.75 / lvl)
    if music:                                            # musique de fond continue (07/11 : thème JJK)
        r_ = subprocess.run([ffmpeg, "-loglevel", "error", "-ss", str(music_start), "-i", str(music), "-t", str(dur + 1),
                             "-f", "f32le", "-ac", "1", "-ar", str(rate), "-"], capture_output=True)
        mu = np.frombuffer(r_.stdout, np.float32)[:na].astype(np.float32)
        if len(mu):
            mu = mu / (float(np.percentile(np.abs(mu), 99.7)) or 1.0)
            env = np.ones(len(mu), np.float32)
            fi, fo = int(0.4 * rate), int(1.5 * rate)
            env[:fi] = np.linspace(0, 1, fi)
            e_ = min(len(mu), int(dur * rate))
            env[max(0, e_ - fo):e_] *= np.linspace(1, 0, e_ - max(0, e_ - fo))
            env[e_:] = 0
            audio[:len(mu)] += mu * env * music_gain
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, np.tanh(audio * 1.1) / math.tanh(1.1) * 0.24)   # ≈ −24 LUFS comme les autres formats
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp), "-i", str(wav), "-c:v", "copy", "-c:a", "aac",
                    "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"kind": "gauntlet", "title": " ".join(title) if title else f"Can Base {hero['name']} beat the {universe} gauntlet?",
            "lost_to": foes[lost[1]]["name"] if lost else None,
            "hero": hero["name"], "names": [hero["name"]] + [f["name"] for f in foes], "universe": universe,
            "seed": seed, "seconds": round(dur, 1), "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    from .domain import _brand_video
    _brand_video(out)
    log.info("gauntlet : %s vs %d adversaires, %.0f s → %s", hero["name"], n, dur, out.name)
    return out
