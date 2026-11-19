"""Analyse d'une vidéo plan par plan (19/11, demandé par l'utilisateur : « un outil qui regarde une vidéo et analyse
chaque scène »). Sert à décortiquer une vidéo qui marche (référence) ou à vérifier une des nôtres.

clipper analyze <fichier ou URL> [--out DOSSIER] [--seuil 0.3] [--lang en] [--no-transcript]

Sortie dans data/analyze/<nom>/ (ou --out) :
  rapport.md      résumé lisible : durée, nb de plans, rythme, 1re seconde, couleurs, mouvement, son, texte dit par plan
  scenes.json     tout en données (début, fin, durée, mouvement, luminosité, palette, mots dits, images)
  timeline.png    bande : une vignette par plan (largeur = durée) + courbe de mouvement + courbe de volume
  planche_NN.png  8 plans par planche : début / milieu / fin de chaque plan + chiffres
  frame0.png      l'image 0 en pleine taille (la couverture et l'accroche)
  plans/          images clés de chaque plan (360 px)
Ensuite Claude lit les planches (vision) et écrit l'analyse DA / montage / script.
Transcription Deepgram si DEEPGRAM_API_KEY est dans .env (sinon ignorée).
"""
from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import config
from .util import log, require_bin

SAMPLE_FPS = 6
SMALL = 160                       # largeur des images d'analyse


