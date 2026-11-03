"""Page de revue locale (FastAPI). Une seule personne, en local : pas d'authentification."""
from __future__ import annotations

import os
import threading
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .. import config, cut, db, ingest, pipeline, quota, schedule, thumbs, titles, youtube
from . import jobs
from ..util import log, tc

HERE = Path(__file__).parent
app = FastAPI(title="Clipper")

from . import lan as _lan  # noqa: E402

app.middleware("http")(_lan.guard)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.filters["tc"] = tc
templates.env.filters["local"] = schedule.local


def _seo(v):
    from ..slides import seo
    try:
        return seo.build(dict(v))
    except Exception:
        return {"youtube": {"title": v.get("title", ""), "description": "", "tags": ""}, "tiktok": "", "instagram": ""}


templates.env.globals["seo"] = _seo

from . import slides_routes  # noqa: E402

slides_routes.templates = templates
app.include_router(slides_routes.router)

# --- travail en arrière-plan (voir jobs.py) -------------------------------------------
state: dict[str, Any] = {"last_publish": None, "publish_report": []}


def enqueue(label: str, fn: Callable[[], Any], lane: str = "video") -> None:
    jobs.enqueue(label, fn, lane)


def _publish_job() -> None:
    from ..slides import publish as spublish
    report = []
    try:
        report += youtube.publish()
    except Exception as e:
        report.append(f"Clips : publication impossible : {e}")
    try:
        report += spublish.run()
    except Exception as e:
        report.append(f"Slideshows : publication impossible : {e}")
    state["publish_report"] = report
    state["last_publish"] = db.now()


def _auto_publish() -> None:
    from ..slides import trends
    while True:
        time.sleep(30 * 60)
        if config.get()["publish"].get("auto_in_server", True):
            enqueue("publication auto", _publish_job, "slides")
        try:
            if trends.due_for_refresh():
                enqueue("veille des tendances", trends.refresh, "slides")
        except Exception as e:
            log.warning("veille : %s", e)


@app.on_event("startup")
def _start() -> None:
    from ..slides import library as slib
    from ..slides import produce
    if os.environ.get("CLIPPER_TESTING"):      # tests : pas de travail en arrière-plan
        return
    jobs.start()
    threading.Thread(target=_auto_publish, daemon=True).start()
    # Reprend ce qui a été laissé en plan (machine éteinte, Ctrl+C, erreur réseau…).
    for vid in pipeline.pending_videos():
        if db.get_video(vid)["status"] != "failed":
            enqueue(f"vidéo {vid}", lambda vid=vid: pipeline.process_video(vid))
    enqueue("scan de la bibliothèque", slib.scan, "slides")
    for src in db.query("SELECT id FROM sources WHERE status IN ('new','downloading','extracting')"):
        enqueue(f"captures {src['id']}", lambda s=src["id"]: slib.process_source(s), "video")
    for sid in produce.pending():
        enqueue(f"slideshow {sid}", lambda sid=sid: produce.produce(sid), "slides")


# --- helpers ------------------------------------------------------------------

def clip_or_404(clip_id: int) -> dict:
    c = db.get_clip(clip_id)
    if not c:
        raise HTTPException(404, "clip inconnu")
    return c


def clip_json(c: dict) -> dict:
    keys = ("id", "video_id", "rank", "start", "end", "sel_start", "sel_end", "topic", "score", "reason", "status",
            "reject_reason", "titles", "title_idx", "description", "tags", "thumb_text", "frame_idx",
            "render_needed", "publish_at", "youtube_id", "error")
    d = {k: c.get(k) for k in keys}
    d["frames"] = [{"t": f["t"], "face": f["face"] > 0} for f in (c.get("frames") or [])]
    d["publish_local"] = schedule.local(c.get("publish_at"))
    d["has_thumb"] = bool(c.get("thumb_path"))
    d["updated_at"] = c.get("updated_at")
    return d


def bounds_cfg() -> tuple[float, float]:
    b = config.get()["bounds"]
    return float(b["min_duration"]), float(b["max_duration"])


# --- pages --------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    videos = db.query("SELECT * FROM videos ORDER BY created_at DESC")
    counts = {r["video_id"]: r for r in db.query(
        "SELECT video_id, SUM(status='review') AS review, SUM(status='approved') AS approved, "
        "SUM(status='uploaded') AS uploaded, SUM(status='rejected') AS rejected, SUM(status='pending') AS pending "
        "FROM clips GROUP BY video_id")}
    return templates.TemplateResponse(request, "index.html", {
        "videos": videos, "counts": counts, "current": jobs.busy_label(), "waiting": jobs.waiting(),
        "q": quota.summary(), "queue_len": len(schedule.queue())})


