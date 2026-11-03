"""Vidéo « Fusion Race » : 2 bols Fusion l'un au-dessus de l'autre (ex. Goku vs Naruto), en même temps.
Le premier qui atteint sa forme finale gagne.

Pour que la course soit prenante, on simule d'abord en silence plusieurs courses (graines différentes, < 1 s chacune)
et on garde celle où le leader change le plus souvent et où la fin est la plus serrée, d'une durée raisonnable.
Puis on rend celle-là (la simulation est déterministe pour une graine donnée).
"""
from __future__ import annotations

import json
import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .. import db
from ..util import log, require_bin
from . import fusion, render

NEON = [(255, 170, 60), (90, 200, 255)]           # haut : orange, bas : bleu


def layout(W: int, H: int) -> list[dict]:
    """Deux bols : en haut à gauche (panneau à droite), en bas à droite (panneau à gauche)."""
    R = H * 0.165
    return [
        {"cx": W * 0.36, "cy": H * 0.34, "R": R, "panel_x": W * 0.82},
        {"cx": W * 0.64, "cy": H * 0.74, "R": R, "panel_x": W * 0.18},
    ]


def make_sides(chains: list[list[dict]], W: int, H: int, seed: int, c: dict) -> list[fusion.Feeder]:
    out = []
    for i, (tiers, L) in enumerate(zip(chains, layout(W, H))):
        sim = fusion.setup(len(tiers), W, H, seed * 7 + i * 1009, bounce=str(c.get("style", "bounce")) != "pile",
                           speed=float(c.get("speed", 0.6)), cx=L["cx"], cy=L["cy"], R=L["R"])
        out.append(fusion.Feeder(sim, sim.cy - sim.R - H * 0.035, c))
    return out


def progress(sim: fusion.Sim) -> float:
    """Avancement 0 → 1 : la meilleure forme, + un peu pour la « matière » accumulée (départage les égalités)."""
    if sim.top <= 0:
        return 1.0
    units = sum(2 ** b.tier for b in sim.balls) / 2 ** sim.top
    return min(1.0, (sim.best + min(0.99, units)) / sim.top) if sim.done_at < 0 else 1.0


def winner_of(sides: list[fusion.Feeder]) -> int | None:
    done = [(s.sim.done_at, i) for i, s in enumerate(sides) if s.sim.done_at >= 0]
    return min(done)[1] if done else None


def simulate(chains: list[list[dict]], W: int, H: int, seed: int, c: dict, fps: int = 30) -> dict:
    """Course en silence : durée, changements de leader, écart final."""
    sides = make_sides(chains, W, H, seed, c)
    sub = int(c.get("substeps", 6))
    lead, changes, t = 0, 0, 0.0
    limit = float(c.get("max_seconds", 120)) * 1.6
    while winner_of(sides) is None and t < limit:
        for s in sides:
            s.tick(1 / fps, sub)
        t += 1 / fps
        a, b = sides[0].sim.best, sides[1].sim.best
        now = (a > b) - (a < b)
        if now and now != lead:
            changes += lead != 0
            lead = now
    w = winner_of(sides)
    loser = 1 - w if w is not None else 0
    gap = 1 - progress(sides[loser].sim) if w is not None else 1.0
    return {"seed": seed, "seconds": t, "changes": changes, "gap": gap, "winner": w}


def pick_seed(chains, W, H, c, tries: int = 24, rnd: random.Random | None = None) -> dict:
    """La course la plus serrée parmi `tries` essais, de préférence entre 25 et 55 s."""
    rnd = rnd or random.Random()
    lo, hi = float(c.get("race_min_seconds", 25)), float(c.get("race_max_seconds", 55))
    best, best_score = None, -1e9
    for _ in range(tries):
        r = simulate(chains, W, H, rnd.randrange(1_000_000), c)
        if r["winner"] is None:
            continue
        score = r["changes"] * 2.0 - r["gap"] * 6.0
        if not lo <= r["seconds"] <= hi:
            score -= 4 + abs(r["seconds"] - (lo + hi) / 2) / 5
        if score > best_score:
            best, best_score = r, score
    return best or {"seed": rnd.randrange(1_000_000), "changes": 0, "gap": 1, "seconds": 0, "winner": None}


