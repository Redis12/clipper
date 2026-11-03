"""Fusion Battle (façon Suika) : fusions, son qui grossit, rendu MP4, page web."""
import json

import numpy as np
from PIL import Image

from clipper.slides import battle, fusion, library


def _run(sim, seconds, fps=30, sub=6):
    drop_t = 0.0
    while sim.t < seconds and sim.done_at < 0:
        if sim.t >= drop_t and fusion.fill_ratio(sim) < 0.6:
            t = fusion.spawn_tier(sim)
            sim.balls.append(fusion.Ball(t, sim.cx, sim.cy - sim.R + sim.radii[t] + 4, 0, sim.R))
            drop_t = sim.t + fusion.drop_gap(sim, 0.75, 0.32)
        stuck = sim.t - (sim.events[-1][0] if sim.events else 0)
        sim.pull = min(3.0, 0.15 + max(0, stuck - 4) * 0.25 + max(0, fusion.fill_ratio(sim) - 0.5) * 4)
        for _ in range(sub):
            fusion.physics_step(sim, 1 / fps / sub)


def test_identical_icons_merge_into_next_tier(cfg):
    sim = fusion.setup(5, 1080, 1920, seed=1)
    r = sim.radii[0]
    sim.balls = [fusion.Ball(0, sim.cx - r * 0.9, sim.cy), fusion.Ball(0, sim.cx + r * 0.9, sim.cy)]
    fusion.physics_step(sim, 1 / 180)
    assert [b.tier for b in sim.balls] == [1] and sim.events[0][1] == 1 and sim.best == 1


def test_reaches_final_tier_and_stays_in_bowl(cfg):
    for tiers in (4, 7):
        sim = fusion.setup(tiers, 1080, 1920, seed=5)
        _run(sim, 150)
        assert sim.done_at > 0, f"{tiers} niveaux : dernier niveau jamais atteint"
        for b in sim.balls:
            assert ((b.x - sim.cx) ** 2 + (b.y - sim.cy) ** 2) ** 0.5 + sim.radii[b.tier] <= sim.R + 2
    assert sim.radii == sorted(sim.radii) and sim.radii[-1] <= sim.R * 0.41


def test_sound_gets_lower_fatter_longer(cfg, tmp_path):
    base = fusion.load_sound(None)
    s0, s6 = fusion.tier_sound(base, 0, 7), fusion.tier_sound(base, 6, 7)
    assert len(s6) > len(s0) * 2                       # plus lent (plus grave) + écho

    def centroid(x):
        sp = np.abs(np.fft.rfft(x))
        return float((sp * np.fft.rfftfreq(len(x), 1 / fusion.RATE)).sum() / sp.sum())
    assert centroid(s6) < centroid(s0)                 # plus grave
    # bruitage de l'utilisateur (wav)
    w = tmp_path / "meow.wav"
    fusion.write_wav(w, 0.5 * np.sin(np.linspace(0, 400 * np.pi, 8000)).astype(np.float32))
    assert len(fusion.load_sound(w)) > 1000
    p = fusion.preview(str(w), 5)
    assert p.exists() and p.stat().st_size > 10000


def test_chain_folder_and_small_video(cfg, tmp_path):
    cfg["slides"]["fusion"] = {"size": [216, 384], "fps": 10, "substeps": 4, "final_seconds": 0.3,
                               "drop_every": 0.3, "drop_every_min": 0.15}
    d = fusion.chains_dir() / "Goku"
    d.mkdir(parents=True)
    for i, n in enumerate(["Base", "SSJ1", "SSJ2", "SSJ3"]):
        im = Image.new("RGBA", (300, 400), (0, 0, 0, 0))
        im.paste((200, 40 * i, 90, 255), (50, 50, 250, 350))
        im.save(d / f"{i + 1} {n}.png")
    (d / "10 extra.txt").write_text("x")
    assert fusion.chain_list() == [{"name": "Goku", "count": 4}]
    tiers = fusion.tiers_from_chain("Goku")
    assert [t["name"] for t in tiers] == ["Base", "SSJ1", "SSJ2", "SSJ3"]
    p = fusion.generate(tiers, title="Goku", seed=2)
    meta = json.loads(p.with_suffix(".json").read_text())
    assert p.exists() and meta["complete"] and meta["reached"] == "SSJ3"
    assert fusion.listing()[0]["file"] == p.name