@app.post("/add")
async def add(request: Request):
    form = await request.form()
    url = str(form.get("url", "")).strip()
    if not url:
        return RedirectResponse("/", 303)
    try:
        new, known = ingest.add(url)
    except Exception as e:
        return templates.TemplateResponse(request, "index.html", {
            "videos": db.query("SELECT * FROM videos ORDER BY created_at DESC"), "counts": {},
            "current": jobs.busy_label(), "waiting": jobs.waiting(), "q": quota.summary(),
            "queue_len": len(schedule.queue()), "error": f"URL non reconnue : {e}"}, status_code=400)
    for vid in new:
        enqueue(f"vidéo {vid}", lambda vid=vid: pipeline.process_video(vid))
    return RedirectResponse(f"/?added={len(new)}&known={len(known)}", 303)


@app.post("/video/{video_id}/retry")
def retry(video_id: str):
    enqueue(f"vidéo {video_id}", lambda: pipeline.process_video(video_id))
    return RedirectResponse("/", 303)


@app.get("/video/{video_id}", response_class=HTMLResponse)
def review(request: Request, video_id: str):
    v = db.get_video(video_id)
    if not v:
        raise HTTPException(404)
    clips = db.query("SELECT * FROM clips WHERE video_id=? AND status!='rejected_auto' ORDER BY score DESC, start",
                     (video_id,))
    auto = db.clips_for(video_id, ["rejected_auto"])
    mn, mx = bounds_cfg()
    return templates.TemplateResponse(request, "video.html", {
        "v": v, "clips": [clip_json(c) for c in clips], "auto": [clip_json(c) for c in auto],
        "min_d": mn, "max_d": mx, "max_chars": int(config.get()["titles"]["max_title_chars"])})


@app.get("/queue", response_class=HTMLResponse)
def queue_page(request: Request):
    recent = db.query("SELECT c.*, v.title AS source_title FROM clips c JOIN videos v ON v.id=c.video_id "
                      "WHERE c.status='uploaded' ORDER BY c.publish_at DESC LIMIT 30")
    return templates.TemplateResponse(request, "queue.html", {
        "items": schedule.queue(), "recent": recent, "q": quota.summary(), "current": jobs.busy_label(),
        "report": state["publish_report"], "last_publish": state["last_publish"],
        "due_ids": {c["id"] for c in schedule.due_for_upload()},
        "ahead": config.get()["publish"].get("upload_ahead_days", 2)})


@app.post("/queue/publish")
def publish_now():
    enqueue("publication", _publish_job)
    return RedirectResponse("/queue", 303)


@app.get("/api/status")
def status():
    return {"current": jobs.busy_label(), "waiting": jobs.waiting(),
            "videos": db.query("SELECT id, status, step, error FROM videos")}


# --- médias -------------------------------------------------------------------

def _file(path: str | None, media_type: str) -> FileResponse:
    if not path or not Path(path).exists():
        raise HTTPException(404)
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "no-cache"})


@app.get("/media/proxy/{video_id}.mp4")
def proxy(video_id: str):
    v = db.get_video(video_id) or {}
    return _file(v.get("proxy_path"), "video/mp4")


@app.get("/media/clip/{clip_id}.mp4")
def clip_file(clip_id: int):
    return _file(clip_or_404(clip_id).get("clip_path"), "video/mp4")


@app.get("/media/thumb/{clip_id}.jpg")
def thumb(clip_id: int):
    return _file(clip_or_404(clip_id).get("thumb_path"), "image/jpeg")


@app.get("/media/frame/{clip_id}/{n}.jpg")
def frame(clip_id: int, n: int):
    frames = clip_or_404(clip_id).get("frames") or []
    if not 0 <= n < len(frames):
        raise HTTPException(404)
    return _file(frames[n]["path"], "image/jpeg")


# --- actions sur un clip --------------------------------------------------------

