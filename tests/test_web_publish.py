"""Revue (FastAPI) et publication avec un faux client YouTube."""
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from clipper import db, quota, schedule, youtube


@pytest.fixture()
def client(video_in_db):
    from clipper.web import app as appmod
    with TestClient(appmod.app) as c:
        yield c


@pytest.fixture()
def ready_clip(video_in_db):
    return db.insert_clip(video_in_db, rank=1, start=20.0, end=200.0, sel_start=20.0, sel_end=200.0,
                          topic="Sujet", score=82, reason="Bonne chute", status="review",
                          titles=["Titre A", "Titre B", "Titre C"], title_idx=0,
                          description="Corps.\n\n▶ Extrait de « Vidéo test », à partir de 0:20 :\nhttps://youtu.be/abcdefghijk?t=20",
                          tags=[f"t{i}" for i in range(10)], thumb_text="Trois mots ici")


def test_pages_render(client, ready_clip, video_in_db):
    assert "Vidéo test" in client.get("/").text
    r = client.get(f"/video/{video_in_db}")
    assert r.status_code == 200 and "Titre A" in r.text
    assert client.get("/queue").status_code == 200
    # Lecture avec Range (nécessaire pour le lecteur)
    r = client.get(f"/media/proxy/{video_in_db}.mp4", headers={"Range": "bytes=0-99"})
    assert r.status_code == 206 and len(r.content) == 100


def test_review_actions(client, ready_clip):
    r = client.post(f"/api/clip/{ready_clip}/adjust", json={"edge": "start", "delta": 1}).json()
    assert r["start"] == 21.0 and r["render_needed"] == 1
    assert "?t=21" in r["description"] and "à partir de 0:21" in r["description"]
    r = client.post(f"/api/clip/{ready_clip}/adjust", json={"edge": "restore"}).json()
    assert r["start"] == 20.0
    r = client.post(f"/api/clip/{ready_clip}/meta", json={"titles": ["Nouveau <titre>", "B", "C"], "title_idx": 2,
                                                          "tags": "un, deux,  ,trois"}).json()
    assert r["titles"][0] == "Nouveau titre" and r["title_idx"] == 2 and r["tags"] == ["un", "deux", "trois"]
    r = client.post(f"/api/clip/{ready_clip}/approve").json()
    assert r["status"] == "approved" and r["publish_at"]
    assert client.post(f"/api/clip/{ready_clip}/reject").json()["status"] == "rejected"
    assert client.post(f"/api/clip/{ready_clip}/reset").json()["status"] == "review"


def test_approve_refuses_bad_duration(client, ready_clip):
    db.update_clip(ready_clip, end=100.0)
    r = client.post(f"/api/clip/{ready_clip}/approve")
    assert r.status_code == 400 and "hors limites" in r.json()["error"]


def test_thumbnail_click_recomposes(client, ready_clip):
    r = client.post(f"/api/clip/{ready_clip}/frames").json()
    assert len(r["frames"]) == 10
    r = client.post(f"/api/clip/{ready_clip}/meta", json={"frame_idx": 7}).json()
    assert r["frame_idx"] == 7 and r["has_thumb"]
    assert client.get(f"/media/thumb/{ready_clip}.jpg").headers["content-type"] == "image/jpeg"


# --- publication --------------------------------------------------------------

class FakeYT:
    """Imite le client googleapiclient pour videos/thumbnails/playlistItems."""

    def __init__(self, fail_on=None):
        self.calls, self.fail_on, self.n = [], fail_on, 0

    def _req(self, name, result, **kw):
        self.calls.append((name, kw))
        if self.fail_on == name:
            from googleapiclient.errors import HttpError
            raise HttpError(SimpleNamespace(status=403, reason="Forbidden"),
                            b'{"error":{"errors":[{"reason":"quotaExceeded"}]}}')
        return result

    def videos(self):
        yt = self

        class V:
            def insert(self, **kw):
                yt.n += 1
                vid = f"yt{yt.n:09d}"

                class R:
                    def next_chunk(self, num_retries=0):
                        return None, yt._req("videos.insert", {"id": vid}, **kw)
                return R()
        return V()

    def thumbnails(self):
        yt = self
        return SimpleNamespace(set=lambda **kw: SimpleNamespace(execute=lambda: yt._req("thumbnails.set", {}, **kw)))

    def playlistItems(self):
        yt = self
        return SimpleNamespace(insert=lambda **kw: SimpleNamespace(execute=lambda: yt._req("playlistItems.insert", {}, **kw)))