def test_fusion_page(cfg, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    root = library.root()
    for n in ("Itadori", "Megumi", "Gojo"):
        (root / "Jujutsu Kaisen" / n).mkdir(parents=True)
        Image.new("RGB", (800, 800), (10, 120, 200)).save(root / "Jujutsu Kaisen" / n / "a.jpg")
    library.scan()
    queued = []
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda label, fn, lane="video": queued.append(label))
    ids = [r["image_id"] for r in battle.roster()]
    with TestClient(appmod.app) as c:
        page = c.get("/fusion").text
        assert "Itadori" in page and "Écouter" in page
        r = c.post("/fusion/sound", files={"file": ("meow.wav", b"RIFF0000WAVEfmt ", "audio/wav")},
                   follow_redirects=False)
        assert r.status_code == 303 and (fusion.sounds_dir() / "meow.wav").exists()
        assert c.post("/fusion/sound", files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 400
        assert "meow.wav" in c.get("/fusion").text
        w = c.get("/fusion/preview.wav?tiers=4")
        assert w.status_code == 200 and w.content[:4] == b"RIFF"
        c.post("/fusion", data={"order": ",".join(str(i) for i in ids), "title": "JJK fusion", "sound": "meow.wav"})
    assert queued and "3 niveaux" in queued[0]


def test_bounce_mode_keeps_icons_moving(cfg):
    sim = fusion.setup(6, 1080, 1920, seed=4, bounce=True)
    _run(sim, 12)
    assert sim.balls
    speeds = [(b.vx ** 2 + b.vy ** 2) ** 0.5 for b in sim.balls]
    assert min(speeds) > sim.speed * 0.4                # personne ne reste figé au fond
    pile = fusion.setup(6, 1080, 1920, seed=4, bounce=False)
    assert pile.g > sim.g and pile.speed == 0           # l'ancien mode « tas » existe toujours (style: pile)


def test_order_file_sets_chain_order(cfg):
    d = fusion.chains_dir() / "Goku2"
    d.mkdir(parents=True)
    for n in ("Base.png", "SSJBLUE.jpg", "SSJGOD.jpg"):
        Image.new("RGB", (50, 50)).save(d / n)
    (d / "ordre.txt").write_text("# du plus petit au plus gros\nBase.png = Base\nSSJGOD = SSJ God\nSSJBLUE.jpg = SSJ Blue\nabsent.png\n",
                                 encoding="utf-8")
    assert [t["name"] for t in fusion.tiers_from_chain("Goku2")] == ["Base", "SSJ God", "SSJ Blue"]
    assert fusion.chain_list() == [{"name": "Goku2", "count": 3}]


def test_order_file_survives_renaming(cfg):
    d = fusion.chains_dir() / "Goku3"
    d.mkdir(parents=True)
    for n in ("1 Base.png", "SSJGOD.jpg", "6 SSJBLUE.jpg"):
        Image.new("RGB", (50, 50)).save(d / n)
    (d / "ordre.txt").write_text("Base.png = Base\nSSJGOD.jpg = God\nSSJBLUE.jpg = Blue\n", encoding="utf-8")
    assert [t["name"] for t in fusion.tiers_from_chain("Goku3")] == ["Base", "God", "Blue"]


def test_head_square_uses_face_box_and_cache(cfg, tmp_path, monkeypatch):
    from clipper import llm
    from clipper.slides import faces
    p = tmp_path / "goku.jpg"
    Image.new("RGB", (400, 800), (255, 255, 255)).save(p)        # perso « en pied » : visage petit, en haut
    calls = []

    def fake(**kw):
        calls.append(1)
        return {"found": True, "x0": 0.4, "y0": 0.1, "x1": 0.6, "y1": 0.2}
    monkeypatch.setattr(llm, "structured", fake)
    im = Image.open(p)
    sq = faces.head_square(im, p)
    assert sq.width == sq.height and abs(sq.width - 80 * 1.9) <= 2   # visage 80×80 px → carré serré autour de la tête
    assert faces.head_square(im, p).size == sq.size and len(calls) == 1      # mémorisé : une seule question
    # pas de clé / erreur → détection locale, jamais de plantage
    monkeypatch.setattr(llm, "structured", lambda **kw: (_ for _ in ()).throw(RuntimeError("no key")))
    q = tmp_path / "b.jpg"
    Image.new("RGB", (300, 900), (200, 200, 200)).save(q)
    sq2 = faces.head_square(Image.open(q), q)
    assert sq2.width == sq2.height


def _chain(name, n):
    d = fusion.chains_dir() / name
    d.mkdir(parents=True)
    for i in range(n):
        Image.new("RGB", (60, 60), (40 * i, 100, 200)).save(d / f"{i + 1} F{i}.png")
    return fusion.tiers_from_chain(name)


def test_race_is_deterministic_and_picks_close_race(cfg):
    from clipper.slides import fusion_race
    cfg["slides"]["fusion"] = {"vision_faces": False}
    a, b = _chain("Goku", 4), _chain("Naruto", 4)
    c = fusion.fcfg()
    r1 = fusion_race.simulate([a, b], 1080, 1920, 42, c)
    r2 = fusion_race.simulate([a, b], 1080, 1920, 42, c)
    assert r1 == r2 and r1["winner"] in (0, 1)        # même graine = même course (on rend celle qu'on a choisie)
    import random
    best = fusion_race.pick_seed([a, b], 1080, 1920, c, tries=4, rnd=random.Random(3))
    assert best["winner"] is not None


def test_race_video_and_page(cfg, monkeypatch):
    from fastapi.testclient import TestClient
    from clipper.slides import fusion_race
    from clipper.web import app as appmod
    cfg["slides"]["fusion"] = {"size": [216, 384], "fps": 10, "substeps": 4, "final_seconds": 0.3,
                               "drop_every": 0.3, "drop_every_min": 0.15, "vision_faces": False}
    a, b = _chain("Goku", 3), _chain("Naruto", 3)
    p = fusion_race.generate([a, b], ["Goku", "Naruto"], seed=5)
    meta = json.loads(p.with_suffix(".json").read_text())
    assert p.exists() and meta["kind"] == "race" and meta["winner"] in ("Goku", "Naruto")
    assert "who transforms first" in meta["title"]
    assert fusion.listing()[0]["file"] == p.name
    queued = []
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda label, fn, lane="video": queued.append(label))
    with TestClient(appmod.app) as c:
        page = c.get("/fusion").text
        assert "Fusion Race" in page and "Naruto vs" not in page
        c.post("/fusion/race", data={"chain_a": "Goku", "chain_b": "Naruto"})
        c.post("/fusion/race", data={"chain_a": "Goku", "chain_b": "Goku"})       # même perso : refusé
    assert queued == ["fusion race (Goku vs Naruto)"]
