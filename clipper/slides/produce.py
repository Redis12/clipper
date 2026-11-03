"""Production d'un slideshow : script → images → rendu → prêt pour la revue."""
from __future__ import annotations

import traceback

from .. import config, db
from ..util import file_lock, log
from . import ideas, library, render


def choose_images(slideshow_id: int, only: list[int] | None = None) -> None:
    s = db.get("slideshows", slideshow_id)
    slides = s["slides"]
    used = {sl["image_path"] for i, sl in enumerate(slides) if sl.get("image_path") and (only is None or i not in only)}
    chosen = []
    for i, sl in enumerate(slides):
        if only is not None and i not in only:
            continue
        if sl.get("twin") and i > 0:                    # wallpaper seul = même image que son aperçu
            sl.update({k: slides[i - 1].get(k) for k in ("image_path", "alts", "character_match")})
            continue
        r = library.pick(sl, exclude=used, seed=slideshow_id * 100 + i)
        sl.update(r)
        if r["image_path"]:
            used.add(r["image_path"])
            chosen.append(r["image_path"])
        db.update("slideshows", slideshow_id, slides=slides, step=f"images {i + 1}/{len(slides)}")
    library.mark_used(chosen)


def produce(slideshow_id: int) -> bool:
    lock = render.out_dir(slideshow_id) / ".lock"
    with file_lock(lock) as got:
        if not got:
            return False
        try:
            db.update("slideshows", slideshow_id, status="drafting", step="script", error=None)
            ideas.write_script(slideshow_id)
            s = db.get("slideshows", slideshow_id)
            if not all(sl.get("image_path") for sl in s["slides"]):
                missing = [i for i, sl in enumerate(s["slides"]) if not sl.get("image_path")]
                choose_images(slideshow_id, missing)
            db.update("slideshows", slideshow_id, step="rendu des slides")
            render.render_all(slideshow_id)
            if render.video_auto():
                db.update("slideshows", slideshow_id, step="vidéo Short")
                render.render_video(slideshow_id)
            s = db.get("slideshows", slideshow_id)
            warn = []
            if any(not sl.get("image_path") for sl in s["slides"] if sl["kind"] == "body"):
                warn.append("des slides n'ont pas d'image : ajoute des images de cet anime dans la bibliothèque")
            small = []
            for i, sl in enumerate(s["slides"]):
                r = db.one("SELECT width, height FROM images WHERE path=?", (sl.get("image_path"),)) if sl.get("image_path") else None
                if r and min(r["width"] or 0, r["height"] or 0) < 600:
                    small.append(i)
            if small:
                warn.append(f"image(s) basse résolution sur la/les slide(s) {', '.join(str(i + 1) for i in small)} : "
                            "floues en plein écran (la grille passe bien) ; remplace-les par des captures HD")
            low = [i for i, sl in enumerate(s["slides"]) if sl["kind"] == "body" and sl.get("confidence", 100) < 70]
            if low:
                warn.append(f"fait(s) incertain(s) sur la/les slide(s) {', '.join(str(i + 1) for i in low)} : vérifie")
            db.update("slideshows", slideshow_id, status="review", step=None, error="; ".join(warn) or None)
            return True
        except Exception as e:
            log.error("slideshow %s : %s", slideshow_id, e)
            log.debug(traceback.format_exc())
            db.update("slideshows", slideshow_id, status="failed", step=None, error=str(e)[:2000])
            return False


def pending() -> list[int]:
    return [r["id"] for r in db.query("SELECT id FROM slideshows WHERE status IN ('queued','drafting') ORDER BY id")]


def run_pending() -> None:
    for sid in pending():
        produce(sid)


def swap_image(slideshow_id: int, index: int, path: str) -> dict:
    s = db.get("slideshows", slideshow_id)
    sl = s["slides"][index]
    alts = [p for p in [sl.get("image_path"), *sl.get("alts", [])] if p and p != path]
    sl["image_path"], sl["alts"] = path, alts
    pair = [index]
    if index + 1 < len(s["slides"]) and s["slides"][index + 1].get("twin"):
        pair.append(index + 1)                          # aperçu changé → le wallpaper seul suit
    if sl.get("twin") and index > 0:
        pair.append(index - 1)
    for j in pair[1:]:
        s["slides"][j]["image_path"], s["slides"][j]["alts"] = path, alts
    db.update("slideshows", slideshow_id, slides=s["slides"])
    library.mark_used([path])
    for j in pair:
        render.render_slide(slideshow_id, j)
    return db.get("slideshows", slideshow_id)


def edit_slide(slideshow_id: int, index: int, **fields) -> dict:
    s = db.get("slideshows", slideshow_id)
    sl = s["slides"][index]
    for k in ("text", "label", "character", "scene"):
        if k in fields and fields[k] is not None:
            sl[k] = " ".join(str(fields[k]).split())
    if "text" in fields:
        sl["confidence"] = 100                      # relu par un humain
    db.update("slideshows", slideshow_id, slides=s["slides"])
    render.render_slide(slideshow_id, index)
    return db.get("slideshows", slideshow_id)


def delete_slide(slideshow_id: int, index: int) -> dict:
    """Retire une slide (jamais la couverture) puis renumérote et redessine tout (images, grille)."""
    s = db.get("slideshows", slideshow_id)
    slides = s["slides"] or []
    if not 0 < index < len(slides):
        raise ValueError("Cette slide ne peut pas être supprimée")
    del slides[index]
    db.update("slideshows", slideshow_id, slides=slides)
    render.render_all(slideshow_id)
    db.update("slideshows", slideshow_id, render_needed=1)
    return db.get("slideshows", slideshow_id)


def repick(slideshow_id: int, index: int) -> dict:
    """Nouvelle recherche d'image pour une slide (après modification du personnage ou de la scène)."""
    s = db.get("slideshows", slideshow_id)
    s["slides"][index]["image_path"] = None
    db.update("slideshows", slideshow_id, slides=s["slides"])
    choose_images(slideshow_id, [index])
    render.render_slide(slideshow_id, index)
    return db.get("slideshows", slideshow_id)


def max_items_ok(slideshow_id: int) -> bool:
    """Instagram : 10 éléments maximum par carrousel."""
    return len(db.get("slideshows", slideshow_id)["slides"]) <= 10 or not config.get()["slides"]["publish"][
        "instagram"].get("enabled")