@app.post("/api/clip/{clip_id}/approve")
def approve(clip_id: int):
    c = clip_or_404(clip_id)
    mn, mx = bounds_cfg()
    d = c["end"] - c["start"]
    if not mn <= d <= mx:
        raise HTTPException(400, f"Durée {tc(d)} hors limites ({tc(mn)}–{tc(mx)}) : ajuste les bornes d'abord.")
    if c["status"] not in ("review", "approved"):
        raise HTTPException(400, "Ce clip n'est pas prêt pour la validation.")
    schedule.approve(clip_id)
    if c["render_needed"]:
        enqueue(f"rendu clip {clip_id}", lambda: cut.render(clip_id))
    return clip_json(db.get_clip(clip_id))


@app.post("/api/clip/{clip_id}/reject")
def reject(clip_id: int):
    clip_or_404(clip_id)
    schedule.unapprove(clip_id, to="rejected")
    return clip_json(db.get_clip(clip_id))


@app.post("/api/clip/{clip_id}/reset")
def reset(clip_id: int):
    c = clip_or_404(clip_id)
    if c["status"] == "rejected_auto" or not c["titles"]:
        db.update_clip(clip_id, status="pending", reject_reason=None)
        enqueue(f"préparation clip {clip_id}", lambda: pipeline.prepare_clip(clip_id))
    else:
        schedule.unapprove(clip_id, to="review")
        if not c["thumb_path"]:
            enqueue(f"miniature clip {clip_id}", lambda: thumbs.make(clip_id))
    return clip_json(db.get_clip(clip_id))


@app.post("/api/clip/{clip_id}/adjust")
def adjust(clip_id: int, body: dict = Body(...)):
    c = clip_or_404(clip_id)
    if c["status"] == "uploaded":
        raise HTTPException(400, "Déjà uploadé")
    v = db.get_video(c["video_id"])
    start, end = float(c["start"]), float(c["end"])
    delta = float(body.get("delta", 0))
    if body.get("edge") == "start":
        start = min(max(0.0, start + delta), end - 1)
    elif body.get("edge") == "end":
        end = max(min(float(v["duration"] or end + delta), end + delta), start + 1)
    elif body.get("edge") == "restore":
        start, end = float(c["sel_start"]), float(c["sel_end"])
    fields: dict[str, Any] = {"start": round(start, 3), "end": round(end, 3), "render_needed": 1}
    if c["description"]:
        fields["description"] = titles.refresh_link(c["description"], v, start)
    db.update_clip(clip_id, **fields)
    if c["status"] == "approved":   # garde son créneau, mais le rendu final sera refait avant upload
        enqueue(f"rendu clip {clip_id}", lambda: cut.render(clip_id))
    return clip_json(db.get_clip(clip_id))


@app.post("/api/clip/{clip_id}/meta")
def meta(clip_id: int, body: dict = Body(...)):
    c = clip_or_404(clip_id)
    if c["status"] == "uploaded":
        raise HTTPException(400, "Déjà uploadé : modifie-le dans YouTube Studio")
    fields: dict[str, Any] = {}
    max_chars = int(config.get()["titles"]["max_title_chars"])
    if "titles" in body:
        fields["titles"] = [titles.clean(t)[:max_chars] for t in body["titles"]]
    if "title_idx" in body:
        fields["title_idx"] = int(body["title_idx"])
    if "description" in body:
        fields["description"] = titles.clean_multiline(str(body["description"]))[:4900]
    if "tags" in body:
        tags = body["tags"] if isinstance(body["tags"], list) else str(body["tags"]).split(",")
        fields["tags"] = titles.fit_tags(tags, 50)
    retext = "thumb_text" in body and titles.clean(body["thumb_text"]) != (c["thumb_text"] or "")
    if "thumb_text" in body:
        fields["thumb_text"] = titles.clean(body["thumb_text"])
    if "frame_idx" in body:
        n = len(c["frames"] or [])
        fields["frame_idx"] = int(body["frame_idx"]) % max(1, n)
        retext = True
    if fields:
        db.update_clip(clip_id, **fields)
    if retext and c["frames"]:
        thumbs.make(clip_id)   # Pillow seul : instantané
    return clip_json(db.get_clip(clip_id))


@app.post("/api/clip/{clip_id}/frames")
def new_frames(clip_id: int):
    clip_or_404(clip_id)
    thumbs.make(clip_id, refresh_frames=True)
    return clip_json(db.get_clip(clip_id))


@app.exception_handler(HTTPException)
async def http_err(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    return HTMLResponse(f"<p>{exc.detail}</p><p><a href='/'>Retour</a></p>", status_code=exc.status_code)
