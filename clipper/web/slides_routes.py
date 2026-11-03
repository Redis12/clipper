"""Pages et API des slideshows."""
from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any

import shutil
import tempfile

from fastapi import APIRouter, Body, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response

from .. import config, db, quota, schedule
from ..slides import ideas, library, produce, publish, render, trends
from . import jobs

router = APIRouter()
templates = None  # injecté par app.py (même environnement Jinja)


def ss_or_404(sid: int) -> dict:
    s = db.get("slideshows", sid)
    if not s:
        raise HTTPException(404, "slideshow inconnu")
    return s


def ss_json(s: dict) -> dict:
    tz = config.get()["slides"]["publish"]["timezone"]
    posts = db.query("SELECT id, platform, mode, status, url, error FROM posts WHERE slideshow_id=? ORDER BY platform",
                     (s["id"],))
    return {
        **{k: s[k] for k in ("id", "anime", "format", "topic", "hook", "angle", "score", "status", "step", "caption",
                             "hashtags", "yt_title", "yt_description", "error", "publish_at", "render_needed")},
        "slides": [{**{k: sl.get(k) for k in ("kind", "label", "text", "anime", "character", "scene", "confidence",
                                              "character_match")},
                    "has_image": bool(sl.get("image_path")), "n_alts": len(sl.get("alts") or [])}
                   for sl in (s["slides"] or [])],
        "publish_local": schedule.local(s["publish_at"]),
        "publish_audience": schedule.local(s["publish_at"], tz),
        "v": s["updated_at"], "posts": posts,
        "has_grid": (render.out_dir(s["id"]) / "grid_vertical.jpg").exists(),
        "has_video": render.has_video(s["id"]),
    }


# --- pages ----------------------------------------------------------------------

@router.get("/slides", response_class=HTMLResponse)
def board(request: Request):
    rows = db.query("SELECT * FROM slideshows WHERE status != 'rejected' ORDER BY "
                    "CASE status WHEN 'review' THEN 0 WHEN 'drafting' THEN 1 WHEN 'queued' THEN 2 WHEN 'failed' THEN 3 "
                    "WHEN 'idea' THEN 4 WHEN 'approved' THEN 5 ELSE 6 END, score DESC, id DESC")
    lib = library.stats()
    animes = list(config.get()["slides"]["animes"])
    known = {library.norm(a) for a in animes}
    animes += sorted(a["anime"] for a in lib if a["anime"] and library.norm(a["anime"]) not in known)   # + dossiers de la bibliothèque
    return templates.TemplateResponse(request, "slides_board.html", {
        "rows": rows, "lib": lib, "animes": animes,
        "formats": config.get()["slides"]["formats"], "current": jobs.busy_label(), "waiting": jobs.waiting(),
        "n_images": sum(a["library"] + a["frames"] for a in lib),
        "n_ideas": config.get()["slides"].get("ideas_per_batch", 12)})


@router.post("/slides/ideas")
def gen_ideas():
    jobs.enqueue("idées de slideshows", ideas.generate_ideas, "slides")
    return RedirectResponse("/slides", 303)


@router.post("/slides/topic")
async def own_topic(request: Request):
    f = await request.form()
    topic = str(f.get("topic", "")).strip()
    anime = str(f.get("anime", "")).strip()
    logo = f.get("logo")
    if anime and logo is not None and getattr(logo, "filename", ""):
        data = await logo.read()
        if data:
            try:
                render.save_logo(ideas.canonical_anime(anime), data)
            except Exception:
                pass                                   # fichier illisible : on continue sans logo
    if topic:
        sid = ideas.add_user_topic(topic, anime, str(f.get("format", "")), str(f.get("notes", "")),
                                   use_logo=f.get("use_logo") is not None)
        jobs.enqueue(f"slideshow {sid}", lambda: produce.produce(sid), "slides")
    return RedirectResponse("/slides", 303)


@router.post("/api/slides/{sid}/produce")
def produce_one(sid: int):
    s = ss_or_404(sid)
    if s["status"] in ("idea", "failed", "rejected"):
        db.update("slideshows", sid, status="queued", error=None)
        jobs.enqueue(f"slideshow {sid}", lambda: produce.produce(sid), "slides")
    return ss_json(db.get("slideshows", sid))