def _font(sz, bold=False):
    for p in ("/usr/share/fonts/truetype/google-fonts/Poppins-" + ("Bold" if bold else "Regular") + ".ttf",
              "C:/Windows/Fonts/" + ("segoeuib.ttf" if bold else "segoeui.ttf"),
              "/usr/share/fonts/truetype/dejavu/DejaVuSans" + ("-Bold" if bold else "") + ".ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def probe(path: Path) -> dict:
    out = subprocess.run([require_bin("ffprobe"), "-v", "error", "-show_entries",
                          "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    v = next((s for s in j["streams"] if s.get("codec_type") == "video" and s.get("width")), {})
    num, den = (v.get("r_frame_rate") or "30/1").split("/")
    return {"duration": float(j["format"]["duration"]), "width": int(v.get("width", 0)),
            "height": int(v.get("height", 0)), "fps": float(num) / max(1.0, float(den)),
            "audio": any(s.get("codec_type") == "audio" for s in j["streams"])}


def download(url: str, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    subprocess.run([require_bin("yt-dlp"), "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
                    "-o", str(dest / "source.%(ext)s"), url], check=True)
    return next(dest.glob("source.*"))


def cuts(path: Path, thr: float) -> list[float]:
    """Changements de plan (filtre scene de ffmpeg) ; deux coupes à moins de 0,25 s = une seule (flashs)."""
    r = subprocess.run([require_bin("ffmpeg"), "-hide_banner", "-i", str(path), "-vf",
                        f"select='gt(scene,{thr})',showinfo", "-map", "0:v:0", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    ts = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    out = []
    for t in ts:
        if not out or t - out[-1] > 0.25:
            out.append(t)
    return out


def soft_cuts(arr, thr=40.0, min_len=0.5):
    """Changements progressifs (zoom, fondu, morph) que le filtre scene ne voit pas : on compare chaque image à la
    1re image du plan en cours ; trop différente → nouveau plan."""
    sm = arr[:, ::4, ::4].astype(np.float32)
    anchor, start, out = sm[0], 0, []
    for i in range(1, len(sm)):
        if np.abs(sm[i] - anchor).mean() > thr and (i - start) / SAMPLE_FPS > min_len:
            out.append(i / SAMPLE_FPS)
            anchor, start = sm[i], i
    return out


def merge_cuts(ts, gap=0.75):
    """Une transition donne souvent 2 coupes rapprochées : on garde la dernière (image stabilisée)."""
    out = []
    for t in sorted(ts):
        if out and t - out[-1] < gap:
            out[-1] = t
        else:
            out.append(t)
    return out


def samples(path: Path, info: dict):
    """Toutes les images à SAMPLE_FPS, en petit (analyse mouvement / couleur)."""
    h = int(SMALL * info["height"] / max(1, info["width"])) // 2 * 2
    p = subprocess.run([require_bin("ffmpeg"), "-v", "error", "-i", str(path), "-map", "0:v:0", "-vf",
                        f"fps={SAMPLE_FPS},scale={SMALL}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True).stdout
    arr = np.frombuffer(p, np.uint8).reshape(-1, h, SMALL, 3)
    return arr


def loudness(path: Path, dur: float, step=0.25):
    if not probe(path)["audio"]:
        return []
    p = subprocess.run([require_bin("ffmpeg"), "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", "8000",
                        "-f", "f32le", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(p, np.float32)
    n = int(8000 * step)
    out = []
    for i in range(0, len(a), n):
        rms = float(np.sqrt(np.mean(a[i:i + n] ** 2) + 1e-12))
        out.append(round(20 * math.log10(rms + 1e-9), 1))
    return out


def grab(path: Path, t: float, out: Path, width=360):
    for tt in (t, t - 0.1, t - 0.3, 0.0):                # près de la fin, ffmpeg peut ne rien sortir : on recule
        subprocess.run([require_bin("ffmpeg"), "-v", "error", "-y", "-ss", f"{max(0, tt):.3f}", "-i", str(path),
                        "-map", "0:v:0", "-frames:v", "1", "-vf", f"scale={width}:-2", str(out)], check=True)
        if out.exists() and out.stat().st_size > 0:
            return out
    raise RuntimeError(f"image introuvable à {t:.2f} s")


def palette(img: Image.Image, n=4):
    q = img.convert("RGB").resize((80, int(80 * img.height / img.width))).quantize(n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: n * 3]
    counts = sorted(q.getcolors(), reverse=True)
    return ["#%02x%02x%02x" % tuple(pal[i * 3:i * 3 + 3]) for c, i in counts]


def transcript(path: Path, lang: str):
    try:
        key = config.secret("DEEPGRAM_API_KEY", required=False)
    except Exception:
        key = ""
    if not key:
        return None
    import httpx
    aud = path.with_suffix(".analyse.ogg")
    subprocess.run([require_bin("ffmpeg"), "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                    "-c:a", "libopus", "-b:a", "32k", str(aud)], check=True)
    with open(aud, "rb") as f:
        r = httpx.post("https://api.deepgram.com/v1/listen", params={"model": "nova-3", "language": lang,
                       "punctuate": "true", "smart_format": "true"},
                       headers={"Authorization": f"Token {key}", "Content-Type": "audio/ogg"}, content=f, timeout=600)
    aud.unlink(missing_ok=True)
    if r.status_code >= 400:
        log.warning("Deepgram %s : transcription ignorée", r.status_code)
        return None
    alt = r.json()["results"]["channels"][0]["alternatives"][0]
    return [{"w": w.get("punctuated_word") or w["word"], "s": w["start"], "e": w["end"]} for w in alt.get("words", [])]


def analyze(src: str, out: Path | None = None, thr: float = 0.3, lang: str = "en", do_transcript: bool = True) -> Path:
    if re.match(r"https?://", src):
        name = re.sub(r"\W+", "_", src.split("/")[-1])[:40] or "video"
        out = Path(out or Path("data/analyze") / name)
        path = download(src, out)
    else:
        path = Path(src)
        out = Path(out or Path("data/analyze") / re.sub(r"\W+", "_", path.stem)[:40])
    out.mkdir(parents=True, exist_ok=True)
    (out / "plans").mkdir(exist_ok=True)
    info = probe(path)
    dur = info["duration"]
    arr = samples(path, info)
    cut = merge_cuts(cuts(path, thr) + soft_cuts(arr))
    bounds = [0.0] + [c for c in cut if 0.15 < c < dur - 0.15] + [dur]
    ts = np.arange(len(arr)) / SAMPLE_FPS
    diff = np.r_[0, np.abs(np.diff(arr.astype(np.int16), axis=0)).mean(axis=(1, 2, 3))]
    lum = arr.mean(axis=(1, 2, 3))
    flashes = [round(float(t), 2) for t, l, l0 in zip(ts[1:], lum[1:], lum[:-1]) if l - l0 > 60]
    loud = loudness(path, dur)
    words = transcript(path, lang) if do_transcript else None

    scenes = []
    for i, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        sel = (ts >= a) & (ts < b)
        mot = float(diff[sel][1:].mean()) if sel.sum() > 1 else 0.0
        imgs = []
        for tag, t in (("debut", a + 0.05), ("milieu", (a + b) / 2), ("fin", max(a + 0.05, b - 0.08))):
            imgs.append(str(grab(path, t, out / "plans" / f"{i + 1:02d}_{tag}.jpg").relative_to(out)))
        mid = Image.open(out / imgs[1])
        sc = {"n": i + 1, "debut": round(a, 2), "fin": round(b, 2), "duree": round(b - a, 2),
              "mouvement": round(mot, 1), "luminosite": round(float(lum[sel].mean()) if sel.any() else 0, 1),
              "palette": palette(mid), "images": imgs}
        if words is not None:
            sc["dit"] = " ".join(w["w"] for w in words if a <= w["s"] < b)
        scenes.append(sc)

    grab(path, 0.0, out / "frame0.png", width=info["width"] or 1080)
    durs = [s["duree"] for s in scenes]
    data = {"source": str(src), "duree": round(dur, 2), "taille": f"{info['width']}x{info['height']}",
            "fps": round(info["fps"], 2), "plans": len(scenes), "duree_moyenne_plan": round(float(np.mean(durs)), 2),
            "plans_par_10s": round(len(scenes) / dur * 10, 2), "flashs": flashes, "volume_db_par_0_25s": loud,
            "mouvement_par_image": [round(float(x), 1) for x in diff], "scenes": scenes,
            "transcription": words}
    (out / "scenes.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    _timeline(out, data, dur)
    _sheets(out, scenes)
    _report(out, data)
    log.info("Analyse : %s", out)
    return out


def _timeline(out: Path, data: dict, dur: float):
    Wt, th = 2000, 260
    im = Image.new("RGB", (Wt, th + 260), (18, 20, 28))
    d = ImageDraw.Draw(im)
    f = _font(20)
    for s in data["scenes"]:
        x0, x1 = int(s["debut"] / dur * Wt), int(s["fin"] / dur * Wt)
        if x1 - x0 < 2:
            continue
        x = x0                                           # début / milieu / fin côte à côte jusqu'à remplir la case
        for rel in (s["images"] * 3):
            if x >= x1:
                break
            t = Image.open(out / rel).convert("RGB")
            t = t.resize((max(1, int(t.width * th / t.height)), th))
            im.paste(t.crop((0, 0, min(t.width, x1 - x), th)), (x, 0))
            x += t.width
        d.line((x0, 0, x0, th + 250), fill=(255, 200, 70), width=2)
        d.text((x0 + 4, th + 4), str(s["n"]), font=f, fill=(255, 200, 70))
    mv = data["mouvement_par_image"]
    if mv:
        mx = max(mv) or 1
        pts = [(i / len(mv) * Wt, th + 130 - 100 * v / mx) for i, v in enumerate(mv)]
        d.line(pts, fill=(110, 200, 255), width=2)
        d.text((6, th + 30), "mouvement", font=f, fill=(110, 200, 255))
    lo = data["volume_db_par_0_25s"]
    if lo:
        pts = [(i / len(lo) * Wt, th + 250 - 100 * (max(-60, v) + 60) / 60) for i, v in enumerate(lo)]
        d.line(pts, fill=(255, 120, 120), width=2)
        d.text((6, th + 150), "volume", font=f, fill=(255, 120, 120))
    for k in range(int(dur) + 1):                       # graduations en secondes
        x = k / dur * Wt
        d.line((x, th + 240, x, th + 250), fill=(120, 120, 130))
        if k % 5 == 0:
            d.text((x + 2, th + 222), f"{k}s", font=_font(16), fill=(160, 160, 170))
    im.save(out / "timeline.png")


def _sheets(out: Path, scenes: list):
    per = 8
    tw = 200
    for p in range(0, len(scenes), per):
        chunk = scenes[p:p + per]
        th = int(tw * 16 / 9)
        im = Image.new("RGB", (3 * (tw + 8) + 330, len(chunk) * (th + 10) + 10), (18, 20, 28))
        d = ImageDraw.Draw(im)
        for r, s in enumerate(chunk):
            y = 10 + r * (th + 10)
            for c, rel in enumerate(s["images"]):
                t = Image.open(out / rel).convert("RGB")
                t.thumbnail((tw, th))
                im.paste(t, (8 + c * (tw + 8), y))
            x = 3 * (tw + 8) + 14
            d.text((x, y + 4), f"PLAN {s['n']}", font=_font(30, True), fill=(255, 200, 70))
            d.text((x, y + 46), f"{s['debut']:.2f} → {s['fin']:.2f} s  ({s['duree']:.2f} s)", font=_font(20), fill=(230, 230, 235))
            d.text((x, y + 76), f"mouvement {s['mouvement']}  ·  lumière {s['luminosite']}", font=_font(18), fill=(170, 170, 180))
            for k, col in enumerate(s["palette"]):
                d.rectangle((x + k * 42, y + 108, x + k * 42 + 36, y + 140), fill=col)
            if s.get("dit"):
                txt, line, yy = s["dit"], "", y + 156
                for w in txt.split():
                    if len(line) + len(w) > 30:
                        d.text((x, yy), line, font=_font(17), fill=(200, 200, 210))
                        yy += 22
                        line = ""
                    line += w + " "
                    if yy > y + th - 30:
                        break
                d.text((x, yy), line, font=_font(17), fill=(200, 200, 210))
        im.save(out / f"planche_{p // per + 1:02d}.png")


def _report(out: Path, data: dict):
    sc = data["scenes"]
    longest = max(sc, key=lambda s: s["duree"])
    lines = [f"# Analyse : {Path(data['source']).name}", "",
             f"- Durée : {data['duree']} s · {data['taille']} · {data['fps']} i/s",
             f"- Plans : {data['plans']} · durée moyenne {data['duree_moyenne_plan']} s · {data['plans_par_10s']} plans / 10 s",
             f"- Plan le plus long : n° {longest['n']} ({longest['duree']} s, à {longest['debut']} s)",
             f"- Flashs blancs : {', '.join(map(str, data['flashs'])) or 'aucun'}",
             f"- 1er plan : {sc[0]['duree']} s, mouvement {sc[0]['mouvement']} (image 0 : frame0.png)", "",
             "| Plan | Début | Durée | Mouvement | Palette | Dit |", "|---|---|---|---|---|---|"]
    for s in sc:
        lines.append(f"| {s['n']} | {s['debut']} | {s['duree']} | {s['mouvement']} | {' '.join(s['palette'][:3])} | "
                     f"{(s.get('dit') or '').replace('|', '/')[:90]} |")
    lines += ["", "Planches : " + ", ".join(sorted(p.name for p in out.glob("planche_*.png"))) + " · timeline.png"]
    (out / "rapport.md").write_text("\n".join(lines) + "\n")
