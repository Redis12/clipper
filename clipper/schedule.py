"""Créneaux de publication : valider un clip lui attribue le prochain créneau libre."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Iterator
from zoneinfo import ZoneInfo

from . import config, db

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
ACTIVE = ("approved", "uploaded")


def _tz(p: dict | None = None) -> ZoneInfo:
    return ZoneInfo((p or config.get()["publish"])["timezone"])


def _utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def slots(after: datetime, p: dict | None = None) -> Iterator[datetime]:
    """Créneaux (aware, fuseau de publication) strictement après `after`, dans l'ordre.
    `p` : section de publication à utiliser (par défaut celle des clips)."""
    p = p or config.get()["publish"]
    tz = _tz(p)
    times = sorted(time.fromisoformat(s) for s in p["slots"])
    allowed = {DAYS.index(d.lower()[:3]) for d in p["days"]}
    if not times or not allowed:
        raise ValueError("publish.slots et publish.days ne doivent pas être vides")
    d: date = after.astimezone(tz).date()
    for _ in range(3660):
        if d.weekday() in allowed:
            for t in times:
                dt = datetime.combine(d, t, tzinfo=tz)
                if dt > after:
                    yield dt
        d += timedelta(days=1)


def taken(exclude_clip: int | None = None) -> set[str]:
    rows = db.query(f"SELECT id, publish_at FROM clips WHERE publish_at IS NOT NULL AND status IN {ACTIVE}")
    return {r["publish_at"] for r in rows if r["id"] != exclude_clip}


def next_free(now: datetime | None = None, exclude_clip: int | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    lead = timedelta(hours=float(config.get()["publish"].get("min_lead_hours", 3)))
    busy = taken(exclude_clip)
    for dt in slots(now + lead):
        iso = _utc_iso(dt)
        if iso not in busy:
            return iso
    raise RuntimeError("Aucun créneau libre sur 10 ans : vérifie publish.slots / days")


def approve(clip_id: int) -> str:
    c = db.get_clip(clip_id)
    if c["status"] == "approved" and c["publish_at"]:
        return c["publish_at"]
    if c["status"] == "uploaded":
        raise ValueError("Clip déjà uploadé")
    at = next_free(exclude_clip=clip_id)
    db.update_clip(clip_id, status="approved", publish_at=at, approved_at=db.now(), error=None)
    return at


def unapprove(clip_id: int, to: str = "review") -> None:
    c = db.get_clip(clip_id)
    if c["status"] == "uploaded":
        raise ValueError("Clip déjà uploadé : gère-le dans YouTube Studio")
    db.update_clip(clip_id, status=to, publish_at=None)


def reschedule_overdue(now: datetime | None = None) -> list[int]:
    """Clips validés pas encore uploadés dont le créneau est passé (ou trop proche) : on les décale."""
    now = now or datetime.now(timezone.utc)
    # Il faut laisser à YouTube le temps de traiter la vidéo avant la sortie programmée.
    late = [c for c in db.query("SELECT * FROM clips WHERE status='approved' AND youtube_id IS NULL ORDER BY publish_at")
            if c["publish_at"] and parse(c["publish_at"]) < now + timedelta(minutes=30)]
    moved = []
    for c in late:
        db.update_clip(c["id"], publish_at=None)
        db.update_clip(c["id"], publish_at=next_free(now))
        moved.append(c["id"])
    return moved


def queue() -> list[dict]:
    return db.query("SELECT c.*, v.title AS source_title FROM clips c JOIN videos v ON v.id=c.video_id "
                    "WHERE c.status='approved' ORDER BY c.publish_at")


def due_for_upload(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    ahead = timedelta(days=float(config.get()["publish"].get("upload_ahead_days", 2)))
    return [c for c in queue() if c["publish_at"] and parse(c["publish_at"]) <= now + ahead]


def local(iso: str | None, tz: str | None = None) -> str:
    """Affichage court ; par défaut à l'heure de Bruxelles (celle de l'utilisateur)."""
    if not iso:
        return ""
    jours = ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."]
    dt = parse(iso).astimezone(ZoneInfo(tz) if tz else _tz())
    return f"{jours[dt.weekday()]} {dt:%d/%m %H:%M}"