class RacePainter:
    def __init__(self, sides: list[fusion.Feeder], chains: list[list[dict]], names: list[str], W: int, H: int,
                 title: str):
        self.sides, self.chains, self.names, self.W, self.H, self.title = sides, chains, names, W, H, title
        self.k = W / 1080
        self.p = [fusion.Painter(s.sim, ch, W, H, title, funnel_top=s.funnel_top, with_bg=False)
                  for s, ch in zip(sides, chains)]
        self.L = layout(W, H)
        self.bg = self._background()

    def _background(self) -> Image.Image:
        W, H, k = self.W, self.H, self.k
        bg = Image.new("RGBA", (W, H), (12, 12, 22, 255))
        for p, col in zip(self.p, NEON):
            p.draw_bowl(bg, col)
        d = ImageDraw.Draw(bg)
        tf = render.font(int(70 * k))
        while tf.size > 30 and len(render.wrap(self.title.upper(), tf, int(W * 0.92), d)) > 2:
            tf = render.font(tf.size - 4)                      # le titre tient toujours en 2 lignes
        y = int(H * 0.022)
        for line in render.wrap(self.title.upper(), tf, int(W * 0.92), d):
            d.text((W / 2, y), line, font=tf, anchor="ma", fill=(240, 242, 250), stroke_width=int(3 * k),
                   stroke_fill=(0, 0, 0))
            y += int(sum(tf.getmetrics()) * 1.02)
        vs = render.font(int(96 * k))                         # « VS » entre les deux bols
        ymid = (self.L[0]["cy"] + self.L[0]["R"] + self.L[1]["cy"] - self.L[1]["R"]) / 2 - H * 0.02
        d.text((W / 2, ymid), "VS", font=vs, anchor="mm", fill=(255, 214, 10), stroke_width=int(5 * k),
               stroke_fill=(0, 0, 0))
        return bg

    def panel(self, img: Image.Image, i: int, winner: int | None) -> None:
        """Nom du perso, sa forme actuelle (déjà vue dans le bol) et une barre d'avancement."""
        W, H, k = self.W, self.H, self.k
        s, L, p = self.sides[i].sim, self.L[i], self.p[i]
        d = ImageDraw.Draw(img)
        x = L["panel_x"]
        y = L["cy"] - L["R"] * 0.85
        nf = render.font(int(52 * k))
        name = self.names[i].upper()
        while nf.size > 24 and render.text_width(d, name, nf) > W * 0.32:
            nf = render.font(nf.size - 4)
        d.text((x, y), name, font=nf, anchor="ma", fill=NEON[i], stroke_width=int(3 * k), stroke_fill=(0, 0, 0))
        size = int(W * 0.22)
        iy = int(y + 80 * k)
        img.alpha_composite(p.get_icon(s.best, size), (int(x - size / 2), iy))
        ff = render.font(int(36 * k))
        form = self.chains[i][s.best]["name"].upper()
        while ff.size > 18 and render.text_width(d, form, ff) > W * 0.32:
            ff = render.font(ff.size - 2)
        fy = iy + size + 18 * k
        d.text((x, fy), form, font=ff, anchor="ma", fill=(255, 255, 255), stroke_width=int(2 * k),
               stroke_fill=(0, 0, 0))
        bw, bh = W * 0.28, 22 * k                              # barre d'avancement
        by = fy + 60 * k
        d.rounded_rectangle((x - bw / 2, by, x + bw / 2, by + bh), radius=bh / 2, fill=(40, 42, 60))
        frac = s.best / max(1, s.top)
        if frac > 0:
            d.rounded_rectangle((x - bw / 2, by, x - bw / 2 + max(bh, bw * frac), by + bh), radius=bh / 2,
                                fill=NEON[i])
        d.text((x, by + bh + 12 * k), f"{s.best + 1}/{s.top + 1}", font=render.font(int(30 * k)), anchor="ma",
               fill=(200, 205, 220))

    def frame(self, winner: int | None = None, win_t: float = 0.0) -> Image.Image:
        img = self.bg.copy()
        for i, (side, p) in enumerate(zip(self.sides, self.p)):
            p.draw_dynamic(img, side.drop, side.waiting if winner is None else None, side.tube)
        if winner is not None:                                 # le perdant devient gris, le gagnant s'illumine
            loser = 1 - winner
            Lw, Ll = self.L[winner], self.L[loser]
            a = min(1.0, win_t / 0.3)
            box = (int(Ll["cx"] - Ll["R"] - 10), int(Ll["cy"] - Ll["R"] - 10), int(Ll["cx"] + Ll["R"] + 10),
                   int(Ll["cy"] + Ll["R"] + 10))
            reg = img.crop(box)
            grey = Image.blend(reg, reg.convert("LA").convert("RGBA"), a * 0.85)
            mask = Image.new("L", reg.size, 0)                 # seulement l'intérieur du bol (rond)
            ImageDraw.Draw(mask).ellipse((10, 10, reg.width - 11, reg.height - 11), fill=255)
            img.paste(grey, box[:2], mask)
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            rr = Lw["R"] * (1.02 + 0.08 * math.sin(win_t * 9))
            ImageDraw.Draw(glow).ellipse((Lw["cx"] - rr, Lw["cy"] - rr, Lw["cx"] + rr, Lw["cy"] + rr),
                                         outline=NEON[winner] + (int(230 * a),), width=int(26 * self.k))
            img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10 * self.k)))
        for i in range(2):
            self.panel(img, i, winner)
        return img.convert("RGB")

    def final(self, winner: int, t: float, seconds: float) -> Image.Image:
        W, H, k = self.W, self.H, self.k
        img = Image.new("RGBA", (W, H), (12, 12, 22, 255))
        d = ImageDraw.Draw(img)
        p, s = self.p[winner], self.sides[winner].sim
        col = NEON[winner]
        a = min(1.0, t / 0.4)
        size = int(W * 0.58 * (0.7 + 0.3 * a))
        cy = H * 0.42
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse((W / 2 - size * 0.62, cy - size * 0.62, W / 2 + size * 0.62, cy + size * 0.62),
                                     fill=col + (150,))
        img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60 * k)))
        img.alpha_composite(p.get_icon(s.top, size), (int(W / 2 - size / 2), int(cy - size / 2)))
        d.text((W / 2, H * 0.1), "WINNER", font=render.font(int(120 * k)), anchor="ma", fill=col,
               stroke_width=int(5 * k), stroke_fill=(0, 0, 0))
        y = cy + size / 2 + 40 * k
        d.text((W / 2, y), self.names[winner].upper(), font=render.font(int(84 * k)), anchor="ma",
               fill=(255, 255, 255), stroke_width=int(4 * k), stroke_fill=(0, 0, 0))
        y += 100 * k
        sub = f"{self.chains[winner][s.top]['name']} in {seconds:.0f}s"
        d.text((W / 2, y), sub, font=render.font(int(46 * k)), anchor="ma", fill=(210, 215, 230))
        lo = 1 - winner
        ls = self.sides[lo].sim
        d.text((W / 2, y + 70 * k), f"{self.names[lo]} stopped at {self.chains[lo][ls.best]['name']}",
               font=render.font(int(38 * k)), anchor="ma", fill=(150, 155, 175))
        cta = (render.rcfg().get("end_cta") or "").strip()
        if cta:
            render.draw_rich(img, (W / 2, H * 0.86), cta, render.font(int(52 * k)), render.rcfg()["accent_color"],
                             "ma", int(3 * k), (0, 0, 0))
        return img.convert("RGB")


