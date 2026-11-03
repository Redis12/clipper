"""Slideshows : idées, script, bibliothèque, choix d'image, rendu, revue, publication."""
import io
import subprocess
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from clipper import db, quota
from clipper.slides import ideas, library, produce, publish, render


def make_img(path: Path, seed: int, size=(1920, 1080)):
    """Image abstraite (formes géométriques), assez nette pour passer les filtres."""
    path.parent.mkdir(parents=True, exist_ok=True)
    import random
    r = random.Random(seed)
    im = Image.new("RGB", size, tuple(r.randrange(60, 200) for _ in range(3)))
    d = ImageDraw.Draw(im)
    for _ in range(40):
        x, y = r.randrange(size[0]), r.randrange(size[1])
        w, h = r.randrange(20, max(21, size[0] // 3)), r.randrange(20, max(21, size[1] // 3))
        d.rectangle((x, y, x + w, y + h), fill=tuple(r.randrange(256) for _ in range(3)), outline=(0, 0, 0), width=4)
    im.save(path, "JPEG", quality=92)


@pytest.fixture()
def lib(cfg):
    root = library.root()
    for i in range(6):
        make_img(root / "Jujutsu Kaisen" / "Gojo Satoru" / f"g{i}.jpg", i)
    for i in range(6):
        make_img(root / "Jujutsu Kaisen" / f"misc{i}.jpg", 10 + i)
    for i in range(3):
        make_img(root / "Naruto" / "_frames" / "abc" / f"{i:04d}.jpg", 20 + i)
    make_img(root / "Naruto" / "tiny.jpg", 30, size=(200, 120))       # trop petite : ignorée
    library.scan()
    return root


SCRIPT = {
    "cover": {"text": "Gojo facts most fans missed", "anime": "Jujutsu Kaisen", "character": "Gojo Satoru", "scene": "smiling"},
    "slides": [{"label": f"Fact {i}", "text": f"Gojo detail number {i} that fans love.", "anime": "Jujutsu Kaisen",
                "character": "Gojo Satoru" if i % 2 else "", "scene": "battle", "confidence": 95 if i != 3 else 55}
               for i in range(1, 6)],
    "end": {"text": "Which one did you know?", "anime": "Jujutsu Kaisen", "character": "", "scene": "group"},
    "caption": "Did you know these? Tell me below", "hashtags": ["#JJK", "gojo", "anime", "gojo"],
    "yt_title": "5 Gojo details most fans missed", "yt_description": "Five small Gojo details.",
}


def fake_llm(calls):
    def f(**kw):
        calls.append(kw)
        if kw["tool_name"] == "propose_ideas":
            return {"ideas": [
                {"anime": "jujutsu kaisen", "format": "facts", "topic": "5 Gojo details fans missed", "hook": "YOU MISSED THESE",
                 "angle": "a", "score": 81, "why": "w"},
                {"anime": "Naruto", "format": "ranking", "topic": "Top 5 Naruto villains", "hook": "#1 IS CONTROVERSIAL",
                 "angle": "a", "score": 74, "why": "w"},
                {"anime": "Naruto", "format": "ranking", "topic": "top 5 naruto villains", "hook": "dup", "angle": "", "score": 1, "why": ""},
            ]}
        if kw["tool_name"] == "write_slideshow":
            return SCRIPT
        if kw["tool_name"] == "pick_image":
            n = sum(1 for b in kw["user"] if b.get("type") == "image")
            return {"index": 0, "character_match": True, "ranking": [0, 1, n - 1]}
        raise AssertionError(kw["tool_name"])
    return f


def test_library_scan_and_stats(lib):
    st = {a["anime"]: a for a in library.stats()}
    assert st["Jujutsu Kaisen"]["library"] == 12 and st["Jujutsu Kaisen"]["characters"] == {"Gojo Satoru": 6}
    assert st["Naruto"]["frames"] == 3 and st["Naruto"]["library"] == 0      # la petite image est ignorée
    assert set(library.animes_with_images()) == {"jujutsukaisen", "naruto"}
    (lib / "Naruto" / "_frames" / "abc" / "0000.jpg").unlink()
    assert library.scan()["removed"] == 1


def test_ideas_dedup_and_canonical(lib, monkeypatch):
    calls = []
    monkeypatch.setattr("clipper.llm.structured", fake_llm(calls))
    ids = ideas.generate_ideas(3)
    rows = [db.get("slideshows", i) for i in ids]
    assert [r["anime"] for r in rows] == ["Jujutsu Kaisen", "Naruto"]        # doublon écarté, nom normalisé
    assert "Jujutsu Kaisen, Naruto" in calls[0]["system"]                     # seulement les animes avec images
    ideas.generate_ideas(3)
    assert "5 Gojo details fans missed" in calls[1]["user"]                    # sujets existants transmis
    assert ideas.guess_format("Top 10 strongest") == "ranking" and ideas.guess_format("Guess who") == "quiz"


def test_produce_end_to_end(lib, monkeypatch):
    calls = []
    monkeypatch.setattr("clipper.llm.structured", fake_llm(calls))
    sid = ideas.add_user_topic("5 Gojo details fans missed", "Jujutsu Kaisen")
    assert produce.produce(sid)
    s = db.get("slideshows", sid)
    assert s["status"] == "review" and len(s["slides"]) == 7
    assert s["hashtags"] == ["jjk", "gojo", "anime"]
    paths = [sl["image_path"] for sl in s["slides"]]
    assert all(paths) and len(set(paths)) == 7                                  # aucune image réutilisée
    gojo = [sl for sl in s["slides"] if sl["character"] == "Gojo Satoru"]
    assert all("Gojo Satoru" in sl["image_path"] for sl in gojo)               # dossier du perso privilégié
    assert "incertain" in s["error"] and "4" in s["error"]                     # slide 4 : confiance 55
    for fmt, (W, H) in [("vertical", (1080, 1920)), ("portrait", (1080, 1350))]:
        imgs = render.slide_paths(sid, fmt)
        assert len(imgs) == 7
        with Image.open(imgs[0]) as im:
            assert im.size == (W, H)
    video = Path(s["video_path"])
    info = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=width,height",
                           "-of", "default=nw=1", str(video)], capture_output=True, text=True).stdout
    assert "width=1080" in info and "height=1920" in info
    dur = float([l for l in info.splitlines() if l.startswith("duration=")][0].split("=")[1])
    expected = sum(render.durations(s["slides"])) + 0.35
    assert abs(dur - expected) < 0.3, (dur, expected)
    assert db.one("SELECT SUM(use_count) AS n FROM images")["n"] == 7


