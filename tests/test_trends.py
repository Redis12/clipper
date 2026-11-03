"""Veille des tendances : YouTube (API simulée), captures (vision simulée), analyse, idées inspirées."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from PIL import Image

from clipper import db, quota
from clipper.slides import ideas, trends


class FakeYTSearch:
    def __init__(self):
        self.calls = []

    def search(self):
        me = self

        def lst(**kw):
            me.calls.append(("search", kw))
            q = kw["q"]
            return SimpleNamespace(execute=lambda: {"items": [{"id": {"videoId": f"{abs(hash(q)) % 10**6:06d}a{i}"}} for i in range(3)]})
        return SimpleNamespace(list=lst)

    def videos(self):
        me = self

        def lst(**kw):
            me.calls.append(("videos", kw))
            ids = kw["id"].split(",")
            now = datetime.now(timezone.utc)
            items = []
            for k, vid in enumerate(ids):
                items.append({"id": vid, "snippet": {"title": f"Top 5 strongest {vid}", "description": "#anime",
                                                     "channelTitle": "c", "publishedAt": (now - timedelta(days=2)).isoformat()},
                              "statistics": {"viewCount": str([500000, 30000, 5000][k % 3]), "likeCount": "1000",
                                             "commentCount": "10"},
                              "contentDetails": {"duration": ["PT45S", "PT59S", "PT40S"][k % 3] if k != 1 else "PT4M"}})
            return SimpleNamespace(execute=lambda: {"items": items})
        return SimpleNamespace(list=lst)


def test_parse_count_and_score():
    assert trends.parse_count("1.2M") == 1_200_000 and trends.parse_count("845K") == 845_000
    assert trends.parse_count("12 345") == 12345 and trends.parse_count("1,2M") == 1_200_000
    assert trends.parse_count("abc") is None and trends.parse_count(None) is None
    now = datetime.now(timezone.utc)
    assert trends.score(100000, 0, (now - timedelta(days=1)).isoformat()) > trends.score(100000, 0, (now - timedelta(days=10)).isoformat())


def test_fetch_youtube_filters_and_counts_quota(cfg, monkeypatch):
    fake = FakeYTSearch()
    monkeypatch.setattr("clipper.youtube.service", lambda: fake)
    cfg["slides"]["trends"]["youtube"]["queries_per_run"] = 2
    n = trends.fetch_youtube()
    rows = db.query("SELECT * FROM trends")
    assert n == len(rows) == 2                         # par recherche : 1 garde (500k, 45 s) ; 4 min et 5k vues écartés
    assert all(r["views"] == 500000 and r["url"].startswith("https://youtube.com/shorts/") for r in rows)
    assert quota.used("search") == 2 and quota.used("default") == 2
    s = [kw for n_, kw in fake.calls if n_ == "search"][0]
    assert s["videoDuration"] == "short" and s["order"] == "viewCount"
    assert trends.fetch_youtube() == 0                 # pas de doublon au 2e passage


def test_analyze_pending_and_top(cfg, monkeypatch):
    a = db.insert("trends", platform="youtube", origin="api", external_id="yt:a", title="Top 5 JJK villains", views=900000, score=50.0)
    b = db.insert("trends", platform="youtube", origin="api", external_id="yt:b", title="Gojo AMV edit", views=2000000, score=99.0)
    monkeypatch.setattr("clipper.llm.structured", lambda **kw: {"items": [
        {"id": a, "anime": "Jujutsu Kaisen", "format": "ranking", "topic": "Top villains", "hook": "Top N — #1 …",
         "slideshow_like": True, "why": "debate"},
        {"id": b, "anime": "Jujutsu Kaisen", "format": "edit", "topic": "AMV", "slideshow_like": False}]})
    assert trends.analyze_pending() == 2
    assert db.get("trends", a)["status"] == "analyzed" and db.get("trends", b)["status"] == "irrelevant"
    assert [t["id"] for t in trends.top()] == [a]
    assert "ranking" in trends.as_prompt(trends.top()) and "900,000 views" in trends.as_prompt(trends.top())


def test_screenshot_import(cfg, monkeypatch, tmp_path):
    shot = tmp_path / "tt.png"
    Image.new("RGB", (600, 1200), (30, 30, 30)).save(shot)
    seen = []

    def fake(**kw):
        seen.append(kw)
        return {"is_post": True, "platform": "tiktok", "slideshow_like": True, "anime": "Naruto", "format": "ranking",
                "topic": "Saddest Naruto deaths", "hook": "THIS ONE STILL HURTS", "views": "1.2M", "likes": "88.4K",
                "comments": "1,203", "why": "emotional"}
    monkeypatch.setattr("clipper.llm.structured", fake)
    tid = trends.import_screenshot(shot, "IMG_0001.png")
    t = db.get("trends", tid)
    assert t["status"] == "analyzed" and t["platform"] == "tiktok" and t["views"] == 1_200_000 and t["likes"] == 88_400
    assert t["comments"] == 1203 and t["image_path"].endswith(f"{tid}.png")
    assert seen[0]["user"][0]["type"] == "image"


def test_ideas_use_trends_and_record_inspiration(cfg, monkeypatch):
    tid = db.insert("trends", platform="tiktok", origin="screenshot", status="analyzed", slideshow_like=1,
                    anime="Naruto", format="ranking", topic="Saddest Naruto deaths", hook="IT STILL HURTS",
                    views=1200000, score=500.0, url="https://tiktok.com/x")
    calls = []

    def fake(**kw):
        calls.append(kw)
        return {"ideas": [{"anime": "Naruto", "format": "ranking", "topic": "Naruto deaths that broke fans", "hook": "H",
                           "angle": "a", "score": 80, "why": "w", "inspired_by": [tid]}]}
    monkeypatch.setattr("clipper.llm.structured", fake)
    (sid,) = ideas.generate_ideas(1)
    assert "Saddest Naruto deaths" in calls[0]["user"] and f"[{tid}]" in calls[0]["user"]
    assert "tiktok: Saddest Naruto deaths" in db.get("slideshows", sid)["inspiration"]
    ideas.generate_ideas(focus_trend=tid)
    assert "ALL ideas around this one trending post" in calls[1]["user"]


def test_refresh_bookkeeping(cfg, monkeypatch):
    monkeypatch.setattr(trends, "fetch_youtube", lambda: 0)
    monkeypatch.setattr(trends, "fetch_anilist", lambda: 15)
    assert trends.due_for_refresh()
    rep = trends.refresh()
    assert "YouTube : 0 nouvelle(s)" in rep and "AniList : 15 animes en tendance" in rep and not trends.due_for_refresh()


def test_trends_page_and_upload(cfg, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    ran = []
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda label, fn, lane="video": ran.append(fn))
    monkeypatch.setattr(trends, "import_screenshot", lambda p, name: ran.append(("imported", name)))
    db.insert("trends", platform="youtube", origin="api", external_id="yt:z", status="analyzed", slideshow_like=1,
              topic="Top 5 JJK", format="ranking", views=1234567, thumb_url="https://i.ytimg.com/vi/z/mqdefault.jpg")
    with TestClient(appmod.app) as c:
        r = c.get("/slides-trends")
        assert r.status_code == 200 and "Top 5 JJK" in r.text and "1 234 567" in r.text
        p = tmp_path / "a.png"
        Image.new("RGB", (10, 10)).save(p)
        r = c.post("/slides-trends/upload", files=[("files", ("a.png", p.read_bytes(), "image/png")),
                                                    ("files", ("notes.txt", b"x", "text/plain"))], follow_redirects=False)
        assert r.status_code == 303
        ran[-1]()                                      # exécute le travail mis en file
        assert ("imported", "a.png") in ran and not any(x == ("imported", "notes.txt") for x in ran)


class FakeComments:
    def __init__(self, disabled=False):
        self.disabled = disabled

    def commentThreads(self):
        me = self

        def lst(**kw):
            def run():
                if me.disabled:
                    from googleapiclient.errors import HttpError
                    raise HttpError(SimpleNamespace(status=403, reason="x"),
                                    b'{"error":{"errors":[{"reason":"commentsDisabled"}]}}')
                return {"items": [{"snippet": {"topLevelComment": {"snippet": {
                    "textDisplay": "Where is Yuta?? he should be #2", "likeCount": 812}}}}]}
            assert kw["videoId"] == "abc" and kw["order"] == "relevance"
            return SimpleNamespace(execute=run)
        return SimpleNamespace(list=lst)


def test_deep_study_reads_cover_and_comments(cfg, monkeypatch, tmp_path):
    tid = db.insert("trends", platform="youtube", origin="api", external_id="yt:abc", status="analyzed",
                    slideshow_like=1, title="Strongest JJK", topic="t", format="ranking", views=900000, score=9.0)
    skip = db.insert("trends", platform="youtube", origin="api", external_id="yt:zzz", status="irrelevant",
                     slideshow_like=0, score=99.0)
    monkeypatch.setattr("clipper.youtube.service", lambda: FakeComments())

    def cover(vid, dest):
        Image.new("RGB", (60, 100), "red").save(dest)
        return dest
    monkeypatch.setattr(trends, "fetch_cover", cover)
    seen = []

    def fake(**kw):
        seen.append(kw)
        return {"hook": "TOP 5 STRONGEST", "format": "ranking", "topic": "Strongest JJK", "slideshow_like": True,
                "why": "debate", "audience": "Fans demand Yuta in the top 2."}
    monkeypatch.setattr("clipper.llm.structured", fake)
    assert trends.deep_pending() == 1 and trends.deep_pending() == 0          # une seule fois par Short
    t = db.get("trends", tid)
    assert t["deep"] == 1 and t["hook"] == "TOP 5 STRONGEST" and "Yuta" in t["audience"] and t["image_path"]
    assert db.get("trends", skip)["deep"] == 0
    user = seen[0]["user"]
    assert user[0]["type"] == "image" and "Where is Yuta??" in user[-1]["text"] and "812 likes" in user[-1]["text"]
    assert quota.used("default") == 1
    assert "audience: Fans demand Yuta" in trends.as_prompt([t])


def test_deep_study_without_comments(cfg, monkeypatch):
    db.insert("trends", platform="youtube", origin="api", external_id="yt:abc", status="analyzed", slideshow_like=1)
    monkeypatch.setattr("clipper.youtube.service", lambda: FakeComments(disabled=True))
    monkeypatch.setattr(trends, "fetch_cover", lambda vid, dest: None)
    monkeypatch.setattr("clipper.llm.structured", lambda **kw: {
        "hook": "h", "format": "facts", "topic": "x", "slideshow_like": False, "why": "w", "audience": "a"})
    assert trends.deep_pending() == 1
    assert db.query("SELECT status FROM trends")[0]["status"] == "irrelevant"


def test_anilist_feeds_ideas(cfg, monkeypatch):
    import httpx

    def post(url, json=None, **kw):
        assert url == "https://graphql.anilist.co" and json["variables"]["n"] == 15
        return httpx.Response(200, request=httpx.Request("POST", url), json={"data": {"Page": {"media": [
            {"title": {"english": None, "romaji": "Jujutsu Kaisen"}, "trending": 900,
             "characters": {"nodes": [{"name": {"full": "Satoru Gojo"}}, {"name": {"full": "Yuta Okkotsu"}}]}}]}}})
    monkeypatch.setattr(trends.httpx, "post", post)
    assert trends.fetch_anilist() == 1
    assert "Jujutsu Kaisen (fan favourites: Satoru Gojo, Yuta Okkotsu)" in trends.anilist_prompt()
    calls = []
    monkeypatch.setattr("clipper.llm.structured", lambda **kw: calls.append(kw) or {"ideas": []})
    ideas.generate_ideas(1)
    assert "Trending on AniList" in calls[0]["user"] and "Satoru Gojo" in calls[0]["user"]