def generate(chains: list[list[dict]], names: list[str], title: str | None = None,
             sounds: list[str | None] | None = None, fat: float = 1.0, seed: int | None = None,
             tries: int | None = None, out: Path | None = None) -> Path:
    """Rend la course la plus serrée trouvée. `chains` = 2 chaînes de niveaux, `names` = 2 noms (Goku, Naruto)."""
    c = fusion.fcfg()
    if len(chains) != 2 or any(len(ch) < 3 for ch in chains):
        raise ValueError("Il faut 2 chaînes d'au moins 3 niveaux")
    chains = [ch[:10] for ch in chains]
    W, H = (int(v) for v in c.get("size", [1080, 1920]))
    fps = int(c.get("fps", 30))
    title = title or f"{names[0]} vs {names[1]}: who transforms first?"
    sounds = list(sounds or [None, None]) + [None, None]
    if seed is None:
        pick = pick_seed(chains, W, H, c, int(tries or c.get("race_tries", 24)))
        seed = pick["seed"]
        log.info("fusion race : graine %s (%d changements de leader, écart %.2f, %.0f s)", seed, pick["changes"],
                 pick["gap"], pick["seconds"])
    sides = make_sides(chains, W, H, seed, c)
    painter = RacePainter(sides, chains, names, W, H, title)
    out = out or fusion.out_dir() / f"race_{seed}.mp4"
    tmp_video = out.with_suffix(".video.mp4")
    ffmpeg = require_bin("ffmpeg")
    proc = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                             "-crf", "20", "-pix_fmt", "yuv420p", str(tmp_video)], stdin=subprocess.PIPE)
    sub = int(c.get("substeps", 6))
    limit = float(c.get("max_seconds", 120)) * 1.6
    frames, t, winner = 0, 0.0, None
    try:
        while True:
            for s in sides:
                s.tick(1 / fps, sub)
            t += 1 / fps
            winner = winner_of(sides)
            if winner is not None:
                for s in sides:                                 # tout s'arrête : la course est finie
                    s.drop = None
                break
            proc.stdin.write(painter.frame().tobytes())
            frames += 1
            if t > limit:
                winner = max(range(2), key=lambda i: progress(sides[i].sim))
                log.warning("fusion race : personne n'a fini, %s gagne aux points", names[winner])
                break
        race_s = t
        for f in range(int(fps * 1.3)):                         # le gagnant s'illumine, le perdant devient gris
            for s in sides:
                s.sim.t += 1 / fps
            proc.stdin.write(painter.frame(winner, f / fps).tobytes())
        frames += int(fps * 1.3)
        fin = int(fps * float(c.get("final_seconds", 3)))
        for f in range(fin):
            proc.stdin.write(painter.final(winner, f / fps, race_s).tobytes())
        frames += fin
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError("ffmpeg a échoué pendant l'encodage de la vidéo")
    finally:
        if proc.poll() is None:
            proc.kill()
    duration = frames / fps
    import numpy as np
    audio = None
    for s, ch, snd in zip(sides, chains, sounds[:2]):
        ev = [(e, tier) for e, tier in s.sim.events if e <= race_s + 0.05]
        a = fusion.mix_events(ev, duration, len(ch), snd, fat=fat)
        audio = a if audio is None else audio[:len(a)] + a[:len(audio)]
    audio = np.tanh(audio * 0.9) / math.tanh(0.9)
    wav = out.with_suffix(".wav")
    fusion.write_wav(wav, audio)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(tmp_video), "-i", str(wav), "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], check=True)
    tmp_video.unlink(missing_ok=True)
    wav.unlink(missing_ok=True)
    meta = {"title": title, "kind": "race", "seed": seed, "seconds": round(duration, 1), "race_seconds": round(race_s, 1),
            "names": names, "winner": names[winner], "tiers": [[t["name"] for t in ch] for ch in chains],
            "reached": [chains[i][sides[i].sim.best]["name"] for i in range(2)], "created_at": db.now()}
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    _brand_video(out)
    log.info("fusion race : %s gagne en %.0f s → %s", names[winner], race_s, out.name)
    return out


def listing() -> list[dict]:
    items = []
    for p in sorted(fusion.out_dir().glob("race_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        j = p.with_suffix(".json")
        meta = json.loads(j.read_text(encoding="utf-8")) if j.exists() else {}
        items.append({"file": p.name, **meta})
    return items


def _brand_video(out):
    """Filigrane anti-vol sur les NOUVELLES vidéos (depuis le 02/11 ; config `slides.render.video_watermark`)."""
    from . import render as _r
    if _r.rcfg().get("video_watermark", True):
        try:
            _r.stamp_video(out)
        except Exception as e:  # pas de badge, ffmpeg… : la vidéo reste sans filigrane
            log.info("filigrane vidéo : %s", e)