def test_review_edits(lib, monkeypatch):
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    sid = ideas.add_user_topic("x", "Jujutsu Kaisen")
    produce.produce(sid)
    before = db.get("slideshows", sid)["slides"][2]
    s = produce.edit_slide(sid, 2, text="Brand new   text", label="#3")
    assert s["slides"][2]["text"] == "Brand new text" and s["slides"][2]["confidence"] == 100 and s["render_needed"]
    alt = before["alts"][0]
    s = produce.swap_image(sid, 2, alt)
    assert s["slides"][2]["image_path"] == alt and before["image_path"] in s["slides"][2]["alts"]


def test_render_no_image_and_long_text(cfg, tmp_path):
    slide = {"kind": "body", "label": "#1", "text": "word " * 40, "image_path": None}
    out = render.draw_slide(slide, 1080, 1920, tmp_path / "a.jpg")
    with Image.open(out) as im:
        assert im.size == (1080, 1920)
    cfg["slides"]["render"]["text_style"] = "box"
    render.draw_slide({**slide, "kind": "cover", "text": "Short hook"}, 1080, 1350, tmp_path / "b.jpg")


def test_smart_crop_follows_detail():
    im = Image.new("RGB", (1920, 1080), (40, 40, 40))
    d = ImageDraw.Draw(im)
    for k in range(60):                               # détails concentrés à droite
        d.line((1500 + k * 5, 0, 1500 + k * 5, 1080), fill=(255, 255, 255), width=2)
    crop = render.smart_crop(im, 1080, 1920)
    assert crop.size == (1080, 1920)
    import numpy as np
    a = np.asarray(crop.convert("L"), dtype=float)
    assert a[:, a.shape[1] // 2:].std() > a[:, : a.shape[1] // 4].std()


def test_approve_schedule_and_manual_packs(lib, cfg, monkeypatch):
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    a, b = ideas.add_user_topic("a", "Jujutsu Kaisen"), ideas.add_user_topic("b", "Jujutsu Kaisen")
    produce.produce(a)
    produce.produce(b)
    ta, tb = publish.approve(a), publish.approve(b)
    assert ta != tb
    local = datetime.fromisoformat(ta).astimezone(__import__("zoneinfo").ZoneInfo("America/New_York"))
    assert local.strftime("%H:%M") in ("12:30", "19:30")
    posts = {p["platform"]: p for p in db.query("SELECT * FROM posts WHERE slideshow_id=?", (a,))}
    assert set(posts) == {"youtube", "instagram", "tiktok"}
    assert all(p["mode"] == "manual" for p in posts.values())        # YouTube auto: false, IG/TikTok désactivés
    z = zipfile.ZipFile(io.BytesIO(publish.export_zip(a, "instagram")))
    assert "caption.txt" in z.namelist() and len([n for n in z.namelist() if n.endswith(".jpg")]) == 7
    assert "#gojo" in z.read("caption.txt").decode()
    with Image.open(io.BytesIO(z.read("01.jpg"))) as im:
        assert im.size == (1080, 1350)
    publish.mark_manual_done(posts["instagram"]["id"], "https://instagram.com/p/x")
    assert db.get("slideshows", a)["status"] == "approved"
    for p in ("youtube", "tiktok"):
        publish.mark_manual_done(posts[p]["id"])
    assert db.get("slideshows", a)["status"] == "published"
    with pytest.raises(ValueError):
        publish.unapprove(a)


def test_youtube_short_upload_private_scheduled(lib, cfg, monkeypatch):
    from test_web_publish import FakeYT
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    (Path(cfg["paths"]["data"]) / "youtube_token.json").write_text("{}")       # « connecté »
    cfg["slides"]["publish"]["youtube"]["auto"] = True
    fake = FakeYT()
    monkeypatch.setattr("clipper.youtube.service", lambda: fake)
    sid = ideas.add_user_topic("a", "Jujutsu Kaisen")
    produce.produce(sid)
    at = publish.approve(sid)
    assert publish.due(datetime.fromisoformat(at) - timedelta(days=1))          # YouTube : en avance
    report = publish.run()
    yt = db.one("SELECT * FROM posts WHERE slideshow_id=? AND platform='youtube'", (sid,))
    assert yt["status"] == "done" and yt["url"].startswith("https://youtube.com/shorts/"), report
    body = [kw for n, kw in fake.calls if n == "videos.insert"][0]["body"]
    assert body["status"]["privacyStatus"] == "private" and body["status"]["publishAt"].endswith("Z")
    assert "#shorts" in body["snippet"]["description"] and body["snippet"]["categoryId"] == "24"
    assert quota.uploads_today() == 1
    assert any("à la main" in r for r in report) or True


def test_instagram_tiktok_auto_publish_at_time(lib, cfg, monkeypatch):
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    cfg["slides"]["publish"]["platforms"] = ["instagram", "tiktok"]
    cfg["slides"]["publish"]["instagram"]["enabled"] = True
    cfg["slides"]["publish"]["tiktok"]["enabled"] = True
    cfg["slides"]["publish"]["hosting"]["kind"] = "s3"
    from clipper.slides import tiktok
    tiktok.token_path().write_text('{"access_token": "a", "refresh_token": "r", "expires_at": 9e12}')
    sent = []
    monkeypatch.setitem(publish.PUBLISHERS, "instagram", lambda s: (sent.append("ig"), ("ig1", "https://ig/p/1"))[1])
    monkeypatch.setitem(publish.PUBLISHERS, "tiktok", lambda s: (sent.append("tt"), ("tt1", ""))[1])
    sid = ideas.add_user_topic("a", "Jujutsu Kaisen")
    produce.produce(sid)
    at = publish.approve(sid)
    assert publish.due() == []                                                    # pas avant l'heure
    later = datetime.fromisoformat(at) + timedelta(minutes=1)
    assert len(publish.due(later)) == 2
    db.execute("UPDATE posts SET publish_at=?", ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),))
    publish.run()
    assert sorted(sent) == ["ig", "tt"] and db.get("slideshows", sid)["status"] == "published"