@router.post("/api/slides/{sid}/discard")
def discard(sid: int):
    s = ss_or_404(sid)
    if s["status"] == "approved":
        publish.unapprove(sid, to="rejected")
    else:
        db.update("slideshows", sid, status="rejected")
    return {"ok": True}


@router.get("/slides/{sid}", response_class=HTMLResponse)
def review(request: Request, sid: int):
    s = ss_or_404(sid)
    return templates.TemplateResponse(request, "slides_review.html", {
        "s": s, "data": ss_json(s), "current": jobs.busy_label(),
        "max_words": config.get()["slides"]["max_words_per_slide"]})


@router.get("/slides-library", response_class=HTMLResponse)
def library_page(request: Request):
    return templates.TemplateResponse(request, "slides_library.html", {
        "lib": library.stats(), "sources": db.query("SELECT * FROM sources ORDER BY created_at DESC LIMIT 100"),
        "root": str(library.root()), "music": [p.name for p in library.music_files()],
        "animes": config.get()["slides"]["animes"], "current": jobs.busy_label()})


@router.post("/slides-library/source")
async def add_source(request: Request):
    f = await request.form()
    url, anime = str(f.get("url", "")).strip(), str(f.get("anime", "")).strip()
    if url and anime:
        for sid in library.add_source(url, anime):
            jobs.enqueue(f"captures {sid}", lambda s=sid: library.process_source(s), "video")
    return RedirectResponse("/slides-library", 303)


@router.post("/slides-library/tag")
async def tag(request: Request):
    f = await request.form()
    anime = str(f.get("anime", "")).strip()
    if anime:
        jobs.enqueue(f"tri des captures {anime}", lambda: library.tag_frames(anime), "slides")
    return RedirectResponse("/slides-library", 303)


@router.post("/slides-library/scan")
def rescan():
    jobs.enqueue("scan de la bibliothèque", library.scan, "slides")
    return RedirectResponse("/slides-library", 303)


@router.get("/slides-queue", response_class=HTMLResponse)
def queue_page(request: Request):
    tz = config.get()["slides"]["publish"]["timezone"]
    items = publish.queue()
    for it in items:
        it["local"], it["audience"] = schedule.local(it["publish_at"]), schedule.local(it["publish_at"], tz)
    return templates.TemplateResponse(request, "slides_queue.html", {
        "items": items, "q": quota.summary(), "current": jobs.busy_label(), "tz": tz,
        "auto": {p: publish.is_auto(p) for p in publish.PLATFORMS}, "tt": _tiktok_state()})


def _tiktok_state() -> dict:
    from ..slides import tiktok
    t = config.get()["slides"]["publish"]
    return {"connected": tiktok.connected(), "enabled": bool(t["tiktok"].get("enabled")), "mode": tiktok.mode(),
            "hosting": t.get("hosting", {}).get("kind", "none"),
            "keys": bool(os.environ.get("TIKTOK_CLIENT_KEY") and os.environ.get("TIKTOK_CLIENT_SECRET"))}


@router.get("/tiktok/connect")
def tiktok_connect(request: Request):
    from ..slides import tiktok
    try:
        return RedirectResponse(tiktok.auth_url(request.url.port or 8765), 303)
    except RuntimeError as e:
        return HTMLResponse(f"<p>{e}</p><p><a href='/slides-queue'>Retour</a></p>", 400)


@router.get("/tiktok/callback/")
def tiktok_callback(request: Request, code: str = "", state: str = "", error: str = "",
                    error_description: str = ""):
    from ..slides import tiktok
    if error:
        return HTMLResponse(f"<p>TikTok : {error} {error_description}</p><p><a href='/slides-queue'>Retour</a></p>", 400)
    try:
        tiktok.finish_auth(code, state, request.url.port or 8765)
    except RuntimeError as e:
        return HTMLResponse(f"<p>{e}</p><p><a href='/slides-queue'>Retour</a></p>", 400)
    return RedirectResponse("/slides-queue?tiktok=ok", 303)


# --- médias -----------------------------------------------------------------------

@router.get("/media/slide/{sid}/{fmt}/{n}.jpg")
def slide_img(sid: int, fmt: str, n: int):
    if fmt not in config.get()["slides"]["render"]["sizes"]:
        raise HTTPException(404)
    p = render.out_dir(sid) / fmt / f"{n:02d}.jpg"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


