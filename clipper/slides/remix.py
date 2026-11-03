"""Mini-éditeur : ajoute une musique sous une vidéo générée (Battle, Fusion, Fusion Race, Domain War),
en gardant les bruitages. Pour Instagram / YouTube Shorts (TikTok permet d'ajouter un son dans l'appli).

Musiques : library/_music/ (mp3, wav…). Sur YouTube, seulement des musiques libres de droits
(YouTube Audio Library…), sinon Content ID réclame la vidéo.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from ..util import ffprobe, log, require_bin
from . import battle, fusion, library

AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"}


def music_dir() -> Path:
    d = library.root() / "_music"
    d.mkdir(parents=True, exist_ok=True)
    return d


def musics() -> list[dict]:
    out = []
    for p in sorted(music_dir().iterdir(), key=lambda p: p.name.lower()):
        if p.is_file() and p.suffix.lower() in AUDIO_EXT:
            try:
                dur = float(ffprobe(p)["format"]["duration"])
            except Exception:
                dur = 0.0
            out.append({"name": p.name, "seconds": round(dur, 1)})
    return out


def music_path(name: str) -> Path | None:
    p = music_dir() / Path(name or "").name
    return p if p.is_file() and p.suffix.lower() in AUDIO_EXT else None


def videos() -> list[dict]:
    """Toutes les vidéos générées, les plus récentes d'abord : {kind, file, src (dossier media), title, music?}."""
    items = []
    for d, media in ((battle.out_dir(), "battle"), (fusion.out_dir(), "fusion")):
        for p in d.glob("*.mp4"):
            if p.name.endswith((".video.mp4", ".tmp.mp4")):
                continue
            meta = {}
            j = p.with_suffix(".json")
            if j.exists():
                try:
                    meta = json.loads(j.read_text(encoding="utf-8"))
                except ValueError:
                    pass
            kind = meta.get("kind") or p.stem.split("_")[0]
            items.append({"file": p.name, "media": media, "kind": kind, "mtime": p.stat().st_mtime,
                          "title": meta.get("title") or p.stem, "music": meta.get("music"),
                          "seconds": meta.get("seconds")})
    return sorted(items, key=lambda x: x["mtime"], reverse=True)


def video_path(media: str, name: str) -> Path | None:
    base = {"battle": battle.out_dir(), "fusion": fusion.out_dir()}.get(media)
    if not base:
        return None
    p = base / Path(name).name
    return p if p.is_file() and p.suffix == ".mp4" else None


def add_music(video: Path, music: Path, start: float = 0.0, music_volume: float = 0.35, sfx_volume: float = 1.0,
              fade_out: float = 2.0) -> Path:
    """Nouvelle vidéo « <nom>_music.mp4 » : la musique (bouclée si trop courte, fondu au début et à la fin)
    mélangée sous le son d'origine. L'image n'est pas réencodée (rapide)."""
    ffmpeg = require_bin("ffmpeg")
    if video.stem.endswith("_music"):                     # changer de musique : on repart de la vidéo d'origine
        orig = video.with_name(video.stem[:-6] + ".mp4")
        if orig.exists():
            video = orig
    info = ffprobe(video)
    dur = float(info["format"]["duration"])
    has_audio = any(s.get("codec_type") == "audio" for s in info.get("streams", []))
    stem = video.stem[:-6] if video.stem.endswith("_music") else video.stem
    out = video.with_name(f"{stem}_music.mp4")
    tmp = video.with_name(f"{stem}_music.tmp.mp4")
    fo = max(0.0, min(fade_out, dur / 3))
    m = (f"[1:a]aresample=44100,volume={music_volume:.3f},afade=t=in:st=0:d=0.8,"
         f"afade=t=out:st={max(0.0, dur - fo):.3f}:d={fo:.3f}[m]")
    if has_audio:
        graph = (f"{m};[0:a]aresample=44100,volume={sfx_volume:.3f}[o];"
                 f"[o][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]")
    else:
        graph = f"{m};[m]anull[a]"
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(video), "-stream_loop", "-1", "-ss", f"{max(0.0, start):.3f}",
           "-i", str(music), "-filter_complex", graph, "-map", "0:v", "-map", "[a]", "-t", f"{dur:.3f}",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0 or not tmp.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError("ffmpeg : " + (r.stderr or b"").decode(errors="ignore")[-400:])
    os.replace(tmp, out)
    src_meta = video.with_name(stem + ".json")                  # la vidéo garde ses infos (gagnant…) + la musique
    meta = {}
    if src_meta.exists():
        try:
            meta = json.loads(src_meta.read_text(encoding="utf-8"))
        except ValueError:
            pass
    meta.update(music=music.name, music_start=start, music_volume=music_volume, sfx_volume=sfx_volume)
    out.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    log.info("musique ajoutée : %s + %s → %s", video.name, music.name, out.name)
    return out


def save_upload(filename: str, data: bytes) -> Path:
    name = Path(filename or "musique.mp3").name
    if Path(name).suffix.lower() not in AUDIO_EXT:
        raise ValueError("Format non pris en charge (mp3, wav, ogg, m4a, aac, flac)")
    p = music_dir() / name
    p.write_bytes(data)
    return p


def preview_music(music: Path, start: float, seconds: float = 12.0) -> Path:
    """Extrait de la musique à partir de `start` (pour écouter avant de choisir)."""
    out = fusion.out_dir() / "_music_preview.mp3"
    subprocess.run([require_bin("ffmpeg"), "-y", "-loglevel", "error", "-ss", f"{max(0.0, start):.2f}", "-t",
                    f"{seconds:.1f}", "-i", str(music), "-b:a", "160k", str(out)], check=True)
    return out


def archive(media: str, name: str) -> bool:
    """« Retirer » une vidéo déjà postée : déplacée (avec son .json) dans data/archive/<media>/, plus affichée
    nulle part, mais récupérable."""
    from .. import config
    p = video_path(media, name)
    if not p:
        return False
    dest = config.data_dir() / "archive" / media
    dest.mkdir(parents=True, exist_ok=True)
    for f in (p, p.with_suffix(".json")):
        if f.exists():
            os.replace(f, dest / f.name)
    log.info("vidéo retirée : %s → data/archive/%s/", p.name, media)
    return True