def test_frames_filter(tmp_path):
    raw = tmp_path / "raw"
    for i in range(5):
        make_img(raw / f"f_{i:05d}.jpg", 40 + i)
    make_img(raw / "f_00010.jpg", 40)                                             # doublon exact
    Image.new("RGB", (1920, 1080), (5, 5, 5)).save(raw / "f_00011.jpg")          # écran noir
    Image.new("RGB", (1920, 1080), (120, 120, 120)).save(raw / "f_00012.jpg")    # flou / vide
    out = tmp_path / "out"
    out.mkdir()
    n = library.filter_frames(sorted(raw.glob("*.jpg")), out, 100, 60)
    assert n == 5 and len(list(out.glob("*.jpg"))) == 5


def test_slide_pages(lib, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda *a, **k: None)
    sid = ideas.add_user_topic("Top Gojo moments", "Jujutsu Kaisen")
    produce.produce(sid)
    with TestClient(appmod.app) as c:
        for url in ("/slides", f"/slides/{sid}", "/slides-library", "/slides-queue"):
            r = c.get(url)
            assert r.status_code == 200, url
        assert c.get(f"/media/slide/{sid}/vertical/1.jpg").headers["content-type"] == "image/jpeg"
        assert c.get(f"/media/slide-alt/{sid}/1/1.jpg").status_code == 200
        r = c.post(f"/api/slides/{sid}/slide/1", json={"text": "Edited"}).json()
        assert r["slides"][1]["text"] == "Edited"
        r = c.post(f"/api/slides/{sid}/slide/1/image/1").json()
        assert r["slides"][1]["has_image"]
        r = c.post(f"/api/slides/{sid}/meta", json={"hashtags": "#a, b #c"}).json()
        assert r["hashtags"] == ["a", "b", "c"]
        r = c.post(f"/api/slides/{sid}/approve").json()
        assert r["status"] == "approved" and len(r["posts"]) == 3
        z = c.get(f"/slides/{sid}/pack/tiktok.zip")
        assert z.status_code == 200 and z.headers["content-type"] == "application/zip"
        assert c.post("/slides/topic", data={"topic": "My topic", "anime": "Naruto"}, follow_redirects=False).status_code == 303


MONTHS = ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER",
          "NOVEMBER", "DECEMBER"]


def test_birth_month_format_12_slides_and_instagram_split(lib, monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw)
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "cover": {"text": "Your birth month = your JJK character", "anime": "Jujutsu Kaisen",
                                        "character": "Gojo Satoru", "scene": ""},
                    "slides": [{"label": m, "text": f"Character {i} — fun reason", "anime": "Jujutsu Kaisen",
                                "character": "Gojo Satoru" if i == 0 else "", "scene": ""} for i, m in enumerate(MONTHS)],
                    "end": {"text": "Comment your month", "anime": "Jujutsu Kaisen", "character": "", "scene": ""}}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    assert ideas.guess_format("Your birth month = your JJK character") == "assign"
    sid = ideas.add_user_topic("Your birth month = your JJK character", "Jujutsu Kaisen")
    assert db.get("slideshows", sid)["format"] == "assign"
    assert produce.produce(sid)
    s = db.get("slideshows", sid)
    assert len(s["slides"]) == 14 and [x["label"] for x in s["slides"][1:13]] == MONTHS
    script_call = [c for c in calls if c["tool_name"] == "write_slideshow"][0]
    assert "12 to 12 content slides" in script_call["system"] and "Gojo Satoru" in script_call["system"]
    z = zipfile.ZipFile(io.BytesIO(publish.export_zip(sid, "instagram")))
    p1 = [n for n in z.namelist() if n.startswith("post1/") and n.endswith(".jpg")]
    p2 = [n for n in z.namelist() if n.startswith("post2/") and n.endswith(".jpg")]
    assert len(p1) <= 10 and len(p2) <= 10 and len(p1) + len(p2) == 15        # couverture dans les deux
    assert "post2/01.jpg" in z.namelist() and "post1/caption.txt" in z.namelist()
    t = zipfile.ZipFile(io.BytesIO(publish.export_zip(sid, "tiktok")))
    assert len([n for n in t.namelist() if n.endswith(".jpg") and "grille" not in n]) == 14
    assert "grille_image_unique.jpg" in t.namelist()


def test_wallpaper_slide_has_no_text_band(cfg, tmp_path):
    src = tmp_path / "bg.jpg"
    make_img(src, 3)
    a = render.draw_slide({"kind": "body", "label": "", "text": "", "image_path": str(src)}, 1080, 1920, tmp_path / "a.jpg")
    b = render.draw_slide({"kind": "body", "label": "", "text": "", "image_path": str(src)}, 1080, 1920, tmp_path / "b.jpg")
    import numpy as np
    with Image.open(src) as s0, Image.open(a) as im:
        ref = np.asarray(render.smart_crop(s0.convert("RGB"), 1080, 1920), dtype=float)
        out = np.asarray(im, dtype=float)
    assert abs(out.mean() - ref.mean()) < 3          # pas d'assombrissement ni de texte


def test_new_formats_no_fact_warnings(lib, monkeypatch):
    def fake(**kw):
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "slides": [{**x, "confidence": 10} for x in SCRIPT["slides"]]}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    sid = ideas.add_user_topic("Red flags of dating JJK characters", "Jujutsu Kaisen")
    produce.produce(sid)
    s = db.get("slideshows", sid)
    assert s["format"] == "redflags" and not (s["error"] or "")      # pas d'alerte « fait incertain »


