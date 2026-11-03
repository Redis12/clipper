"""SEO : titre / description / hashtags pour YouTube, TikTok, Instagram, affichés sous chaque vidéo."""
import json

from clipper.slides import battle, fusion, seo


def test_domain_seo_names_first_no_spoiler():
    r = seo.build({"kind": "domain", "names": ["Satoru Gojo", "Ryomen Sukuna"], "winner": "Ryomen Sukuna"})
    yt = r["youtube"]
    assert yt["title"].startswith("Gojo vs Sukuna") and len(yt["title"]) <= 70
    assert "winner" not in yt["title"].lower() and "Sukuna wins" not in yt["description"]
    tags = [w for w in yt["description"].split() if w.startswith("#")]
    assert tags[:2] == ["#gojo", "#sukuna"] and len(tags) <= 5
    for plat in (yt["description"], r["tiktok"], r["instagram"]):           # 3 hashtags fixes partout
        h = [w for w in plat.split() if w.startswith("#")]
        assert {"#anime", "#animebattle", "#whowouldwin"} <= set(h) and len(h) <= 5
    assert len([w for w in r["instagram"].split() if w.startswith("#")]) <= 5      # limite Instagram
    assert "Gojo vs Sukuna who would win" in yt["tags"] and len(yt["tags"]) <= 500


def test_common_names_and_franchise():
    assert seo.short("Naruto Uzumaki") == "Naruto" and seo.short("Son Goku") == "Goku"
    assert seo.short("Monkey D. Luffy") == "Luffy" and seo.short("Kakashi Hatake") == "Kakashi"
    r = seo.build({"kind": "race", "names": ["Naruto Uzumaki", "Son Goku"]})
    assert r["youtube"]["title"].startswith("Naruto vs Goku")
    assert "#naruto" in r["youtube"]["description"]


def test_seo_box_on_pages(cfg):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    for d, name, meta in ((fusion.out_dir(), "domain_1", {"kind": "domain", "names": ["Son Goku", "Vegeta"],
                                                        "winner": "Son Goku", "title": "t"}),
                          (fusion.out_dir(), "fusion_2", {"title": "Goku every form", "tiers": ["Base", "UI"]}),
                          (battle.out_dir(), "battle_3", {"title": "Which anime character wins?",
                                                          "fighters": ["Satoru Gojo", "Monkey D. Luffy"]})):
        (d / f"{name}.mp4").write_bytes(b"x")
        (d / f"{name}.json").write_text(json.dumps(meta), encoding="utf-8")
    with TestClient(appmod.app) as c:
        for url in ("/battle", "/fusion", "/m"):
            page = c.get(url).text
            assert "SEO" in page and "seoCopy" in page, url
        assert "Goku vs Vegeta: Who Wins?" in c.get("/battle").text
