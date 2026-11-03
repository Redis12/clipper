"""Enchaînement des étapes. Idempotent : relancer reprend là où ça s'est arrêté."""
from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor

from . import config, cut, db, ingest, selection, thumbs, titles, transcribe
from .util import file_lock, log


def prepare_clip(clip_id: int) -> None:
    """Titres → (découpe) → miniature. Chaque sous-étape saute si déjà faite."""
    c = db.get_clip(clip_id)
    try:
        titles.generate(clip_id)
        if config.get()["cut"].get("render_before_review", True):
            cut.render(clip_id)
        if not c["thumb_path"]:
            thumbs.make(clip_id)
        if db.get_clip(clip_id)["status"] == "pending":
            db.update_clip(clip_id, status="review", error=None)
    except Exception as e:  # un clip en échec ne bloque pas les autres
        log.error("clip %s : %s", clip_id, e)
        db.update_clip(clip_id, error=str(e)[:2000])


def process_video(video_id: str) -> bool:
    lock = config.video_dir(video_id) / ".lock"
    with file_lock(lock) as got:
        if not got:
            log.info("[%s] déjà en cours ailleurs, je passe", video_id)
            return False
        try:
            db.update_video(video_id, error=None)
            ingest.download(video_id)
            ingest.make_proxy(video_id)
            db.update_video(video_id, status="ingested")
            transcribe.transcribe(video_id)
            db.update_video(video_id, status="transcribed")
            selection.select(video_id)
            db.update_video(video_id, step="titres, découpe, miniatures")
            pending = [c["id"] for c in db.clips_for(video_id, ["pending"])]
            # Titres en parallèle (appels réseau), puis découpe/miniatures en série (ffmpeg occupe déjà les cœurs).
            with ThreadPoolExecutor(4) as ex:
                list(ex.map(lambda cid: _safe(titles.generate, cid), pending))
            for cid in pending:
                prepare_clip(cid)
            db.update_video(video_id, status="review", step=None)
            return True
        except Exception as e:
            log.error("[%s] échec : %s", video_id, e)
            log.debug(traceback.format_exc())
            db.update_video(video_id, status="failed", error=str(e)[:2000], step=None)
            return False


def _safe(fn, clip_id: int) -> None:
    try:
        fn(clip_id)
    except Exception as e:
        log.error("clip %s : %s", clip_id, e)
        db.update_clip(clip_id, error=str(e)[:2000])


def pending_videos() -> list[str]:
    return [r["id"] for r in db.query(
        "SELECT id FROM videos WHERE status NOT IN ('review') OR id IN "
        "(SELECT video_id FROM clips WHERE status='pending') ORDER BY created_at")]


def run_all(video_id: str | None = None) -> None:
    for vid in ([video_id] if video_id else pending_videos()):
        process_video(vid)