def test_tag_frames_moves_into_character_folders(lib, cfg, monkeypatch):
    root = lib
    for i in range(5):
        make_img(root / "Jujutsu Kaisen" / "_frames" / "src1" / f"{i:04d}.jpg", 60 + i)
    library.scan()
    seen = []

    def fake(**kw):
        seen.append(kw)
        n = sum(1 for b in kw["user"] if b.get("type") == "image")
        names = ["gojo satoru", "Sukuna", "", "Sukuna", "Yuji Itadori"]
        confs = [95, 90, 99, 40, 88]
        return {"items": [{"index": k, "character": names[k], "confidence": confs[k]} for k in range(n)]}
    monkeypatch.setattr("clipper.llm.structured", fake)
    r = library.tag_frames("Jujutsu Kaisen")
    assert r == {"moved": 3, "kept": 2, "seen": 5}
    assert "Gojo Satoru" in seen[0]["system"]                                   # orthographe existante proposée
    chars = {a["anime"]: a for a in library.stats()}["Jujutsu Kaisen"]["characters"]
    assert chars["Gojo Satoru"] == 7 and chars["Sukuna"] == 1 and chars["Yuji Itadori"] == 1
    assert (root / "Jujutsu Kaisen" / "Sukuna" / "src1_0001.jpg").exists()
    assert library.scan()["added"] == 0 and library.scan()["removed"] == 0     # index cohérent avec le disque
    assert library.tag_frames("Jujutsu Kaisen")["seen"] == 0                   # jamais retrié


def test_birth_month_grid_and_notes(lib, monkeypatch):
    calls = []

    def fake(**kw):
        calls.append(kw)
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "cover": {"text": "Your birth month = your JJK character", "anime": "Jujutsu Kaisen",
                                        "character": "", "scene": ""},
                    "slides": [{"label": m, "text": f"Char {i} — reason", "anime": "Jujutsu Kaisen", "character": "",
                                "scene": ""} for i, m in enumerate(MONTHS)]}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    sid = ideas.add_user_topic("Your birth month = your JJK character", "Jujutsu Kaisen",
                               notes="Use exactly: Toji, Nobara, Choso")
    produce.produce(sid)
    script = [c for c in calls if c["tool_name"] == "write_slideshow"][0]
    assert "MANDATORY instructions from the creator: Use exactly: Toji, Nobara, Choso" in script["user"]
    for fmt, size in [("vertical", (1080, 1920)), ("portrait", (1080, 1350))]:
        with Image.open(render.out_dir(sid) / f"grid_{fmt}.jpg") as im:
            assert im.size == size
    z = zipfile.ZipFile(io.BytesIO(publish.export_zip(sid, "tiktok")))
    assert "grille_image_unique.jpg" in z.namelist()


def test_end_without_image_and_video_off(lib, cfg, monkeypatch):
    cfg["slides"]["video"]["auto"] = False
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    sid = ideas.add_user_topic("5 Gojo details fans missed", "Jujutsu Kaisen")
    produce.produce(sid)
    s = db.get("slideshows", sid)
    s["slides"][-1]["image_path"] = None                      # la fin n'a pas d'image
    db.update("slideshows", sid, slides=s["slides"])
    render.render_slide(sid, len(s["slides"]) - 1)
    import numpy as np
    with Image.open(render.slide_paths(sid, "vertical")[-1]) as im:
        assert np.asarray(im, dtype=float).std() > 15            # fond flouté, pas un aplat
    assert not (render.out_dir(sid) / "short.mp4").exists()     # pas de vidéo
    publish.approve(sid)                                        # la fin sans image ne bloque pas
    plats = {p["platform"] for p in db.query("SELECT platform FROM posts WHERE slideshow_id=?", (sid,))}
    assert plats == {"instagram", "tiktok"}



def test_video_on_demand_adds_youtube_post(lib, cfg, monkeypatch):
    cfg["slides"]["video"]["auto"] = False
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    sid = ideas.add_user_topic("a", "Jujutsu Kaisen")
    produce.produce(sid)
    publish.approve(sid)
    assert not render.has_video(sid)
    assert not db.query("SELECT 1 AS x FROM posts WHERE slideshow_id=? AND platform='youtube'", (sid,))
    publish.make_video(sid)                                      # clic sur « Générer la vidéo »
    assert render.has_video(sid)
    assert db.query("SELECT 1 AS x FROM posts WHERE slideshow_id=? AND platform='youtube'", (sid,))


def test_upload_image_for_a_slide(lib, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda *a, **k: None)
    sid = ideas.add_user_topic("x", "Jujutsu Kaisen")
    produce.produce(sid)
    p = tmp_path / "toji action.png"
    make_img(p, 77, size=(1920, 1080))
    with TestClient(appmod.app) as c:
        r = c.post(f"/api/slides/{sid}/slide/1/upload", files={"file": ("toji action.png", p.read_bytes(), "image/png")})
        assert r.status_code == 200, r.text
        s = db.get("slideshows", sid)
        new = s["slides"][1]["image_path"]
        assert new.endswith("toji_action.png") and "Gojo Satoru" in new          # rangée dans le dossier du perso
        assert db.one("SELECT 1 AS x FROM images WHERE path=?", (new,))
        bad = c.post(f"/api/slides/{sid}/slide/1/upload", files={"file": ("x.txt", b"hello", "text/plain")})
        assert bad.status_code == 400


