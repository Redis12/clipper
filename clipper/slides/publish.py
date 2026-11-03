"""Planification et publication multi-plateforme d'un slideshow (YouTube Shorts, Instagram, TikTok).

YouTube accepte une date programmée (upload privé + publishAt) ; Instagram et TikTok non : l'outil publie
lui-même à l'heure prévue. Une plateforme non configurée produit un « pack » à poster à la main.
"""
from __future__ import annotations

import io
import json
import secrets
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from .. import config, db, quota, schedule, youtube
from ..util import log
from . import render

PLATFORMS = ("youtube", "instagram", "tiktok")


def pcfg() -> dict:
    return config.get()["slides"]["publish"]


def is_auto(platform: str) -> bool:
    p = pcfg()
    if platform == "youtube":
        # « auto: false » tant que Clipper n'est pas relié à la bonne chaîne (sinon upload sur la mauvaise).
        return bool(p.get("youtube", {}).get("auto", True)) and (config.data_dir() / "youtube_token.json").exists()
    ok = bool(p.get(platform, {}).get("enabled")) and p.get("hosting", {}).get("kind", "none") != "none"
    if platform == "tiktok":
        from . import tiktok
        ok = ok and tiktok.connected()
    return ok


# --- créneaux -----------------------------------------------------------------------

def taken(exclude: int | None = None) -> set[str]:
    rows = db.query("SELECT id, publish_at FROM slideshows WHERE publish_at IS NOT NULL "
                    "AND status IN ('approved','published')")
    return {r["publish_at"] for r in rows if r["id"] != exclude}


