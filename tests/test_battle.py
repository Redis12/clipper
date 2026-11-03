"""Vidéo battle : simulation (vols de liens, éliminations), rendu MP4, page web."""
import json

from PIL import Image

from clipper import db
from clipper.slides import battle, library


def test_simulation_steals_and_eliminates(cfg):
    fighters = [{"name": f"P{i}", "image_path": None} for i in range(6)]
    sim = battle.setup(fighters, 1080, 1920, 4, seed=3)
    assert sum(battle.counts(sim)) == 24 and all(c == 4 for c in battle.counts(sim))
    for _ in range(30 * 3 * 25):                      # 25 s simulées
        battle.step(sim, 1 / 90)
    assert sum(battle.counts(sim)) == 24              # toucher = le lien change de main, jamais perdu
    assert sim.events                                  # il y a eu des vols
    assert any(not b.alive for b in sim.balls)         # et des éliminés
    for b in sim.balls:
        if b.alive:
            assert ((b.x - sim.cx) ** 2 + (b.y - sim.cy) ** 2) ** 0.5 <= sim.R + 1   # toujours dans l'arène


def test_generate_small_video(cfg, tmp_path):
    cfg["slides"]["battle"] = {"size": [216, 384], "fps": 10, "safety_seconds": 3, "intro_seconds": 0.2, "links_per": 3}
    img = tmp_path / "a.jpg"
    Image.new("RGB", (400, 400), (200, 50, 50)).save(img)
    p = battle.generate([{"name": "Gojo", "image_path": str(img)}, {"name": "Sukuna", "image_path": None},
                         {"name": "Toji", "image_path": str(img)}], seed=1)
    assert p.exists() and p.stat().st_size > 1000
    meta = json.loads(p.with_suffix(".json").read_text())
    assert meta["winner"] in ("Gojo", "Sukuna", "Toji") and meta["seconds"] > 3
    assert battle.listing()[0]["file"] == p.name


def test_battle_page(cfg, monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    root = library.root()
    for n in ("Gojo Satoru", "Ryomen Sukuna"):
        (root / "Jujutsu Kaisen" / n).mkdir(parents=True)
        Image.new("RGB", (800, 800), (10, 120, 200)).save(root / "Jujutsu Kaisen" / n / "a.jpg")
    library.scan()
    queued = []
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda label, fn, lane="video": queued.append(label))
    ids = [r["image_id"] for r in battle.roster()]
    assert len(ids) == 2
    with TestClient(appmod.app) as c:
        assert "Gojo Satoru" in c.get("/battle").text
        c.post("/battle", data={"img": [str(i) for i in ids], "title": "Who wins?", "links_per": "6"})
    assert queued and "2 persos" in queued[0]
    assert [f["name"] for f in battle.fighters_from_library(["gojo satoru", "nobody"])] == ["Gojo Satoru"]


def test_duel_then_cut_to_winner(cfg, tmp_path):
    cfg["slides"]["battle"] = {"size": [216, 384], "fps": 10, "intro_seconds": 0.1, "links_per": 6,
                               "duel_seconds": 4, "stall_seconds": 6, "safety_seconds": 60}
    p = battle.generate([{"name": n, "image_path": None} for n in ("A", "B", "C", "D")], seed=2)
    meta = json.loads(p.with_suffix(".json").read_text())
    assert meta["winner"] in "ABCD" and meta["seconds"] < 70        # toujours un gagnant, sans minuteur affiché


def test_min_seconds_option(cfg):
    base = {"size": [216, 384], "fps": 10, "intro_seconds": 0.1, "links_per": 10, "duel_seconds": 2,
            "stall_seconds": 3, "safety_seconds": 120}
    fighters = [{"name": n, "image_path": None} for n in "ABCDEFGH"]
    cfg["slides"]["battle"] = dict(base)
    short = json.loads(battle.generate(fighters, seed=4).with_suffix(".json").read_text())["seconds"]
    cfg["slides"]["battle"] = {**base, "min_seconds": short + 15}
    longer = json.loads(battle.generate(fighters, seed=4).with_suffix(".json").read_text())["seconds"]
    assert longer > short                                   # démarrage lent + duel tenu jusqu'à la durée minimum