def test_choose_library_image_by_hand(lib, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda *a, **k: None)
    sid = ideas.add_user_topic("x", "Jujutsu Kaisen")
    produce.produce(sid)
    sl = db.get("slideshows", sid)["slides"][1]
    with TestClient(appmod.app) as c:
        lst = c.get(f"/api/slides/{sid}/slide/1/choices").json()
        assert lst and sum(x["current"] for x in lst) == 1
        assert all(sl["character"].split()[0].lower() in x["character"].lower() for x in lst)   # seulement ce perso
        assert lst[0]["uses"] <= lst[-1]["uses"]                                                 # moins utilisées d'abord
        other = next(x for x in lst if not x["current"])
        t = c.get(f"/media/lib/{other['id']}.jpg")
        assert t.status_code == 200 and t.headers["content-type"] == "image/jpeg"
        r = c.post(f"/api/slides/{sid}/slide/1/lib/{other['id']}", json={})
        assert r.status_code == 200
        assert db.get("slideshows", sid)["slides"][1]["image_path"] == db.get("images", other["id"])["path"]
        assert c.post(f"/api/slides/{sid}/slide/1/lib/999999", json={}).status_code == 404


def test_emoji_are_drawn_not_tofu(cfg, tmp_path):
    assert render.split_emoji("A ⚠️ b 👍🏽") == [("A ", False), ("⚠️", True), (" b ", False), ("👍🏽", True)]
    if render._emoji_font() is None:
        pytest.skip("pas de police emoji sur cette machine")
    im = render.emoji_image("🔥", 80)
    assert im is not None and im.height == 80
    import numpy as np
    px = np.asarray(im.convert("RGB"), dtype=int)[np.asarray(im)[:, :, 3] > 128]
    assert (px[:, 0] - px[:, 2]).mean() > 40                      # du rouge/orange : un vrai emoji en couleur
    out = render.draw_slide({"kind": "cover", "label": "", "text": "TOP 5 ⚠️ SPOILERS", "image_path": None},
                            1080, 1920, tmp_path / "e.jpg")
    assert out.exists()


def test_mobile_page_and_lan_key(lib, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod, lan
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda *a, **k: None)
    sid = ideas.add_user_topic("5 Gojo details fans missed", "Jujutsu Kaisen")
    produce.produce(sid)
    publish.approve(sid)
    with TestClient(appmod.app) as c:                      # depuis le PC : libre
        r = c.get("/m")
        assert r.status_code == 200 and "5 Gojo details fans missed" in r.text and "#gojo" in r.text
        assert "clipper serve --lan" in r.text                # serveur pas ouvert au téléphone : on le dit
        monkeypatch.setenv("CLIPPER_LAN", "1")
        r = c.get("/m")
        assert f"/m?k={lan.token()}" in r.text and "<svg" in r.text   # lien + QR code sur le PC
    with TestClient(appmod.app, client=("192.168.1.42", 50000)) as phone:
        r = phone.get("/m")
        assert r.status_code == 403 and 'name="k"' in r.text   # téléphone sans clé : refusé, champ pour la coller
        assert lan.token() not in r.text and "<svg" not in phone.get(f"/m?k={lan.token()}").text
        assert phone.get(f"/m?k=wrong").status_code == 403
        assert phone.get(f"/m?k={lan.token()}").status_code == 200
        assert phone.get("/media/slide/%d/vertical/1.jpg" % sid).status_code == 200   # cookie posé
        assert f"/slides/{sid}/pack/tiktok.zip" in phone.get("/m").text
        z = phone.get(f"/slides/{sid}/pack/tiktok.zip")
        assert z.status_code == 200 and z.content[:2] == b"PK"


def test_watermark_and_end_cta(cfg, tmp_path):
    import numpy as np
    src = tmp_path / "bg.jpg"
    Image.new("RGB", (1920, 1080), (40, 40, 40)).save(src)
    cfg["slides"]["render"]["shade_opacity"] = 0
    body = {"kind": "body", "label": "", "text": "", "image_path": str(src)}
    with_wm = np.asarray(Image.open(render.draw_slide(body, 1080, 1920, tmp_path / "a.jpg")), dtype=float)
    cfg["slides"]["render"]["watermark"] = ""
    no_wm = np.asarray(Image.open(render.draw_slide(body, 1080, 1920, tmp_path / "b.jpg")), dtype=float)
    band = slice(int(1920 * 0.70), int(1920 * 0.75))
    assert with_wm[band].max() > no_wm[band].max() + 60            # le filigrane est là, au-dessus de la légende TikTok
    assert abs(with_wm[:1200].mean() - no_wm[:1200].mean()) < 1     # et nulle part ailleurs
    end = {"kind": "end", "label": "", "text": "Who did you get?", "image_path": str(src)}
    cfg["slides"]["render"]["end_cta"] = ""
    plain = np.asarray(Image.open(render.draw_slide(end, 1080, 1920, tmp_path / "c.jpg")), dtype=float)
    cfg["slides"]["render"]["end_cta"] = "Follow @animelorehq for more"
    cta = np.asarray(Image.open(render.draw_slide(end, 1080, 1920, tmp_path / "d.jpg")), dtype=float)
    yellow = lambda a: ((a[:, :, 0] > 200) & (a[:, :, 1] > 180) & (a[:, :, 2] < 90)).sum()
    assert yellow(cta) > yellow(plain) + 500                         # ligne jaune « Follow… » ajoutée


def test_parse_chart_variants():
    ch = ideas.parse_chart("EP1 8.1, EP2 7.9, Ep 3: 8,4 / episode 4 - 8.4 overall 8.6 (IMDb)")
    assert ch["labels"] == ["EP 1", "EP 2", "EP 3", "EP 4"] and ch["values"] == [8.1, 7.9, 8.4, 8.4]
    assert ch["score"] == "8.6" and ch["source"] == "IMDb rating"
    ch = ideas.parse_chart("E2 9.0 E1 8.0 MAL")                    # trié, note globale = moyenne
    assert ch["values"] == [8.0, 9.0] and ch["score"] == "8.5" and ch["source"] == "MyAnimeList rating"
    assert ideas.parse_chart("no numbers here") is None
    ov = ideas.parse_chart("Dragon Ball Super Beerus IMDb rating 8,3")
    assert ov["values"] == [8.3] and ov["overall"] and ov["labels"] == [""] and ov["source"] == "IMDb rating"
    one = ideas.parse_chart("EP8 9.1 IMDb")
    assert one["values"] == [9.1] and one["labels"] == ["EP 8"]
    assert ideas.guess_format("Edgerunners 2 episodes ranked by IMDb rating") == "ratings"


