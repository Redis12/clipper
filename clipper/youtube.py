"""Upload YouTube : toujours en privé avec date programmée. Reprenable étape par étape."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from . import config, cut, db, quota, schedule, thumbs
from .util import log

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube"]
QUOTA_REASONS = {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "uploadLimitExceeded"}


def _token_path() -> Path:
    return config.data_dir() / "youtube_token.json"


def auth() -> str:
    """OAuth « application de bureau » : ouvre le navigateur une fois, stocke le jeton."""
    from google_auth_oauthlib.flow import InstalledAppFlow

    secrets = Path(config.secret("YOUTUBE_CLIENT_SECRETS"))
    if not secrets.is_absolute():
        secrets = config.ROOT / secrets
    if not secrets.exists():
        raise RuntimeError(
            f"Fichier OAuth introuvable : {secrets}\n"
            "Télécharge-le depuis Google Cloud Console (Identifiants → ID client OAuth « Application de bureau » "
            "→ Télécharger le JSON), renomme-le client_secret.json et mets-le à la racine du projet.")
    flow = InstalledAppFlow.from_client_secrets_file(str(secrets), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    _token_path().write_text(creds.to_json(), encoding="utf-8")
    return str(_token_path())


def service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    p = _token_path()
    if not p.exists():
        raise RuntimeError("Pas encore connecté à YouTube : lance `clipper auth`.")
    creds = Credentials.from_authorized_user_info(json.loads(p.read_text(encoding="utf-8")), SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            p.write_text(creds.to_json(), encoding="utf-8")
        else:
            raise RuntimeError("Jeton YouTube invalide : relance `clipper auth`.")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def _reason(err) -> str:
    try:
        return json.loads(err.content)["error"]["errors"][0]["reason"]
    except Exception:
        return ""


def _call(method: str, clip_id: int | None, fn):
    """Journalise l'appel dans quota_log AVANT de l'exécuter ; bloque le seau si YouTube dit quota épuisé."""
    from googleapiclient.errors import HttpError

    quota.record(method, clip_id)
    try:
        return fn()
    except HttpError as e:
        if _reason(e) in QUOTA_REASONS:
            quota.block(quota.cost(method)[0])
            raise quota.QuotaBlocked(f"{method} : YouTube a répondu {_reason(e)}") from e
        raise


def playlist_for(video: dict) -> str:
    p = config.get()["publish"]
    return (p.get("playlist_by_source_channel") or {}).get(video.get("channel_id") or "", "") or p.get("playlist_id") or ""


def video_body(clip: dict, publish_at: str) -> dict:
    p = config.get()["publish"]
    titles = clip["titles"] or [clip["topic"]]
    title = titles[min(clip["title_idx"] or 0, len(titles) - 1)]
    body = {
        "snippet": {
            "title": title[:100],
            "description": clip["description"] or "",
            "tags": clip["tags"] or [],
            "categoryId": str(p.get("category_id", "27")),
            "defaultLanguage": p.get("default_language", "fr"),
            "defaultAudioLanguage": p.get("default_language", "fr"),
        },
        "status": {
            "privacyStatus": "private",
            "publishAt": datetime.fromisoformat(publish_at).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "selfDeclaredMadeForKids": bool(p.get("made_for_kids", False)),
            "embeddable": True,
        },
    }
    # Garde-fou : rien ne part jamais en public directement.
    assert body["status"]["privacyStatus"] == "private"
    return body


def upload(clip_id: int) -> str:
    from googleapiclient.http import MediaFileUpload

    c = db.get_clip(clip_id)
    v = db.get_video(c["video_id"])
    playlist = playlist_for(v)
    yt = service()

    if not c["youtube_id"]:
        why = quota.affordable(quota.per_clip_methods(bool(playlist)))
        if why:
            raise quota.QuotaBlocked(why)
        if quota.uploads_today() >= int(config.get()["publish"].get("max_uploads_per_day", 10**6)):
            raise quota.QuotaBlocked("plafond max_uploads_per_day atteint")
        clip_path = cut.render(clip_id)          # re-rend si ajusté depuis
        if not c["thumb_path"] or not Path(c["thumb_path"]).exists():
            thumbs.make(clip_id)
        body = video_body(db.get_clip(clip_id), c["publish_at"])
        media = MediaFileUpload(str(clip_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
        req = yt.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)

        def go():
            resp = None
            while resp is None:
                status, resp = req.next_chunk(num_retries=5)
                if status:
                    log.info("clip %s : upload %d %%", clip_id, int(status.progress() * 100))
            return resp

        resp = _call("videos.insert", clip_id, go)
        db.update_clip(clip_id, youtube_id=resp["id"], error=None)
        log.info("clip %s : vidéo %s créée (privée, sortie %s)", clip_id, resp["id"], schedule.local(c["publish_at"]))
        c = db.get_clip(clip_id)

    if not c["thumb_done"]:
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload as MFU
        try:
            _call("thumbnails.set", clip_id, lambda: yt.thumbnails().set(
                videoId=c["youtube_id"], media_body=MFU(c["thumb_path"], mimetype="image/jpeg")).execute())
            db.update_clip(clip_id, thumb_done=1)
        except HttpError as e:  # ex. chaîne non vérifiée : on n'empêche pas la suite
            db.update_clip(clip_id, thumb_done=-1, error=f"Miniature refusée par YouTube : {_reason(e) or e}")

    if playlist and not c["playlist_done"]:
        _call("playlistItems.insert", clip_id, lambda: yt.playlistItems().insert(part="snippet", body={
            "snippet": {"playlistId": playlist, "resourceId": {"kind": "youtube#video", "videoId": c["youtube_id"]}}
        }).execute())
        db.update_clip(clip_id, playlist_done=1)

    db.update_clip(clip_id, status="uploaded", uploaded_at=db.now())
    return c["youtube_id"]


def list_playlists() -> list[dict]:
    yt = service()
    out, token = [], None
    while True:
        r = _call("playlists.list", None, lambda: yt.playlists().list(
            part="snippet,status", mine=True, maxResults=50, pageToken=token).execute())
        out += [{"id": p["id"], "title": p["snippet"]["title"], "privacy": p["status"]["privacyStatus"]}
                for p in r.get("items", [])]
        token = r.get("nextPageToken")
        if not token:
            return out


def publish(dry_run: bool = False) -> list[str]:
    """Uploade les clips dont la sortie approche, dans l'ordre, tant que le quota le permet."""
    report = []
    moved = schedule.reschedule_overdue()
    if moved:
        report.append(f"{len(moved)} clip(s) en retard décalé(s) au prochain créneau libre")
    due = schedule.due_for_upload()
    if not due:
        report.append("Rien à uploader maintenant.")
    for c in due:
        label = f"#{c['id']} « {(c['titles'] or [c['topic']])[c['title_idx'] or 0]} » → {schedule.local(c['publish_at'])}"
        if dry_run:
            report.append(f"[simulation] {label}")
            continue
        try:
            yid = upload(c["id"])
            report.append(f"OK {label} : https://youtu.be/{yid}")
        except quota.QuotaBlocked as e:
            report.append(f"Arrêt : {e}. La file est conservée, reprise au prochain passage.")
            break
        except Exception as e:
            db.update_clip(c["id"], error=str(e)[:2000])
            report.append(f"ÉCHEC {label} : {e}")
    s = quota.summary()
    report.append("Quota restant : " + ", ".join(f"{b} {d['remaining']}/{d['limit']}" for b, d in s["buckets"].items())
                  + f" ; encore {s['clips_left_today']} clip(s) possible(s) aujourd'hui (jour PT {s['pt_day']}).")
    return report