@router.get("/media/slide-alt/{sid}/{idx}/{k}.jpg")
def slide_alt(sid: int, idx: int, k: int):
    s = ss_or_404(sid)
    sl = s["slides"][idx]
    paths = [sl.get("image_path"), *(sl.get("alts") or [])]
    if not 0 <= k < len(paths) or not paths[k] or not Path(paths[k]).exists():
        raise HTTPException(404)
    return FileResponse(paths[k], headers={"Cache-Control": "max-age=3600"})


@router.get("/media/grid/{sid}/{fmt}.jpg")
def grid_img(sid: int, fmt: str):
    ss_or_404(sid)
    p = render.out_dir(sid) / f"grid_{fmt}.jpg"
    if fmt not in config.get()["slides"]["render"]["sizes"] or not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})


@router.get("/media/short/{sid}.mp4")
def short(sid: int):
    p = render.out_dir(sid) / "short.mp4"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4", headers={"Cache-Control": "no-cache"})


@router.get("/slides/{sid}/pack/{platform}.zip")
def pack(sid: int, platform: str):
    ss_or_404(sid)
    if platform not in publish.PLATFORMS:
        raise HTTPException(404)
    data = publish.export_zip(sid, platform)
    return Response(data, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="slideshow-{sid}-{platform}.zip"'})


# --- actions ------------------------------------------------------------------------

@router.post("/api/slides/{sid}/slide/{idx}")
def edit(sid: int, idx: int, body: dict = Body(...)):
    s = ss_or_404(sid)
    if s["status"] not in ("review", "approved"):
        raise HTTPException(400, "Slideshow pas encore prêt")
    if not 0 <= idx < len(s["slides"]):
        raise HTTPException(404)
    s = produce.edit_slide(sid, idx, **{k: body.get(k) for k in ("text", "label", "character", "scene") if k in body})
    return ss_json(s)


@router.post("/api/slides/{sid}/slide/{idx}/image/{k}")
def choose(sid: int, idx: int, k: int):
    s = ss_or_404(sid)
    sl = s["slides"][idx]
    paths = [sl.get("image_path"), *(sl.get("alts") or [])]
    if not 0 < k < len(paths):
        raise HTTPException(400, "image inconnue")
    return ss_json(produce.swap_image(sid, idx, paths[k]))


@router.post("/api/slides/{sid}/slide/{idx}/upload")
async def upload_image(sid: int, idx: int, file: UploadFile = File(...)):
    s = ss_or_404(sid)
    if not 0 <= idx < len(s["slides"] or []):
        raise HTTPException(404)
    sl = s["slides"][idx]
    try:
        path = library.add_uploaded(await file.read(), file.filename or "image.jpg", sl.get("anime") or s["anime"],
                                    sl.get("character") or "")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return ss_json(produce.swap_image(sid, idx, path))


@router.get("/api/slides/{sid}/slide/{idx}/choices")
def slide_choices(sid: int, idx: int):
    s = ss_or_404(sid)
    if not 0 <= idx < len(s["slides"] or []):
        raise HTTPException(404)
    sl = s["slides"][idx]
    rows = library.choices(sl.get("anime") or s["anime"], sl.get("character") or "", wallpaper=bool(sl.get("wallpaper")))
    return [{"id": r["id"], "uses": r["use_count"] or 0, "character": r["character"] or "",
             "current": r["path"] == sl.get("image_path")} for r in rows]


@router.post("/api/slides/{sid}/slide/{idx}/lib/{image_id}")
def slide_use_library_image(sid: int, idx: int, image_id: int):
    s = ss_or_404(sid)
    img = db.get("images", image_id)
    if not img or not 0 <= idx < len(s["slides"] or []):
        raise HTTPException(404)
    return ss_json(produce.swap_image(sid, idx, img["path"]))


@router.get("/media/lib/{image_id}.jpg")
def library_thumb(image_id: int):
    p = library.thumb(image_id)
    if not p:
        raise HTTPException(404)
    return FileResponse(p, media_type="image/jpeg")


@router.post("/api/slides/{sid}/slide/{idx}/delete")
def delete_slide(sid: int, idx: int):
    s = ss_or_404(sid)
    if s["status"] not in ("review", "approved"):
        raise HTTPException(400, "Slideshow pas encore prêt")
    try:
        return ss_json(produce.delete_slide(sid, idx))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/slides/{sid}/slide/{idx}/repick")
def repick(sid: int, idx: int):
    ss_or_404(sid)
    return ss_json(produce.repick(sid, idx))


@router.post("/api/slides/{sid}/meta")
def meta(sid: int, body: dict = Body(...)):
    ss_or_404(sid)
    f: dict[str, Any] = {}
    if "caption" in body:
        f["caption"] = " ".join(str(body["caption"]).split())[:2000]
    if "hashtags" in body:
        raw = body["hashtags"] if isinstance(body["hashtags"], list) else str(body["hashtags"]).replace(",", " ").split()
        f["hashtags"] = [h.strip("#").lower() for h in raw if h.strip("#")][:15]
    if "yt_title" in body:
        f["yt_title"] = " ".join(str(body["yt_title"]).split())[:100]
    if f:
        db.update("slideshows", sid, **f)
    return ss_json(db.get("slideshows", sid))


@router.post("/api/slides/{sid}/approve")
def approve(sid: int):
    s = ss_or_404(sid)
    missing = [i + 1 for i, sl in enumerate(s["slides"] or []) if sl["kind"] == "body" and not sl.get("image_path")]
    if missing:
        raise HTTPException(400, f"Slide(s) {', '.join(map(str, missing))} sans image")
    publish.approve(sid)
    if render.has_video(sid) and db.get("slideshows", sid)["render_needed"]:
        jobs.enqueue(f"Short {sid}", lambda: render.render_video(sid), "slides")
    return ss_json(db.get("slideshows", sid))


@router.post("/api/slides/{sid}/reject")
def reject(sid: int):
    s = ss_or_404(sid)
    if s["status"] == "approved":
        publish.unapprove(sid, to="rejected")
    else:
        db.update("slideshows", sid, status="rejected")
    return ss_json(db.get("slideshows", sid))


@router.post("/api/slides/{sid}/unapprove")
def unapprove(sid: int):
    ss_or_404(sid)
    publish.unapprove(sid)
    return ss_json(db.get("slideshows", sid))


@router.post("/api/slides/{sid}/rerender")
def rerender(sid: int):
    ss_or_404(sid)
    jobs.enqueue(f"vidéo {sid}", lambda: publish.make_video(sid), "slides")
    return {"ok": True}


@router.post("/api/posts/{pid}/done")
def post_done(pid: int, body: dict = Body(default={})):
    if not db.get("posts", pid):
        raise HTTPException(404)
    publish.mark_manual_done(pid, str(body.get("url", "")))
    return {"ok": True}


# --- veille des tendances ---------------------------------------------------------------

@router.get("/slides-trends", response_class=HTMLResponse)
def trends_page(request: Request, show: str = "useful"):
    where = {"useful": "status='analyzed' AND slideshow_like=1", "all": "1=1",
             "pending": "status IN ('new','failed')"}.get(show, "status='analyzed' AND slideshow_like=1")
    rows = db.query(f"SELECT * FROM trends WHERE {where} ORDER BY COALESCE(score,0) DESC, id DESC LIMIT 200")
    tc = config.get()["slides"]["trends"]
    return templates.TemplateResponse(request, "slides_trends.html", {
        "rows": rows, "show": show, "last": trends.last_refresh(), "current": jobs.busy_label(),
        "yt_on": tc["youtube"].get("enabled", True), "ig_on": tc["instagram"].get("enabled", False),
        "counts": {r["status"]: r["n"] for r in db.query("SELECT status, COUNT(*) AS n FROM trends GROUP BY status")},
        "q": quota.summary(), "anilist": trends.anilist()})


@router.post("/slides-trends/refresh")
def trends_refresh():
    jobs.enqueue("veille des tendances", trends.refresh, "slides")
    return RedirectResponse("/slides-trends", 303)


@router.post("/slides-trends/upload")
async def trends_upload(files: list[UploadFile] = File(...)):
    tmpdir = Path(tempfile.mkdtemp(prefix="clipper-shots-"))
    saved = []
    for f in files:
        ext = Path(f.filename or "").suffix.lower()
        if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
            continue
        p = tmpdir / f"{len(saved)}{ext}"
        with open(p, "wb") as out:
            shutil.copyfileobj(f.file, out)
        saved.append((p, f.filename or p.name))

    def work():
        for p, name in saved:
            try:
                trends.import_screenshot(p, name)
            except Exception:
                pass
        shutil.rmtree(tmpdir, ignore_errors=True)

    jobs.enqueue(f"lecture de {len(saved)} capture(s)", work, "slides")
    return RedirectResponse("/slides-trends?show=all", 303)


@router.post("/api/trends/{tid}/ideas")
def trend_ideas(tid: int):
    if not db.get("trends", tid):
        raise HTTPException(404)
    jobs.enqueue(f"idées depuis la tendance {tid}", lambda: ideas.generate_ideas(focus_trend=tid), "slides")
    return {"ok": True}


@router.post("/api/trends/{tid}/hide")
def trend_hide(tid: int):
    if not db.get("trends", tid):
        raise HTTPException(404)
    db.update("trends", tid, status="irrelevant")
    return {"ok": True}


@router.get("/media/trend/{tid}")
def trend_img(tid: int):
    t = db.get("trends", tid)
    if not t or not t["image_path"] or not Path(t["image_path"]).exists():
        raise HTTPException(404)
    return FileResponse(t["image_path"])


# --- page téléphone -------------------------------------------------------------------

@router.get("/m", response_class=HTMLResponse)
def mobile(request: Request):
    rows = db.query("SELECT * FROM slideshows WHERE status IN ('approved','review','published') "
                    "ORDER BY CASE status WHEN 'approved' THEN 0 WHEN 'review' THEN 1 ELSE 2 END, publish_at, id DESC "
                    "LIMIT 30")
    tz = config.get()["slides"]["publish"]["timezone"]
    items = []
    for r in rows:
        posts = {p["platform"]: p for p in db.query("SELECT * FROM posts WHERE slideshow_id=?", (r["id"],))}
        items.append({**r, "n": len(r["slides"] or []), "caption_full": publish.caption(r),
                      "when": schedule.local(r["publish_at"]), "when_us": schedule.local(r["publish_at"], tz),
                      "posts": posts, "grid": (render.out_dir(r["id"]) / "grid_vertical.jpg").exists()})
    from . import lan
    on_pc = (request.client.host if request.client else "") in lan.LOCAL
    port = request.url.port or int(config.get().get("server", {}).get("port", 8765))
    phone = lan.phone_url(port) if on_pc else ""
    return templates.TemplateResponse(request, "mobile.html", {
        "items": items, "on_pc": on_pc, "phone_url": phone, "qr": lan.qr_svg(phone) if phone else "",
        "battles": __import__("clipper.slides.battle", fromlist=["listing"]).listing()[:6],
        "fusions": __import__("clipper.slides.fusion", fromlist=["listing"]).listing()[:6],
        "lan_on": os.environ.get("CLIPPER_LAN") == "1"})


# --- vidéos « battle » (persos-balles) -------------------------------------------------

@router.get("/battle", response_class=HTMLResponse)
def battle_page(request: Request):
    from ..slides import battle
    c = config.get()["slides"].get("battle", {})
    return templates.TemplateResponse(request, "battle.html", {
        "roster": battle.roster(), "videos": battle.listing(), "current": jobs.busy_label(),
        "sheets": __import__("clipper.slides.movesets", fromlist=["all_sheets"]).all_sheets(),
        "domains": [v for v in __import__("clipper.slides.fusion", fromlist=["listing"]).listing()
                    if v.get("kind") == "domain"],
        "links_per": c.get("links_per", 8), "max_seconds": c.get("max_seconds", 45)})


@router.post("/battle")
async def battle_make(request: Request):
    from ..slides import battle
    f = await request.form()
    ids = [int(x) for x in f.getlist("img") if str(x).isdigit()]
    fighters = []
    for i in ids:
        r = db.get("images", i)
        if r:
            fighters.append({"name": r["character"] or "?", "image_path": r["path"]})
    if len(fighters) >= 2:
        title = str(f.get("title") or "Which anime character wins?").strip()
        links = int(f.get("links_per") or 8)
        jobs.enqueue(f"vidéo battle ({len(fighters)} persos)",
                     lambda: battle.generate(fighters, title=title, links_per=links), "video")
    return RedirectResponse("/battle", 303)


@router.post("/domain")
async def domain_make(request: Request):
    """Domain War : 2 persos cochés, leurs domaines (grille) s'affrontent 30 s."""
    from ..slides import domain
    f = await request.form()
    ids = [int(x) for x in f.getlist("img") if str(x).isdigit()][:2]
    fighters = []
    for i in ids:
        r = db.get("images", i)
        if r:
            fighters.append({"name": r["character"] or "?", "image_path": r["path"]})
    if len(fighters) == 2:
        title = str(f.get("title") or "").strip() or None
        try:
            secs = max(15.0, min(90.0, float(f.get("seconds") or 35)))
        except ValueError:
            secs = 35.0
        w = str(f.get("winner") or "")
        winner = int(w) if w in ("0", "1") else (-1 if w in ("d0", "d1") else None)
        underdog = int(w[1]) if w in ("d0", "d1") else None          # égalité : celui qui perd d'abord
        comeback = bool(f.get("comeback")) and winner is not None
        cine = str(f.get("cine") or "auto")
        snd = str(f.get("sounds") or "anime")
        snd = snd if snd in ("auto", "anime", "safe") else "anime"

        def run():
            if cine != "both":
                return domain.generate(fighters, seconds=secs, title=title, winner=winner, comeback=comeback,
                                       cine=cine if cine in ("auto", "clip", "card") else "auto", sounds=snd,
                                       underdog=underdog)
            p = domain.generate(fighters, seconds=secs, title=title, winner=winner, comeback=comeback, cine="clip",
                                underdog=underdog,
                                sounds="anime" if snd == "auto" else snd)          # TikTok / Insta
            m1 = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
            seed = m1["seed"]                                    # même combat (même n° d'épisode), sans clip
            return domain.generate(fighters, seconds=secs, title=m1.get("title") or title, winner=winner,
                                   comeback=comeback, seed=seed,
                                   underdog=underdog,
                                   cine="card", sounds=snd,
                                   out=domain.out_dir() / f"domain_{seed}_popup.mp4")
        jobs.enqueue(f"domain war ({fighters[0]['name']} vs {fighters[1]['name']})", run, "video")
    return RedirectResponse("/battle", 303)


@router.get("/media/battle/{name}")
def battle_file(name: str):
    from ..slides import battle
    p = battle.out_dir() / Path(name).name
    if not p.exists() or p.suffix != ".mp4":
        raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4", filename=p.name)


# --- vidéos « Fusion Battle » (façon Suika) --------------------------------------------

@router.get("/fusion", response_class=HTMLResponse)
def fusion_page(request: Request):
    from ..slides import battle, fusion
    c = config.get()["slides"].get("fusion", {})
    return templates.TemplateResponse(request, "fusion.html", {
        "roster": battle.roster(), "chains": fusion.chain_list(), "sounds": fusion.sound_list(),
        "default_sound": c.get("sound") or "", "videos": fusion.listing(), "current": jobs.busy_label()})


def _fusion_sound(form) -> str | None:
    from ..slides import fusion
    return fusion.sound_path(str(form.get("sound") or ""))


@router.post("/fusion/sound")
async def fusion_sound_upload(file: UploadFile = File(...)):
    """Ajoute un bruitage (mp3, wav…) dans library/_sounds."""
    from ..slides import fusion
    name = Path(file.filename or "son.mp3").name
    if Path(name).suffix.lower() not in fusion.SOUND_EXT:
        raise HTTPException(400, "Format de son non pris en charge (mp3, wav, ogg, m4a, aac, flac)")
    data = await file.read()
    if len(data) > 15_000_000:
        raise HTTPException(400, "Son trop lourd (15 Mo max)")
    (fusion.sounds_dir() / name).write_bytes(data)
    return RedirectResponse(f"/fusion?sound={name}", 303)


@router.get("/fusion/preview.wav")
def fusion_preview(sound: str = "", tiers: int = 7, fat: float = 1.0):
    """Aperçu du bruitage niveau par niveau (de plus en plus grave / gras / écho)."""
    from ..slides import fusion
    p = fusion.preview(fusion.sound_path(sound), max(3, min(10, tiers)), fat=max(0.0, min(2.0, fat)))
    return FileResponse(p, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@router.post("/fusion")
async def fusion_make(request: Request):
    from ..slides import fusion
    f = await request.form()
    chain = str(f.get("chain") or "").strip()
    if chain:
        tiers = fusion.tiers_from_chain(chain)
    else:
        tiers = []
        for x in str(f.get("order") or "").split(","):
            r = db.get("images", int(x)) if x.strip().isdigit() else None
            if r:
                tiers.append({"name": r["character"] or "?", "image_path": r["path"]})
    if len(tiers) >= 3:
        title = str(f.get("title") or "Fusion Battle").strip()
        sound = _fusion_sound(f)
        try:
            fat = max(0.0, min(2.0, float(f.get("fat") or 1)))
        except ValueError:
            fat = 1.0
        jobs.enqueue(f"vidéo fusion ({len(tiers)} niveaux)",
                     lambda: fusion.generate(tiers, title=title, sound=sound, fat=fat), "video")
    return RedirectResponse("/fusion", 303)


@router.post("/fusion/race")
async def fusion_race_make(request: Request):
    """Fusion Race : 2 dossiers _fusion côte à côte, le premier à sa forme finale gagne."""
    from ..slides import fusion, fusion_race
    f = await request.form()
    names = [str(f.get("chain_a") or "").strip(), str(f.get("chain_b") or "").strip()]
    chains = [fusion.tiers_from_chain(n) for n in names if n]
    if len(chains) == 2 and all(len(ch) >= 3 for ch in chains) and names[0] != names[1]:
        title = str(f.get("title") or "").strip() or None
        sounds = [fusion.sound_path(str(f.get("sound_a") or "")), fusion.sound_path(str(f.get("sound_b") or ""))]
        try:
            fat = max(0.0, min(2.0, float(f.get("fat") or 1)))
        except ValueError:
            fat = 1.0
        jobs.enqueue(f"fusion race ({names[0]} vs {names[1]})",
                     lambda: fusion_race.generate(chains, names, title=title, sounds=sounds, fat=fat), "video")
    return RedirectResponse("/fusion", 303)


@router.get("/media/fusion/{name}")
def fusion_file(name: str):
    from ..slides import fusion
    p = fusion.out_dir() / Path(name).name
    if not p.exists() or p.suffix != ".mp4":
        raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4", filename=p.name)


# --- mini-éditeur : musique sous une vidéo générée (Instagram / YouTube) -------------

@router.get("/music", response_class=HTMLResponse)
def music_page(request: Request, done: str = "", err: str = ""):
    from ..slides import remix
    vids = remix.videos()
    return templates.TemplateResponse(request, "music.html", {
        "videos": [v for v in vids if not v["file"].endswith("_music.mp4")],
        "done_list": [v for v in vids if v["file"].endswith("_music.mp4")],
        "musics": remix.musics(), "done": done, "err": err})


@router.post("/music/upload")
async def music_upload(file: UploadFile = File(...)):
    from ..slides import remix
    data = await file.read()
    if len(data) > 40_000_000:
        raise HTTPException(400, "Musique trop lourde (40 Mo max)")
    try:
        remix.save_upload(file.filename or "", data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return RedirectResponse("/music", 303)


@router.get("/music/preview.mp3")
def music_preview(name: str, start: float = 0.0):
    from ..slides import remix
    m = remix.music_path(name)
    if not m:
        raise HTTPException(404)
    return FileResponse(remix.preview_music(m, start), media_type="audio/mpeg", headers={"Cache-Control": "no-store"})


@router.post("/music")
async def music_make(request: Request):
    from urllib.parse import quote

    from ..slides import remix
    f = await request.form()
    media, _, name = str(f.get("video") or "").partition("/")
    video, music = remix.video_path(media, name), remix.music_path(str(f.get("music") or ""))
    if not video or not music:
        return RedirectResponse("/music?err=" + quote("Choisis une vidéo et une musique"), 303)

    def num(key, default, lo, hi):
        try:
            return max(lo, min(hi, float(f.get(key) or default)))
        except ValueError:
            return default
    try:
        out = remix.add_music(video, music, start=num("start", 0, 0, 3600), music_volume=num("music_volume", 35, 0, 150) / 100,
                              sfx_volume=num("sfx_volume", 100, 0, 150) / 100)
    except RuntimeError as e:
        return RedirectResponse("/music?err=" + quote(str(e)[:200]), 303)
    return RedirectResponse(f"/music?done={media}/{out.name}", 303)


@router.post("/media/{media}/{name}/remove")
def media_remove(request: Request, media: str, name: str):
    """Retire une vidéo générée déjà postée (déplacée dans data/archive/)."""
    from ..slides import remix
    if not remix.archive(media, name):
        raise HTTPException(404)
    back = request.headers.get("referer") or "/"
    return RedirectResponse(back if back.startswith(("http://", "https://", "/")) else "/", 303)