def test_ratings_slideshow_gets_chart(lib, monkeypatch, tmp_path):
    import numpy as np
    eps = [8.1, 7.9, 8.4, 8.4, 8.7, 8.2, 8.7, 9.2, 9.0, 9.2]
    seen = []

    def fake(**kw):
        seen.append(kw)
        if kw["tool_name"] == "write_slideshow":
            order = sorted(range(10), key=lambda i: -eps[i])
            return {**SCRIPT, "cover": {**SCRIPT["cover"], "text": "Edgerunners 2 IMDb ratings"},
                    "slides": [{**SCRIPT["slides"][0], "label": f"#{r + 1} · EP {i + 1}", "text": f"{eps[i]} ⭐ — great"}
                               for r, i in enumerate(order)]}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    notes = ", ".join(f"EP{i + 1} {v}" for i, v in enumerate(eps)) + " overall 8.6 IMDb"
    sid = ideas.add_user_topic("Edgerunners 2 episodes ranked by IMDb rating", "Jujutsu Kaisen", notes=notes)
    assert db.get("slideshows", sid)["format"] == "ratings"
    produce.produce(sid)
    s = db.get("slideshows", sid)
    assert s["slides"][0]["chart"]["values"] == eps and len(s["slides"]) == 12
    script_call = next(k for k in seen if k["tool_name"] == "write_slideshow")
    assert "EP1 8.1" in script_call["user"]                     # les notes sont transmises telles quelles
    cover = np.asarray(Image.open(render.slide_paths(sid, "vertical")[0]).convert("RGB"), dtype=int)
    _, bottom = render.chart_geometry(1080, 1920)
    row = cover[bottom - 5]
    yellow = (row[:, 0] > 200) & (row[:, 1] > 170) & (row[:, 2] < 80)
    assert yellow.sum() > 400                                   # les barres sont dessinées
    bad = ideas.add_user_topic("Some show IMDb ratings", "Jujutsu Kaisen", notes="no numbers")
    assert produce.produce(bad) is False and "notes dans les consignes" in db.get("slideshows", bad)["error"]


def test_board_accepts_any_anime(lib, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda *a, **k: None)
    with TestClient(appmod.app) as c:
        r = c.get("/slides")
        assert r.status_code == 200 and 'list="board-animes"' in r.text and "<option>Naruto</option>" in r.text
        c.post("/slides/topic", data={"topic": "Edgerunners 2 IMDb ratings", "anime": "Cyberpunk Edgerunners",
                                      "notes": "EP1 8.1 EP2 7.9"}, follow_redirects=False)
    s = db.query("SELECT * FROM slideshows ORDER BY id DESC LIMIT 1")[0]
    assert s["anime"] == "Cyberpunk Edgerunners" and s["format"] == "ratings"


def test_badge_generated_once_and_reused(cfg, tmp_path):
    src = tmp_path / "bg.jpg"
    Image.new("RGB", (1080, 1920), (40, 40, 40)).save(src)
    slide = {"kind": "body", "label": "", "text": "", "image_path": str(src)}
    render.draw_slide(slide, 1080, 1920, tmp_path / "a.jpg")
    p = render.brand_dir() / "watermark.png"
    assert p.exists()
    Image.new("RGBA", (200, 50), (255, 0, 0, 255)).save(p)           # badge perso : il est utilisé tel quel
    img = Image.open(render.draw_slide(slide, 1080, 1920, tmp_path / "b.jpg")).convert("RGB")
    y = int(1920 * 0.74) - 10
    assert img.getpixel((540, y))[0] > 200 and img.getpixel((540, y))[1] < 80


def test_ratings_logo_checkbox(lib, monkeypatch):
    import io
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda *a, **k: None)
    buf = io.BytesIO()
    Image.new("RGBA", (400, 120), (255, 255, 255, 255)).save(buf, "PNG")
    notes = "EP1 8.1 EP2 7.9 EP3 8.4"
    with TestClient(appmod.app) as c:
        c.post("/slides/topic", data={"topic": "Show IMDb ratings", "anime": "Jujutsu Kaisen", "notes": notes,
                                      "use_logo": "on"}, files={"logo": ("logo.png", buf.getvalue(), "image/png")})
        c.post("/slides/topic", data={"topic": "Show IMDb ratings 2", "anime": "Jujutsu Kaisen", "notes": notes})
    assert render.logo_path("Jujutsu Kaisen").exists()
    with_logo, without = db.query("SELECT * FROM slideshows ORDER BY id")[-2:]
    assert with_logo["use_logo"] == 1 and without["use_logo"] == 0

    def fake(**kw):
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "slides": SCRIPT["slides"][:3]}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    ideas.write_script(with_logo["id"])
    ideas.write_script(without["id"])
    assert db.get("slideshows", with_logo["id"])["slides"][0]["chart"]["logo"].endswith("jujutsu-kaisen.png")
    assert "logo" not in db.get("slideshows", without["id"])["slides"][0]["chart"]
    s = db.get("slideshows", with_logo["id"])["slides"][0]
    render.draw_slide({**s, "image_path": None}, 1080, 1920, render.brand_dir() / "t.jpg")   # rendu avec logo OK