def _approve_n(video_id, n):
    ids = []
    for i in range(n):
        cid = db.insert_clip(video_id, start=10.0 + i, end=140.0 + i, topic=f"c{i}", score=50, reason="",
                             status="review", titles=[f"Titre {i}"], title_idx=0, description="d",
                             tags=["a"], thumb_text="un deux trois")
        schedule.approve(cid)
        ids.append(cid)
    return ids


def test_publish_private_scheduled_with_playlist(video_in_db, cfg, monkeypatch):
    cfg["publish"]["playlist_id"] = "PLtest"
    cfg["publish"]["upload_ahead_days"] = 30
    fake = FakeYT()
    monkeypatch.setattr(youtube, "service", lambda: fake)
    ids = _approve_n(video_in_db, 3)
    report = youtube.publish()
    assert all(db.get_clip(i)["status"] == "uploaded" for i in ids), report
    inserts = [kw for name, kw in fake.calls if name == "videos.insert"]
    assert len(inserts) == 3
    for kw in inserts:
        assert kw["body"]["status"]["privacyStatus"] == "private"
        assert kw["body"]["status"]["publishAt"].endswith("Z")
    assert [n for n, _ in fake.calls].count("playlistItems.insert") == 3
    s = quota.summary()
    assert s["buckets"]["uploads"]["used"] == 3 and s["buckets"]["default"]["used"] == 300
    assert db.get_clip(ids[0])["render_needed"] == 0     # rendu fait juste avant l'upload


def test_publish_respects_daily_cap_and_keeps_queue(video_in_db, cfg, monkeypatch):
    cfg["publish"]["upload_ahead_days"] = 30
    cfg["publish"]["max_uploads_per_day"] = 2
    monkeypatch.setattr(youtube, "service", lambda: FakeYT())
    monkeypatch.setattr("clipper.cut.render", lambda cid, force=False: __import__("pathlib").Path(db.get_video(video_in_db)["source_path"]))
    monkeypatch.setattr("clipper.thumbs.make", lambda cid, refresh_frames=False: None)
    for cid in _approve_n(video_in_db, 4):
        db.update_clip(cid, thumb_path=db.get_video(video_in_db)["source_path"])
    report = youtube.publish()
    statuses = [c["status"] for c in db.query("SELECT status FROM clips ORDER BY publish_at")]
    assert statuses == ["uploaded", "uploaded", "approved", "approved"]
    assert any("Arrêt" in r and "plafond" in r for r in report)


def test_quota_exceeded_blocks_and_resumes(video_in_db, cfg, monkeypatch):
    cfg["publish"]["upload_ahead_days"] = 30
    fake = FakeYT(fail_on="thumbnails.set")
    monkeypatch.setattr(youtube, "service", lambda: fake)
    monkeypatch.setattr("clipper.cut.render", lambda cid, force=False: __import__("pathlib").Path(db.get_video(video_in_db)["source_path"]))
    monkeypatch.setattr("clipper.thumbs.make", lambda cid, refresh_frames=False: None)
    (cid,) = _approve_n(video_in_db, 1)
    db.update_clip(cid, thumb_path=db.get_video(video_in_db)["source_path"])
    report = youtube.publish()
    c = db.get_clip(cid)
    assert c["youtube_id"] and c["status"] == "approved" and not c["thumb_done"]   # vidéo créée, finitions en attente
    assert quota.blocked("default") and any("Arrêt" in r for r in report)
    # Le lendemain (bloc levé) : on reprend sans re-uploader la vidéo
    db.execute("DELETE FROM quota_block")
    fake.fail_on = None
    youtube.publish()
    c = db.get_clip(cid)
    assert c["status"] == "uploaded" and c["thumb_done"] == 1
    assert [n for n, _ in fake.calls].count("videos.insert") == 1


def test_add_form(client, monkeypatch):
    """Le bouton « Ajouter » : formulaire POST, puis redirection vers l'accueil."""
    from clipper.web import app as appmod
    monkeypatch.setattr(appmod.ingest, "add", lambda url, **kw: (["zzzzzzzzzzz"], []))
    monkeypatch.setattr(appmod, "enqueue", lambda label, fn: None)
    r = client.post("/add", data={"url": "https://www.youtube.com/watch?v=zzzzzzzzzzz"}, follow_redirects=False)
    assert r.status_code == 303 and "added=1" in r.headers["location"]
    monkeypatch.setattr(appmod.ingest, "add", lambda url, **kw: (_ for _ in ()).throw(ValueError("mauvaise URL")))
    r = client.post("/add", data={"url": "https://exemple.com"})
    assert r.status_code == 400 and "mauvaise URL" in r.text
