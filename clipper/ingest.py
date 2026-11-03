"""Étape 1 : résolution des URL, téléchargement en meilleure qualité, proxy de revue."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import config, db
from .util import atomic_write_json, ffprobe, log, require_bin, run, safe_replace, video_stream

YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _ydl_opts(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    c = config.get()["ingest"]
    opts: dict[str, Any] = {"quiet": True, "no_warnings": True, "noprogress": True}
    if c.get("js_runtime"):
        opts["js_runtimes"] = {c["js_runtime"]: {"path": None}}
    if c.get("cookies_from_browser"):
        opts["cookiesfrombrowser"] = (c["cookies_from_browser"],)
    opts.update(extra or {})
    return opts


def _normalize_channel_url(url: str) -> str:
    """Une URL de chaîne nue liste ses onglets : on vise l'onglet Vidéos."""
    m = re.match(r"^(https?://(www\.)?youtube\.com/(@[^/?#]+|channel/[^/?#]+|c/[^/?#]+|user/[^/?#]+))/?$", url)
    return m.group(1) + "/videos" if m else url


def resolve(url: str) -> list[dict[str, Any]]:
    """Rend [{id, url, title}] pour une vidéo, une playlist ou une chaîne, sans rien télécharger."""
    import yt_dlp

    url = _normalize_channel_url(url.strip())
    limit = int(config.get()["ingest"].get("max_videos_per_channel", 10))
    is_channel = "/@" in url or "/channel/" in url or "/c/" in url or "/user/" in url
    opts = _ydl_opts({"extract_flat": "in_playlist", "skip_download": True})
    if is_channel:
        opts["playlistend"] = limit
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    entries = info.get("entries")
    if entries is None:
        return [{"id": info["id"], "url": info.get("webpage_url") or url, "title": info.get("title")}]
    out = []
    for e in entries:
        if not e or not e.get("id") or not YT_ID.match(e["id"]):
            continue  # onglets imbriqués, shorts sans id standard, etc.
        out.append({"id": e["id"], "url": f"https://www.youtube.com/watch?v={e['id']}", "title": e.get("title")})
    return out


def add(url: str) -> tuple[list[str], list[str]]:
    """Enregistre les vidéos d'une URL. Rend (nouvelles, déjà connues)."""
    new, known = [], []
    for v in resolve(url):
        (new if db.insert_video(v["id"], v["url"], title=v.get("title")) else known).append(v["id"])
    return new, known


def download(video_id: str) -> None:
    """Télécharge la source et stocke les métadonnées. Sans effet si déjà fait."""
    import yt_dlp

    v = db.get_video(video_id)
    if v["source_path"] and Path(v["source_path"]).exists():
        return
    c = config.get()["ingest"]
    vdir = config.video_dir(video_id)
    db.update_video(video_id, step="téléchargement")
    opts = _ydl_opts({
        "format": c.get("format", "bv*+ba/b"),
        "merge_output_format": c.get("merge_output_format", "mkv"),
        "outtmpl": str(vdir / "source.%(ext)s"),
        "writeinfojson": False,
        "retries": 10,
        "fragment_retries": 10,
        "continuedl": True,
    })
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(v["url"], download=True)
        info = ydl.sanitize_info(info)
    src = next((p for p in vdir.glob("source.*") if p.suffix not in {".part", ".ytdl", ".json"}), None)
    if src is None:
        raise RuntimeError("yt-dlp n'a produit aucun fichier source")
    keep = {k: info.get(k) for k in (
        "id", "title", "channel", "channel_id", "channel_url", "duration", "upload_date",
        "description", "chapters", "webpage_url", "width", "height", "fps", "language")}
    atomic_write_json(vdir / "info.json", keep)
    db.update_video(
        video_id,
        title=info.get("title"), channel=info.get("channel"), channel_id=info.get("channel_id"),
        duration=float(info.get("duration") or 0) or None, upload_date=info.get("upload_date"),
        description=info.get("description"), chapters=info.get("chapters") or [],
        source_path=str(src),
    )
    if not db.get_video(video_id)["duration"]:
        db.update_video(video_id, duration=float(ffprobe(src)["format"]["duration"]))
    log.info("[%s] téléchargé : %s", video_id, src.name)


def make_proxy(video_id: str) -> None:
    """Aperçu H.264 léger pour la lecture et l'ajustement instantanés dans le navigateur."""
    v = db.get_video(video_id)
    out = config.video_dir(video_id) / "proxy.mp4"
    if v["proxy_path"] and Path(v["proxy_path"]).exists():
        return
    db.update_video(video_id, step="aperçu")
    h = int(config.get()["ingest"].get("proxy_height", 480))
    tmp = out.with_name("proxy.tmp.mp4")
    run([require_bin("ffmpeg"), "-y", "-v", "error", "-i", v["source_path"],
         "-vf", f"scale=-2:'min({h},ih)'", "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
         "-g", "48", "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart", str(tmp)])
    safe_replace(tmp, out)
    db.update_video(video_id, proxy_path=str(out))


def source_size(video_id: str) -> tuple[int, int]:
    v = db.get_video(video_id)
    s = video_stream(ffprobe(Path(v["source_path"])))
    return int(s["width"]), int(s["height"])