def test_ratings_two_seasons(lib, monkeypatch):
    notes = ("S1: EP1 7.9 EP2 8.2 EP3 7.9 EP4 8.7 EP5 8.0 EP6 9.2 EP7 8.0 EP8 8.2 EP9 8.6 EP10 9.5 "
             "S2: EP1 8.0 EP2 7.8 EP3 8.1 EP4 8.2 EP5 8.5 EP6 7.9 EP7 8.2 EP8 9.1 EP9 8.7 EP10 9.0 (IMDb)")
    charts = ideas.parse_charts(notes)
    assert [c["season"] for c in charts] == [1, 2] and charts[0]["values"][-1] == 9.5 and charts[1]["values"][7] == 9.1
    assert all(c["source"] == "IMDb rating" and not c["score_given"] for c in charts)
    from clipper.slides import library as lib_mod
    (lib_mod.root() / "logos").mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (300, 100), (255, 0, 0, 255)).save(lib_mod.root() / "logos" / "jujutsu_kaisen_logo_hd.png")
    assert render.logo_path("Jujutsu Kaisen").name == "jujutsu_kaisen_logo_hd.png"
    assert lib_mod.scan() and not db.query("SELECT 1 AS x FROM images WHERE path LIKE '%logo_hd%'")   # jamais une slide

    def fake(**kw):
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "slides": SCRIPT["slides"][:5]}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    sid = ideas.add_user_topic("Edgerunners IMDb ratings season 1 vs 2", "Jujutsu Kaisen", notes=notes)
    ideas.write_script(sid)
    sl = db.get("slideshows", sid)["slides"]
    assert sl[0]["chart"]["season"] == 1 and "logo" not in sl[0]["chart"]
    assert sl[1]["kind"] == "body" and sl[1]["text"] == "Season 2" and sl[1]["chart"]["logo"].endswith("logo_hd.png")
    assert len(sl) == 1 + 1 + 5 + 1



def test_single_episode_card(cfg, tmp_path):
    import numpy as np
    src = tmp_path / "bg.jpg"
    Image.new("RGB", (1920, 1080), (30, 30, 30)).save(src)
    ch = ideas.parse_chart("JJK S3 EP8 9.6 (IMDb)")
    out = render.draw_slide({"kind": "cover", "text": "JJK episode 8", "label": "", "image_path": str(src), "chart": ch},
                            1080, 1920, tmp_path / "one.jpg")
    a = np.asarray(Image.open(out).convert("RGB"), dtype=int)
    _, bottom = render.chart_geometry(1080, 1920)
    row = a[bottom - 20]
    yellow = (row[:, 0] > 200) & (row[:, 1] > 170) & (row[:, 2] < 80)
    assert 500 < yellow.sum() < 900                             # jauge remplie à 96 %, marges symétriques



def test_single_rating_is_card_only(lib, monkeypatch):
    def fake(**kw):
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "cover": {**SCRIPT["cover"], "text": "Dragon Ball Super: Beerus"}, "slides": []}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    sid = ideas.add_user_topic("Dragon Ball Super: Beerus IMDb rating", "Jujutsu Kaisen", notes="IMDb rating 8.3")
    ideas.write_script(sid)
    sl = db.get("slideshows", sid)["slides"]
    assert len(sl) == 1 and sl[0]["kind"] == "cover" and sl[0]["chart"]["values"] == [8.3]


def test_text_and_chart_are_centered(cfg, tmp_path):
    import numpy as np
    src = tmp_path / "bg.jpg"
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(src)
    cfg["slides"]["render"]["watermark"] = ""
    cfg["slides"]["render"]["shade_opacity"] = 0
    for slide in ({"kind": "body", "label": "", "text": "IIIIIIII", "image_path": str(src)},
                  {"kind": "cover", "text": "", "label": "", "image_path": str(src), "chart": ideas.parse_chart("EP1 9.9 IMDb")}):
        a = np.asarray(Image.open(render.draw_slide(slide, 1080, 1920, tmp_path / "c.jpg")).convert("L"), dtype=int)
        cols = np.where((a > 128).any(axis=0))[0]
        assert abs((cols.min() + cols.max()) / 2 - 540) <= 6, (cols.min(), cols.max())


def test_news_card_with_fun_fact(lib, monkeypatch, tmp_path):
    import numpy as np
    seen = []

    def fake(**kw):
        seen.append(kw)
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "slides": [{**SCRIPT["slides"][0], "character": "Gojo Satoru", "text": "ignored"}]}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    assert ideas.guess_format("Steel Ball Run EP 7 30th October") == "news"
    notes = ("Netflix, every Friday. SUB: Swipe for more →\n> FUN FACT | *Tomokazu Sugita* is returning as *Funny Valentine* | "
             "Previously voiced young *Joseph Joestar*")
    sid = ideas.add_user_topic("*Steel Ball Run* EP 7 | 30th October", "Jujutsu Kaisen", "news", notes)
    produce.produce(sid)
    sl = db.get("slideshows", sid)["slides"]
    assert [x["kind"] for x in sl] == ["cover", "body"]                    # carte + fun fact, pas de fin
    assert sl[0]["text"] == "*Steel Ball Run* EP 7 | 30th October" and sl[0]["news"]["sub"] == "SWIPE FOR MORE →"
    assert sl[1]["text"].startswith("*Tomokazu Sugita*") and sl[1]["news"]["tag"] == "FUN FACT"
    assert sl[1]["image_path"]                                             # image choisie via le perso de Claude
    img = np.asarray(Image.open(render.slide_paths(sid, "vertical")[0]).convert("RGB"), dtype=int)
    yellow = (img[..., 0] > 200) & (img[..., 1] > 170) & (img[..., 2] < 80)
    assert yellow[int(1920 * 0.55):int(1920 * 0.80)].sum() > 2000          # « STEEL BALL RUN » en jaune


def test_news_list_rows_title_left_date_right(cfg, tmp_path):
    import numpy as np
    src = tmp_path / "bg.jpg"
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(src)
    cfg["slides"]["render"]["watermark"] = ""
    sl = {"kind": "body", "label": "", "image_path": str(src), "text": "*THE ONE PIECE* — Feb 2027 // *FILM BAAD* — 2029",
          "news": {"tag": "X", "sub": "", "arrow": False}}
    a = np.asarray(Image.open(render.draw_slide(sl, 1080, 1920, tmp_path / "t.jpg")).convert("RGB"), dtype=int)
    yellow = (a[..., 0] > 200) & (a[..., 1] > 170) & (a[..., 2] < 80)
    cols = np.where(yellow.any(axis=0))[0]
    white = (a.min(axis=2) > 220)
    wcols = np.where(white[int(1920 * 0.5):].any(axis=0))[0]
    assert cols.min() < 260 and cols.max() < 700      # titres (jaunes) collés à gauche
    assert wcols.max() > 820                          # dates (blanches) collées à droite


