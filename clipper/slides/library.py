"""Bibliothèque d'images : dossiers par anime/personnage + captures extraites d'épisodes ou de trailers.

Arborescence (à la racine du projet par défaut) :
  library/
    Jujutsu Kaisen/
      Gojo Satoru/*.jpg        ← images rangées par personnage (le nom du dossier sert au choix)
      Sukuna/*.png
      *.jpg                    ← images diverses de l'anime
      _frames/<source>/*.jpg   ← captures extraites automatiquement (non étiquetées)
    _music/*.mp3               ← musiques libres de droits pour les Shorts
"""
from __future__ import annotations

import random
import re
import shutil
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .. import config, db, llm
from ..util import log, require_bin, run
from . import prompts

EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def cfg() -> dict:
    return config.get()["slides"]


def root() -> Path:
    p = Path(cfg().get("library", "./library"))
    if not p.is_absolute():
        p = config.ROOT / p
    p.mkdir(parents=True, exist_ok=True)
    for sub in ("_music", "_sounds", "_fusion"):         # musiques, bruitages (Fusion), chaînes de niveaux (Fusion)
        (p / sub).mkdir(exist_ok=True)
    return p


def norm(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def safe_dirname(s: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "", s).strip().rstrip(".") or "Unknown"


# --- analyse d'image --------------------------------------------------------------

def measure(path: Path) -> dict | None:
    """Taille, netteté (variance du laplacien) et empreinte (aHash 8×8) ; None si illisible."""
    import cv2
    import numpy as np

    data = np.fromfile(str(path), dtype=np.uint8)          # fromfile : chemins Unicode sous Windows
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        return None
    h, w = img.shape[:2]
    small = cv2.resize(img, (640, max(1, round(640 * h / w))))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    tiny = cv2.resize(gray, (8, 8), interpolation=cv2.INTER_AREA)
    bits = (tiny > tiny.mean()).flatten()
    ahash = "".join("1" if b else "0" for b in bits)
    return {"width": w, "height": h, "sharp": round(sharp, 1), "ahash": f"{int(ahash, 2):016x}",
            "mean": float(gray.mean())}


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


# --- index ------------------------------------------------------------------------

def scan() -> dict:
    """Synchronise la table images avec le disque. Rend {added, removed, total}."""
    r = root()
    min_side = int(cfg().get("min_image_side", 480))
    known = {row["path"]: row["id"] for row in db.query("SELECT id, path FROM images")}
    seen, added = set(), 0
    for p in r.rglob("*"):
        if p.suffix.lower() not in EXTS or not p.is_file():
            continue
        rel = p.relative_to(r).parts
        if len(rel) < 2 or rel[0].startswith("_") or rel[0].lower() in ("logos", "logo"):   # _originals aussi
            continue                                   # _music, _brand, logos : jamais des images de slides
        sp = str(p)
        seen.add(sp)
        wall = rel[0].lower() in WALL_DIRS                 # library/wallpaper/<Anime>/[<Perso>/]image
        if wall and len(rel) < 3:
            continue
        if wall:
            anime, character, origin = rel[1], (rel[2] if len(rel) >= 4 else None), "wallpaper"
        else:
            frames = "_frames" in rel
            anime, origin = rel[0], "frames" if frames else "library"
            character = None if frames or len(rel) < 3 or rel[1].startswith("_") else rel[1]
        if sp in known:
            if wall:                                       # rangée avant que le dossier wallpaper soit reconnu
                db.execute("UPDATE images SET anime=?, character=?, origin='wallpaper' WHERE id=? AND origin!='wallpaper'",
                           (anime, character, known[sp]))
            continue
        m = measure(p)
        if not m or min(m["width"], m["height"]) < min_side:
            continue
        db.insert("images", path=sp, anime=anime, character=character, origin=origin,
                  width=m["width"], height=m["height"], sharp=m["sharp"], ahash=m["ahash"])
        added += 1
    removed = [i for p, i in known.items() if p not in seen]
    for i in removed:
        db.execute("DELETE FROM images WHERE id=?", (i,))
    total = db.one("SELECT COUNT(*) AS n FROM images")["n"]
    log.info("Bibliothèque : %d ajoutée(s), %d retirée(s), %d au total", added, len(removed), total)
    return {"added": added, "removed": len(removed), "total": total}


WALL_DIRS = ("wallpaper", "wallpapers")


def animes_with_images() -> list[str]:
    return sorted({norm(r["anime"]) for r in db.query("SELECT DISTINCT anime FROM images")})


def characters_for(anime: str) -> list[str]:
    """Personnages qui ont un dossier d'images pour cet anime."""
    a = norm(anime)
    return sorted({r["character"] for r in db.query("SELECT anime, character FROM images WHERE character IS NOT NULL")
                   if norm(r["anime"]) == a})


def stats() -> list[dict]:
    rows = db.query("SELECT anime, origin, character, COUNT(*) AS n, SUM(origin='frames' AND character IS NULL "
                    "AND tagged=0) AS untagged FROM images GROUP BY anime, origin, character")
    out: dict[str, dict] = {}
    for r in rows:
        a = out.setdefault(r["anime"], {"anime": r["anime"], "library": 0, "frames": 0, "wallpaper": 0,
                                        "characters": {}, "untagged": 0})
        a["untagged"] += r["untagged"] or 0
        a[r["origin"]] += r["n"]
        if r["character"] and r["origin"] != "wallpaper":
            a["characters"][r["character"]] = a["characters"].get(r["character"], 0) + r["n"]
    return sorted(out.values(), key=lambda a: a["anime"].lower())


# --- sources : épisodes / trailers → captures ----------------------------------------

def add_source(url: str, anime: str) -> list[str]:
    from .. import ingest

    anime = anime.strip()
    if not anime:
        raise ValueError("Indique l'anime de cette source")
    ids = []
    for v in ingest.resolve(url):
        if not db.get("sources", v["id"]):
            t = db.now()
            db.execute("INSERT INTO sources (id,url,anime,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
                       (v["id"], v["url"], anime, v.get("title"), "new", t, t))
            ids.append(v["id"])
    return ids


def process_source(source_id: str) -> int:
    """Télécharge (1080p max), extrait une image par changement de plan, filtre floues/noires/doublons."""
    import yt_dlp

    from .. import ingest

    s = db.get("sources", source_id)
    if s["status"] == "done":
        return s["n_frames"] or 0
    fc = cfg()["frames"]
    out_dir = root() / safe_dirname(s["anime"]) / "_frames" / source_id
    out_dir.mkdir(parents=True, exist_ok=True)
    db.update("sources", source_id, status="downloading", error=None)
    try:
        opts = ingest._ydl_opts({
            "format": "bv*[height<=1080]/b[height<=1080]/b",   # la vidéo seule suffit
            "outtmpl": str(out_dir / "source.%(ext)s"), "retries": 10, "continuedl": True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(s["url"], download=True)
        src = next((p for p in out_dir.glob("source.*") if p.suffix not in {".part", ".ytdl"}), None)
        if src is None:
            raise RuntimeError("yt-dlp n'a produit aucun fichier")
        db.update("sources", source_id, title=info.get("title"), status="extracting")
        raw = out_dir / "raw"
        raw.mkdir(exist_ok=True)
        thr = float(fc.get("scene_threshold", 0.3))
        run([require_bin("ffmpeg"), "-y", "-v", "error", "-i", str(src),
             "-vf", f"select='gt(scene,{thr})',scale='min(1920,iw)':-2", "-vsync", "vfr", "-q:v", "2",
             "-frames:v", str(int(fc.get("max_per_source", 300)) * 4), str(raw / "f_%05d.jpg")])
        kept = filter_frames(sorted(raw.glob("*.jpg")), out_dir, int(fc.get("max_per_source", 300)),
                             float(fc.get("min_sharpness", 60)))
        shutil.rmtree(raw, ignore_errors=True)
        if not fc.get("keep_source_video", False):
            src.unlink(missing_ok=True)
        db.update("sources", source_id, status="done", n_frames=kept)
        scan()
        log.info("source %s : %d images gardées", source_id, kept)
        if fc.get("auto_tag", True):
            tag_frames(s["anime"])
        return kept
    except Exception as e:
        db.update("sources", source_id, status="failed", error=str(e)[:2000])
        raise


def filter_frames(paths: list[Path], out_dir: Path, max_n: int, min_sharp: float) -> int:
    """Garde les captures nettes, pas trop sombres, sans quasi-doublons ; les plus nettes d'abord."""
    measured = []
    for p in paths:
        m = measure(p)
        if m and m["sharp"] >= min_sharp and m["mean"] > 25:
            measured.append((p, m))
    measured.sort(key=lambda x: -x[1]["sharp"])
    kept: list[tuple[Path, dict]] = []
    for p, m in measured:
        if len(kept) >= max_n:
            break
        if all(hamming(m["ahash"], k[1]["ahash"]) > 6 for k in kept):
            kept.append((p, m))
    for i, (p, _) in enumerate(sorted(kept, key=lambda x: x[0].name)):
        shutil.move(str(p), out_dir / f"{i:04d}.jpg")
    return len(kept)


# --- choix des images ----------------------------------------------------------------

def candidates(anime: str, character: str, exclude: set[str], wallpaper: bool = False) -> tuple[list[dict], list[dict]]:
    """(images étiquetées avec ce personnage, autres images du même anime), hors `exclude`.
    Les images de library/wallpaper/ ne servent qu'aux posts wallpaper (et ceux-ci n'utilisent qu'elles s'il y en a)."""
    a = norm(anime)
    every = [r for r in db.query("SELECT * FROM images") if norm(r["anime"]) == a and Path(r["path"]).exists()]
    has_walls = any(r["origin"] == "wallpaper" for r in every)
    rows = [r for r in every if r["path"] not in exclude]
    if wallpaper and has_walls:
        rows = [r for r in rows if r["origin"] == "wallpaper"]
    elif not wallpaper:
        rows = [r for r in rows if r["origin"] != "wallpaper"]
    c = norm(character)
    labeled = [r for r in rows if c and r["character"] and (norm(r["character"]) in c or c in norm(r["character"]))]
    others = [r for r in rows if r not in labeled]
    return labeled, others


def _freshness_key(r: dict) -> tuple:
    """Jamais utilisée d'abord, puis la plus anciennement utilisée ; à égalité, la plus nette."""
    return (r["use_count"] > 0, r["last_used_at"] or "", -(r["sharp"] or 0))


def shortlist(labeled: list[dict], others: list[dict], n: int, seed: int = 0) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=int(cfg().get("avoid_reuse_days", 30)))).isoformat()
    rnd = random.Random(seed)

    def fresh_first(rows: list[dict]) -> list[dict]:
        fresh = [r for r in rows if not r["last_used_at"] or r["last_used_at"] < cutoff]
        stale = [r for r in rows if r not in fresh]
        rnd.shuffle(fresh)                      # variété d'un slideshow à l'autre
        fresh.sort(key=lambda r: r["use_count"] > 0)
        return fresh + sorted(stale, key=_freshness_key)

    lab, oth = fresh_first(labeled), fresh_first(others)
    if len(lab) >= 4:              # assez d'images rangées pour ce personnage : on s'y tient
        return lab[:n]
    k_lab = min(len(lab), max(n // 2, n - len(oth)))
    picked = lab[:k_lab] + oth[: n - k_lab]
    return picked[:n]


def pick(slide: dict, exclude: set[str], seed: int = 0) -> dict:
    """Choisit l'image d'une slide. Rend {image_path, alts, character_match}."""
    wall = bool(slide.get("wallpaper"))
    labeled, others = candidates(slide["anime"], "" if wall else slide["character"], exclude, wallpaper=wall)
    pool = shortlist(labeled, others, int(cfg().get("vision_candidates", 12)), seed)
    if wall and not pool:                              # plus de wallpaper neuf (couverture, fin) : on en réutilise un
        pool = shortlist(*candidates(slide["anime"], "", set(), wallpaper=True), 12, seed)
    if not pool:
        return {"image_path": None, "alts": [], "character_match": False}
    if wall:                                           # wallpaper : la plus fraîche, pas besoin de Claude
        return {"image_path": pool[0]["path"], "alts": [r["path"] for r in pool[1:5]], "character_match": True}
    if len(pool) == 1:
        return {"image_path": pool[0]["path"], "alts": [], "character_match": bool(labeled)}
    content: list = [{"type": "text", "text": (
        f"Slide text: {slide['text']}\nAnime: {slide['anime']}\n"
        f"Character to show: {slide['character'] or '(any)'}\nScene: {slide['scene'] or '(any)'}\n"
        f"Choose among these {len(pool)} images (indices 0-{len(pool) - 1}).")}]
    for i, r in enumerate(pool):
        content.append({"type": "text", "text": f"Image {i}:"})
        content.append(llm.image_block(r["path"]))
    try:
        out = llm.structured(model=cfg()["model"], system=prompts.PICK_SYSTEM, user=content,
                             tool_name="pick_image", tool_desc="Store the chosen image.",
                             schema=prompts.PICK_SCHEMA, max_tokens=300)
        idx = int(out.get("index", 0))
        order = [i for i in [idx, *out.get("ranking", [])] if 0 <= i < len(pool)]
        match = bool(out.get("character_match", False))
    except Exception as e:  # la vision est un plus : sans elle on prend la plus nette
        log.warning("choix par vision impossible (%s) : image la plus nette", e)
        order, match = [max(range(len(pool)), key=lambda i: pool[i]["sharp"] or 0)], bool(labeled)
    order = list(dict.fromkeys(order + list(range(len(pool)))))
    return {"image_path": pool[order[0]]["path"], "alts": [pool[i]["path"] for i in order[1:]],
            "character_match": match}


def choices(anime: str, character: str, limit: int = 60, wallpaper: bool = False) -> list[dict]:
    """Images proposées pour un choix manuel : celles du perso (sinon tout l'anime), les moins utilisées d'abord."""
    labeled, others = candidates(anime, "" if wallpaper else character, set(), wallpaper=wallpaper)
    rows = labeled or others
    rows.sort(key=lambda r: (r["use_count"] or 0, r["last_used_at"] or "", -(r["sharp"] or 0)))
    return rows[:limit]


def thumb(image_id: int, side: int = 360) -> Path | None:
    """Miniature JPEG en cache (data/thumbs) : certaines sources font 20 Mo."""
    r = db.get("images", image_id)
    if not r or not Path(r["path"]).exists():
        return None
    d = config.data_dir() / "thumbs"
    d.mkdir(parents=True, exist_ok=True)
    out = d / f"{image_id}_{side}.jpg"
    src = Path(r["path"])
    if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
        from PIL import Image

        with Image.open(src) as im:
            im = im.convert("RGB")
            im.thumbnail((side, side * 2))
            im.save(out, "JPEG", quality=82)
    return out


def mark_used(paths: list[str]) -> None:
    t = db.now()
    for p in paths:
        db.execute("UPDATE images SET use_count=use_count+1, last_used_at=? WHERE path=?", (t, p))


def music_files() -> list[Path]:
    d = Path(cfg()["video"].get("music_dir") or "")
    if not str(d):
        return []
    if not d.is_absolute():
        d = config.ROOT / d
    return sorted(p for p in d.glob("*") if p.suffix.lower() in {".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac"})


# --- tri automatique des captures par personnage (Claude vision) -----------------------------

def tag_frames(anime: str, batch: int = 12, limit: int | None = None) -> dict:
    """Range les captures non triées de cet anime dans library/<Anime>/<Perso>/. Rend {moved, kept, seen}."""
    fc = cfg()["frames"]
    min_conf = int(fc.get("tag_min_confidence", 75))
    a = norm(anime)
    rows = [r for r in db.query("SELECT * FROM images WHERE origin='frames' AND character IS NULL AND tagged=0")
            if norm(r["anime"]) == a and Path(r["path"]).exists()]
    rows.sort(key=lambda r: r["path"])
    rows = rows[:limit] if limit else rows
    moved = kept = 0
    for i in range(0, len(rows), batch):
        chunk = rows[i:i + batch]
        known = characters_for(anime)
        content: list = [{"type": "text", "text": f"{len(chunk)} images, indices 0-{len(chunk) - 1}."}]
        for k, r in enumerate(chunk):
            content += [{"type": "text", "text": f"Image {k}:"}, llm.image_block(r["path"], max_side=512)]
        try:
            out = llm.structured(model=cfg()["model"], system=prompts.TAG_SYSTEM.format(
                anime=anime, known=", ".join(known) or "(none yet)"), user=content, tool_name="tag_images",
                tool_desc="Store the character of each image.", schema=prompts.TAG_SCHEMA, max_tokens=1500)
        except Exception as e:
            log.warning("tri des captures interrompu : %s", e)
            break
        by_idx = {int(x["index"]): x for x in out.get("items", []) if "index" in x}
        for k, r in enumerate(chunk):
            x = by_idx.get(k) or {}
            name = " ".join(str(x.get("character", "")).split())
            if name and int(x.get("confidence", 0)) >= min_conf:
                name = next((c for c in known if norm(c) == norm(name)), name)   # orthographe existante
                dest_dir = Path(r["path"]).parents[2] / safe_dirname(name)       # library/<Anime>/<Perso>/
                dest_dir.mkdir(parents=True, exist_ok=True)
                dest = dest_dir / f"{Path(r['path']).parent.name}_{Path(r['path']).name}"
                shutil.move(r["path"], dest)
                db.update("images", r["id"], path=str(dest), character=name, tagged=1)
                moved += 1
            else:
                db.update("images", r["id"], tagged=1)
                kept += 1
    log.info("tri %s : %d rangée(s) par perso, %d en divers", anime, moved, kept)
    return {"moved": moved, "kept": kept, "seen": len(rows)}


def add_uploaded(data: bytes, filename: str, anime: str, character: str = "") -> str:
    """Range une image envoyée depuis la revue dans library/<Anime>/<Perso>/ et l'indexe. Rend son chemin."""
    from io import BytesIO

    from PIL import Image as _Image

    ext = Path(filename or "").suffix.lower()
    if ext not in EXTS:
        raise ValueError("Format accepté : .jpg, .jpeg, .png ou .webp")
    try:
        with _Image.open(BytesIO(data)) as im:
            im.verify()
    except Exception as e:
        raise ValueError("Ce fichier n'est pas une image lisible") from e
    folder = root() / safe_dirname(anime or "Mixed")
    if character:
        folder = folder / safe_dirname(character)
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w-]+", "_", Path(filename).stem)[:40] or "image"
    dest = folder / f"{stem}{ext}"
    k = 1
    while dest.exists():
        dest = folder / f"{stem}_{k}{ext}"
        k += 1
    dest.write_bytes(data)
    try:
        from . import upscale
        upscale.upscale_file(dest)                     # petite image : agrandie par IA si le moteur est installé
    except Exception as e:                             # jamais bloquant
        log.warning("agrandissement ignoré : %s", e)
    m = measure(dest)
    if m and not db.one("SELECT 1 AS x FROM images WHERE path=?", (str(dest),)):
        db.insert("images", path=str(dest), anime=safe_dirname(anime or "Mixed"), character=character or None,
                  origin="library", width=m["width"], height=m["height"], sharp=m["sharp"], ahash=m["ahash"],
                  tagged=1)
    return str(dest)