def next_free(now: datetime | None = None, exclude: int | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    p = pcfg()
    busy = taken(exclude)
    for dt in schedule.slots(now + timedelta(hours=float(p.get("min_lead_hours", 2))), p):
        iso = dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()
        if iso not in busy:
            return iso
    raise RuntimeError("Aucun créneau libre : vérifie slides.publish.slots / days")


def approve(slideshow_id: int) -> str:
    s = db.get("slideshows", slideshow_id)
    if s["status"] == "approved" and s["publish_at"]:
        return s["publish_at"]
    if s["status"] not in ("review", "approved"):
        raise ValueError("Ce slideshow n'est pas prêt pour la validation")
    at = next_free(exclude=slideshow_id)
    db.update("slideshows", slideshow_id, status="approved", publish_at=at, approved_at=db.now(), error=None)
    for platform in pcfg().get("platforms", PLATFORMS):
        if platform not in PLATFORMS or (platform == "youtube" and not render.has_video(slideshow_id)):
            continue                     # YouTube seulement si tu as généré la vidéo
        row = db.one("SELECT * FROM posts WHERE slideshow_id=? AND platform=?", (slideshow_id, platform))
        mode = "auto" if is_auto(platform) else "manual"
        if row is None:
            db.insert("posts", slideshow_id=slideshow_id, platform=platform, mode=mode, publish_at=at,
                      status="scheduled")
        elif row["status"] != "done":
            db.update("posts", row["id"], mode=mode, publish_at=at, status="scheduled", error=None)
    return at


def make_video(slideshow_id: int) -> None:
    """Vidéo sur demande ; si le slideshow est déjà programmé, ajoute aussi sa publication YouTube."""
    render.render_video(slideshow_id, force=True)
    s = db.get("slideshows", slideshow_id)
    if s["status"] == "approved" and "youtube" in pcfg().get("platforms", PLATFORMS) and not db.one(
            "SELECT 1 AS x FROM posts WHERE slideshow_id=? AND platform='youtube'", (slideshow_id,)):
        db.insert("posts", slideshow_id=slideshow_id, platform="youtube",
                  mode="auto" if is_auto("youtube") else "manual", publish_at=s["publish_at"], status="scheduled")


def unapprove(slideshow_id: int, to: str = "review") -> None:
    if db.one("SELECT 1 AS x FROM posts WHERE slideshow_id=? AND status='done'", (slideshow_id,)):
        raise ValueError("Déjà publié sur au moins une plateforme : retire-le depuis la plateforme")
    db.execute("DELETE FROM posts WHERE slideshow_id=?", (slideshow_id,))
    db.update("slideshows", slideshow_id, status=to, publish_at=None)


def mark_manual_done(post_id: int, url: str = "") -> None:
    db.update("posts", post_id, status="done", url=url or None)
    _maybe_published(db.get("posts", post_id)["slideshow_id"])


def _maybe_published(slideshow_id: int) -> None:
    left = db.one("SELECT COUNT(*) AS n FROM posts WHERE slideshow_id=? AND status NOT IN ('done','cancelled')",
                  (slideshow_id,))["n"]
    if left == 0:
        db.update("slideshows", slideshow_id, status="published")


# --- textes -------------------------------------------------------------------------

def caption(s: dict) -> str:
    tags = " ".join(f"#{h}" for h in (s["hashtags"] or []))
    return f"{s['caption']}\n\n{tags}".strip()


def youtube_body(s: dict) -> dict:
    y = pcfg().get("youtube", {})
    desc = (s["yt_description"] or s["caption"] or "").strip()
    tags = s["hashtags"] or []
    desc = f"{desc}\n\n{' '.join('#' + t for t in tags[:5])} #shorts".strip()
    body = {
        "snippet": {"title": (s["yt_title"] or s["topic"])[:100], "description": desc[:4900], "tags": tags,
                    "categoryId": str(y.get("category_id", "24")), "defaultLanguage": "en",
                    "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "private",
                   "publishAt": datetime.fromisoformat(s["publish_at"]).astimezone(timezone.utc)
                   .strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "selfDeclaredMadeForKids": False},
    }
    assert body["status"]["privacyStatus"] == "private"      # jamais public directement
    return body


# --- packs manuels ------------------------------------------------------------------

def export_zip(slideshow_id: int, platform: str) -> bytes:
    s = db.get("slideshows", slideshow_id)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        if platform == "youtube":
            z.write(render.render_video(slideshow_id), "short.mp4")
            z.writestr("title.txt", s["yt_title"] or s["topic"])
            z.writestr("description.txt", youtube_body({**s, "publish_at": s["publish_at"] or db.now()})
                       ["snippet"]["description"])
        else:
            fmt = "portrait" if platform == "instagram" else "vertical"
            imgs = render.slide_paths(slideshow_id, fmt)
            if len(imgs) != len(s["slides"]):
                render.render_all(slideshow_id)
                imgs = render.slide_paths(slideshow_id, fmt)
            grid = render.out_dir(slideshow_id) / f"grid_{fmt}.jpg"
            if grid.exists():
                z.write(grid, "grille_image_unique.jpg")
            if platform == "instagram" and len(imgs) > 10:
                # Instagram : 10 images max par carrousel → 2 posts (la couverture ouvre les deux).
                cut_at = (len(imgs) + 2) // 2
                for p in imgs[:cut_at]:
                    z.write(p, f"post1/{p.name}")
                for p in [imgs[0], *imgs[cut_at:]]:
                    z.write(p, f"post2/{p.name}")
                z.writestr("post1/caption.txt", caption(s) + "\n\nPart 2 on my profile 👀")
                z.writestr("post2/caption.txt", caption(s) + "\n\nPart 1 on my profile 👀")
                z.writestr("LISEZ-MOI.txt", "Instagram limite un carrousel à 10 images : poste post1 puis post2.")
            else:
                for p in imgs:
                    z.write(p, p.name)
                z.writestr("caption.txt", caption(s))
    return buf.getvalue()


# --- hébergement public (requis par Instagram et TikTok) ---------------------------------

def host_kind() -> str:
    return pcfg().get("hosting", {}).get("kind", "none")


def _github_put(rel: str, data: bytes, message: str) -> str:
    """Dépose un fichier dans le dépôt GitHub Pages (API Contents). Rend son URL publique."""
    import base64

    h = pcfg()["hosting"]
    repo, branch = h["repo"], h.get("branch", "main")
    api = f"https://api.github.com/repos/{repo}/contents/{rel}"
    headers = {"Authorization": f"Bearer {config.secret('GITHUB_TOKEN')}",
               "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    with httpx.Client(timeout=60, headers=headers) as c:
        old = c.get(api, params={"ref": branch})
        body = {"message": message, "branch": branch, "content": base64.b64encode(data).decode()}
        if old.status_code == 200:
            body["sha"] = old.json()["sha"]
        r = c.put(api, json=body)
        if r.status_code >= 400:
            raise RuntimeError(f"GitHub {r.status_code} : {r.text[:300]}")
    return f"{h['public_base_url'].rstrip('/')}/{rel}"


def wait_public(urls: list[str], timeout_s: float = 300, every: float = 10) -> None:
    """GitHub Pages met ~1 min à publier : on attend que chaque image réponde 200 (sans redirection)."""
    import time

    end = time.time() + timeout_s
    left = list(urls)
    with httpx.Client(timeout=20, follow_redirects=False) as c:
        while left:
            left = [u for u in left if c.head(u).status_code != 200]
            if not left:
                return
            if time.time() > end:
                raise RuntimeError(f"Images pas encore en ligne après {int(timeout_s)} s : {left[0]}")
            time.sleep(every)


def host_file(path: Path, rel: str | None = None) -> str:
    """Met un fichier quelconque en ligne (ex. fichier de vérification TikTok), à la racine du site."""
    if host_kind() != "github":
        raise RuntimeError("host_file : seulement avec hosting.kind = github")
    return _github_put(rel or path.name, path.read_bytes(), f"clipper: {path.name}")


def host_images(slideshow_id: int, fmt: str) -> list[str]:
    h = pcfg().get("hosting", {})
    kind = h.get("kind", "none")
    paths = render.slide_paths(slideshow_id, fmt)
    if kind == "github":
        tag = secrets.token_hex(4)            # nom imprévisible + jamais en cache
        urls = [_github_put(f"s/{slideshow_id}-{tag}/{p.name}", p.read_bytes(), f"clipper: slideshow {slideshow_id}")
                for p in paths]
        wait_public(urls)
        return urls
    if kind != "s3":
        raise RuntimeError("Hébergement d'images non configuré (slides.publish.hosting)")
    try:
        import boto3
    except ImportError as e:
        raise RuntimeError("boto3 manquant : pip install boto3") from e
    s3 = boto3.client("s3", endpoint_url=h.get("endpoint_url") or None,
                      aws_access_key_id=config.secret("S3_ACCESS_KEY_ID"),
                      aws_secret_access_key=config.secret("S3_SECRET_ACCESS_KEY"))
    urls = []
    for p in paths:
        key = f"slides/{slideshow_id}/{fmt}/{p.name}"
        s3.upload_file(str(p), h["bucket"], key, ExtraArgs={"ContentType": "image/jpeg"})
        urls.append(f"{h['public_base_url'].rstrip('/')}/{key}")
    return urls


def publish_instagram(s: dict) -> tuple[str, str]:
    """Carrousel via l'API Instagram (connexion Instagram). Rend (media_id, permalink)."""
    import time

    base = pcfg()["instagram"].get("graph_base", "https://graph.instagram.com/v23.0").rstrip("/")
    uid, token = config.secret("IG_USER_ID"), config.secret("IG_ACCESS_TOKEN")
    urls = host_images(s["id"], "portrait")[:10]
    with httpx.Client(timeout=60) as c:
        def post(path, **data):
            r = c.post(f"{base}/{path}", data={**data, "access_token": token})
            if r.status_code >= 400:
                raise RuntimeError(f"Instagram {r.status_code} : {r.text[:400]}")
            return r.json()

        children = [post(f"{uid}/media", image_url=u, is_carousel_item="true")["id"] for u in urls]
        container = post(f"{uid}/media", media_type="CAROUSEL", children=",".join(children), caption=caption(s))["id"]
        for _ in range(30):
            st = c.get(f"{base}/{container}", params={"fields": "status_code", "access_token": token}).json()
            if st.get("status_code") == "FINISHED":
                break
            if st.get("status_code") == "ERROR":
                raise RuntimeError(f"Instagram : conteneur en erreur {st}")
            time.sleep(4)
        media_id = post(f"{uid}/media_publish", creation_id=container)["id"]
        link = c.get(f"{base}/{media_id}", params={"fields": "permalink", "access_token": token}).json()
    return media_id, link.get("permalink", "")


def publish_tiktok(s: dict) -> tuple[str, str]:
    """Mode inbox : rend (publish_id, "") ; le post est fini dans l'appli TikTok (notification → son → publier)."""
    from . import tiktok
    urls = host_images(s["id"], "vertical")[:35]
    return tiktok.send(s["yt_title"] or s["topic"], caption(s), urls), ""


def publish_youtube(s: dict) -> tuple[str, str]:
    from googleapiclient.http import MediaFileUpload

    y = pcfg().get("youtube", {})
    methods = ["videos.insert"] + (["playlistItems.insert"] if y.get("playlist_id") else [])
    why = quota.affordable(methods)
    if why:
        raise quota.QuotaBlocked(why)
    if quota.uploads_today() >= int(config.get()["publish"].get("max_uploads_per_day", 10**6)):
        raise quota.QuotaBlocked("plafond max_uploads_per_day atteint")
    path = render.render_video(s["id"])
    yt = youtube.service()
    media = MediaFileUpload(str(path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=youtube_body(s), media_body=media, notifySubscribers=True)

    def go():
        resp = None
        while resp is None:
            _, resp = req.next_chunk(num_retries=5)
        return resp

    vid = youtube._call("videos.insert", None, go)["id"]
    if y.get("playlist_id"):
        try:
            youtube._call("playlistItems.insert", None, lambda: yt.playlistItems().insert(part="snippet", body={
                "snippet": {"playlistId": y["playlist_id"], "resourceId": {"kind": "youtube#video", "videoId": vid}}
            }).execute())
        except quota.QuotaBlocked:
            raise
        except Exception as e:  # la vidéo est en ligne ; la playlist n'est pas bloquante
            log.warning("playlist : %s", e)
    return vid, f"https://youtube.com/shorts/{vid}"


PUBLISHERS = {"youtube": publish_youtube, "instagram": publish_instagram, "tiktok": publish_tiktok}


def due(now: datetime | None = None) -> list[dict]:
    """Posts automatiques à faire maintenant : YouTube en avance (programmé), les autres à l'heure."""
    now = now or datetime.now(timezone.utc)
    ahead = timedelta(days=float(config.get()["publish"].get("upload_ahead_days", 2)))
    rows = db.query("SELECT p.*, s.publish_at AS s_at FROM posts p JOIN slideshows s ON s.id=p.slideshow_id "
                    "WHERE p.status IN ('scheduled','failed') AND p.mode='auto' AND p.attempts < 5 "
                    "ORDER BY p.publish_at")
    out = []
    for r in rows:
        at = datetime.fromisoformat(r["publish_at"])
        early = timedelta(0)
        if r["platform"] == "tiktok" and pcfg()["tiktok"].get("mode", "inbox") != "direct":
            early = timedelta(minutes=float(pcfg()["tiktok"].get("inbox_ahead_minutes", 30)))
        if (r["platform"] == "youtube" and at <= now + ahead) or (r["platform"] != "youtube" and at <= now + early):
            out.append(r)
    return out


def reschedule_youtube_overdue(now: datetime | None = None) -> int:
    """Un Short pas encore uploadé dont l'heure est passée : on décale tout le slideshow au prochain créneau."""
    now = now or datetime.now(timezone.utc)
    late = db.query("SELECT DISTINCT p.slideshow_id FROM posts p WHERE p.platform='youtube' AND p.mode='auto' "
                    "AND p.status IN ('scheduled','failed') AND p.publish_at < ?",
                    ((now + timedelta(minutes=30)).isoformat(),))
    for r in late:
        if db.one("SELECT 1 AS x FROM posts WHERE slideshow_id=? AND status='done'", (r["slideshow_id"],)):
            continue                                    # déjà sorti ailleurs : on garde l'heure
        at = next_free(now, exclude=r["slideshow_id"])
        db.update("slideshows", r["slideshow_id"], publish_at=at)
        db.execute("UPDATE posts SET publish_at=? WHERE slideshow_id=? AND status!='done'", (at, r["slideshow_id"]))
    return len(late)


def run(dry_run: bool = False) -> list[str]:
    report = []
    n = reschedule_youtube_overdue()
    if n:
        report.append(f"Slideshows : {n} Short(s) en retard décalé(s)")
    for p in due():
        s = db.get("slideshows", p["slideshow_id"])
        label = f"slideshow #{s['id']} « {s['topic']} » → {p['platform']}"
        if dry_run:
            report.append(f"[simulation] {label}")
            continue
        try:
            db.update("posts", p["id"], attempts=p["attempts"] + 1)
            remote, url = PUBLISHERS[p["platform"]](s)
            db.update("posts", p["id"], status="done", remote_id=remote, url=url or None, error=None)
            _maybe_published(s["id"])
            if p["platform"] == "tiktok" and pcfg()["tiktok"].get("mode", "inbox") != "direct":
                report.append(f"OK {label} : dans ta boîte TikTok → ouvre la notification, ajoute un son, publie")
            else:
                report.append(f"OK {label} {url}")
        except quota.QuotaBlocked as e:
            report.append(f"Arrêt YouTube : {e}. Reprise au prochain passage.")
            if p["platform"] == "youtube":
                db.update("posts", p["id"], attempts=p["attempts"])     # ne compte pas comme un échec
        except Exception as e:
            db.update("posts", p["id"], status="failed", error=str(e)[:2000])
            report.append(f"ÉCHEC {label} : {e}")
    manual = db.query("SELECT COUNT(*) AS n FROM posts WHERE mode='manual' AND status='scheduled' AND publish_at <= ?",
                      (datetime.now(timezone.utc).isoformat(),))[0]["n"]
    if manual:
        report.append(f"{manual} post(s) à publier à la main (packs prêts dans la file des slideshows)")
    return report


def queue() -> list[dict]:
    return db.query("SELECT p.*, s.topic, s.anime FROM posts p JOIN slideshows s ON s.id=p.slideshow_id "
                    "WHERE p.status != 'cancelled' ORDER BY p.publish_at, p.slideshow_id, p.platform")