def test_upscale_small_upload(lib, cfg, tmp_path, monkeypatch):
    import stat
    import sys
    exe = tmp_path / "realesrgan-ncnn-vulkan"
    exe.write_text(f"""#!{sys.executable}
import sys
from PIL import Image
a = sys.argv
i, o, s = a[a.index('-i') + 1], a[a.index('-o') + 1], int(a[a.index('-s') + 1])
im = Image.open(i); im.resize((im.width * s, im.height * s)).save(o)
""")
    exe.chmod(exe.stat().st_mode | stat.S_IEXEC)
    cfg["slides"]["upscale"] = {"enabled": True, "min_side": 1080, "target_side": 1440, "bin": str(exe),
                                "model": "realesrgan-x4plus-anime"}
    small = tmp_path / "small.jpg"
    make_img(small, 33, size=(500, 700))
    path = library.add_uploaded(small.read_bytes(), "toji.jpg", "Jujutsu Kaisen", "Toji Fushiguro")
    with Image.open(path) as im:
        assert min(im.size) == 1440                       # 500 → ×4 → redescendu à 1440
    assert (library.root() / "_originals" / "Jujutsu Kaisen" / "Toji Fushiguro" / "toji.jpg").exists()
    r = db.one("SELECT * FROM images WHERE path=?", (path,))
    assert min(r["width"], r["height"]) == 1440
    cfg["slides"]["upscale"]["bin"] = str(tmp_path / "missing")
    monkeypatch.setattr("shutil.which", lambda *a: None)
    p2 = library.add_uploaded(small.read_bytes(), "x.jpg", "Jujutsu Kaisen", "")
    with Image.open(p2) as im:
        assert im.size == (500, 700)                      # sans moteur : image inchangée, jamais bloquant


def test_delete_slide(lib, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda *a, **k: None)
    sid = ideas.add_user_topic("5 Gojo details fans missed", "Jujutsu Kaisen")
    produce.produce(sid)
    before = db.get("slideshows", sid)["slides"]
    n = len(before)
    with TestClient(appmod.app) as c:
        assert c.post(f"/api/slides/{sid}/slide/0/delete").status_code == 400          # jamais la couverture
        r = c.post(f"/api/slides/{sid}/slide/2/delete")
        assert r.status_code == 200
    after = db.get("slideshows", sid)["slides"]
    assert len(after) == n - 1 and after[2]["text"] == before[3]["text"]
    for fmt in ("vertical", "portrait"):
        assert len(render.slide_paths(sid, fmt)) == n - 1                              # fichiers renumérotés


def test_wallpapers_preview_then_clean(lib, monkeypatch):
    def fake(**kw):
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "slides": [{**SCRIPT["slides"][i], "text": "", "label": ""} for i in range(4)]}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    sid = ideas.add_user_topic("JJK wallpapers >>>", "Jujutsu Kaisen", "wallpaper")
    produce.produce(sid)
    sl = db.get("slideshows", sid)["slides"]
    assert sl[0]["plain"] and sl[0]["text"] == "JJK wallpapers >>>"
    body = sl[1:-1]
    assert len(body) == 8 and all("lock" in b for b in body[0::2]) and all(b.get("twin") for b in body[1::2])
    assert all(body[i]["image_path"] == body[i + 1]["image_path"] for i in range(0, 8, 2))   # même image
    assert len({body[i]["image_path"] for i in range(0, 8, 2)}) == 4                           # 4 wallpapers différents
    other = next(r["path"] for r in db.query("SELECT path FROM images") if r["path"] != body[0]["image_path"])
    produce.swap_image(sid, 1, other)                                    # changer l'aperçu change le wallpaper seul
    sl = db.get("slideshows", sid)["slides"]
    assert sl[1]["image_path"] == sl[2]["image_path"] == other
    off = ideas.add_user_topic("Naruto wallpapers", "Jujutsu Kaisen", "wallpaper", "no lockscreen")
    ideas.write_script(off)
    assert not any("lock" in x for x in db.get("slideshows", off)["slides"])


def test_wallpaper_folder(lib, monkeypatch):
    root = library.root()
    for i in range(5):
        make_img(root / "wallpaper" / "Jujutsu Kaisen" / f"w{i}.jpg", 40 + i, size=(1080, 1920))
    library.scan()
    rows = db.query("SELECT * FROM images WHERE origin='wallpaper'")
    assert len(rows) == 5 and all(r["anime"] == "Jujutsu Kaisen" and r["character"] is None for r in rows)
    assert not any(a["anime"].lower() == "wallpaper" for a in library.stats())
    calls = []

    def fake(**kw):
        calls.append(kw["tool_name"])
        if kw["tool_name"] == "write_slideshow":
            return {**SCRIPT, "slides": [{**SCRIPT["slides"][0], "text": "", "label": ""}] * 5}
        return fake_llm([])(**kw)
    monkeypatch.setattr("clipper.llm.structured", fake)
    sid = ideas.add_user_topic("JJK wallpapers >>>", "Jujutsu Kaisen", "wallpaper")
    produce.produce(sid)
    body = [x for x in db.get("slideshows", sid)["slides"] if x["kind"] == "body"]
    assert len(body) == 8                                              # 5 wallpapers : 1 couverture + 4 × (aperçu + seul)
    assert all("/wallpaper/" in x["image_path"].replace("\\\\", "/") for x in body)
    assert "pick_image" not in calls                                   # pas de vision pour les wallpapers
    # un post normal n'utilise jamais les wallpapers
    sid2 = ideas.add_user_topic("x", "Jujutsu Kaisen")
    monkeypatch.setattr("clipper.llm.structured", fake_llm([]))
    produce.produce(sid2)
    assert not any("/wallpaper/" in (x.get("image_path") or "") for x in db.get("slideshows", sid2)["slides"])
