"""Domain War : fiches persos, scénario, victoire totale, vidéo, page Battle."""
import json

from PIL import Image

from clipper.slides import battle, domain, library, movesets


def _sheets(*names):
    return [movesets.parse(f"name: {n}\n" + movesets.PRESETS[n]) for n in names]


def test_presets_valid_and_files_written(cfg):
    for n, body in movesets.PRESETS.items():
        s = movesets.parse(f"name: {n}\n{body}")
        assert s["zone"]["fam"] in movesets.ZONE_FAM and s["secret"]["fam"] in movesets.SECRET_FAM, n
        assert s["passive"]["fam"] in movesets.PASSIVE_FAM and s.get("about"), n
    movesets.ensure_presets()
    assert (movesets.folder() / "Satoru Gojo.txt").exists()
    assert movesets.find("Sukuna")["secret"]["summon"] == "Mahoraga"
    assert movesets.find("Gojo Satoru")["passive"]["fam"] == "infinity"
    # une correction de l'utilisateur n'est jamais écrasée
    p = movesets.folder() / "Satoru Gojo.txt"
    p.write_text(p.read_text(encoding="utf-8").replace("front: Lapse: Blue\n", "front: Purple!!\n"), encoding="utf-8")
    movesets.ensure_presets()
    assert movesets.find("Satoru Gojo")["front"]["name"] == "Purple!!"


def test_unknown_character_without_key_gets_generic(cfg, monkeypatch):
    from clipper import llm
    monkeypatch.setattr(llm, "structured", lambda **kw: (_ for _ in ()).throw(RuntimeError("no key")))
    s = movesets.sheet_for("Some Unknown Guy")
    assert s["zone"]["fam"] == "bomb" and s["secret"]["name"]


def test_scenario_secrets_clash_and_total_victory():
    sheets = _sheets("Satoru Gojo", "Ryomen Sukuna")
    war, dr = domain.make(4, 20, 540, 960, sheets)
    while not domain.finished(war, 20):
        dr.tick()
        for _ in range(4):
            war.step(1 / 120)
    slots = [(e[1], e[2]) for e in dr.events]
    assert sum(1 for _, s in slots if s == "secret") == 2           # chacun son secret
    assert {t for t, s in slots if s == "secret"} == {0, 1}
    assert sum(1 for _, s in slots if s == "zone") >= 2              # choc final : les 2 zones
    assert war.share() in (0.0, 1.0)                                 # jusqu'à la fin : un camp a tout
    assert dr.kos                                                    # le perdant a perdu ses persos


def test_infinity_blocks_and_mahoraga_negates_it():
    sheets = _sheets("Satoru Gojo", "Ryomen Sukuna")
    war, _ = domain.make(1, 20, 540, 960, sheets)
    g = war.mains(0)[0]
    gx, gy = int(g["x"] / war.cell), int(g["y"] / war.cell)
    assert not war.paint(1, gx, gy, war._shields(0))                 # l'Infini arrête tout
    fx = war.launch(1, "secret")                                     # Sukuna invoque Mahoraga
    assert fx.get("broke") == "Infinity" and not war.passive_on(0, "infinity")
    assert any(b["kind"] == "summon" for b in war.balls)
    assert war.paint(1, gx, gy, war._shields(0))


def test_small_video_and_page(cfg, monkeypatch, tmp_path):
    cfg["slides"]["fusion"] = {"vision_faces": False}
    img = tmp_path / "a.jpg"
    Image.new("RGB", (300, 300), (200, 50, 50)).save(img)
    p = domain.generate([{"name": "Satoru Gojo", "image_path": str(img)}, {"name": "Ryomen Sukuna", "image_path": None}],
                        seconds=8, seed=3, W=216, H=384, fps=10)
    meta = json.loads(p.with_suffix(".json").read_text())
    assert p.exists() and meta["winner"] in ("Satoru Gojo", "Ryomen Sukuna") and meta["kind"] == "domain"
    assert any("Hollow Purple" in m or "Unlimited Void" in m or "Red" in m for m in meta["moves"])
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    root = library.root()
    for n in ("Gojo", "Sukuna"):
        (root / "Jujutsu Kaisen" / n).mkdir(parents=True)
        Image.new("RGB", (800, 800), (10, 120, 200)).save(root / "Jujutsu Kaisen" / n / "a.jpg")
    library.scan()
    queued = []
    monkeypatch.setattr(appmod.jobs, "enqueue", lambda label, fn, lane="video": queued.append(label))
    ids = [str(r["image_id"]) for r in battle.roster()]
    with TestClient(appmod.app) as c:
        page = c.get("/battle").text
        assert "Domain War" in page
        c.post("/domain", data={"img": ids, "seconds": "30"})
    assert queued and queued[0].startswith("domain war (")


def test_designed_sfx_from_cc0_samples():
    import numpy as np
    from clipper.slides import sfxdesign
    assert len(list(sfxdesign.ASSETS.glob("*.ogg"))) >= 20
    for fam in ("domain", "shrine", "bomb", "meteor", "beam", "mega_beam", "shots", "timestop", "teleport",
                "summon", "clones", "giant", "ko", "win", "tick"):
        x = sfxdesign.build(fam)
        assert len(x) > 1000 and 0.5 < float(np.max(np.abs(x))) <= 1.0, fam
    assert len(sfxdesign.build("domain")) > len(sfxdesign.build("shots"))      # le domaine résonne longtemps


def test_transformation_and_scripted_comeback(cfg):
    from PIL import Image as Im
    sheets = _sheets("Son Goku", "Vegeta")
    assert sheets[0]["form"] == "_fusion/Goku"
    d = library.root() / "_fusion" / "Goku"
    d.mkdir(parents=True)
    for i, n in enumerate(["Base", "SSJ", "UI"]):
        Im.new("RGB", (40, 40), (i * 80, 0, 0)).save(d / f"{i + 1} {n}.png")
    assert domain.form_image("_fusion/Goku").name == "3 UI.png"          # sa dernière forme
    assert domain.form_image("_fusion/Nobody") is None
    war, _ = domain.make(3, 20, 540, 960, sheets)
    fx = war.launch(0, "secret")                                          # Goku : Ultra Instinct = transformation
    assert fx.get("transform") and war.transformed[0] == 0.0 and war.power[0] > 1
    assert all(b["r0"] > 1.4 for b in war.mains(0))
    import random
    seed = domain.pick_seed(20, 540, 960, sheets, tries=4, rnd=random.Random(1), winner=1, comeback=True)
    r = domain.simulate(seed, 20, 540, 960, sheets, winner=1)
    assert r["winner"] == 1                                               # le scénario est tenu


def test_old_sheet_gets_form_line(cfg):
    p = movesets.folder() / "Son Goku.txt"
    body = "\n".join(l for l in movesets.PRESETS["Son Goku"].splitlines() if not l.startswith("form:"))
    p.write_text("name: Son Goku\n" + body + "\n", encoding="utf-8")
    movesets.ensure_presets()
    assert movesets.find("Goku")["form"] == "_fusion/Goku"


def test_db_mechanics_beam_clash_ki_hp_vanish():
    sheets = _sheets("Son Goku", "Vegeta")
    war, dr = domain.make(5, 20, 540, 960, sheets, 0)
    while not domain.finished(war, 20):
        dr.tick()
        for _ in range(4):
            war.step(1 / 120)
    assert any(e[2] == "clash" for e in dr.events)                       # pas 2 domaines → Beam Clash
    assert war.share() == 1.0                                             # le scénario (Goku) est tenu
    assert war.vanishes                                                   # Ultra Instinct : Vanish
    war2, _ = domain.make(5, 20, 540, 960, sheets)
    v = war2.mains(1)[0]
    war2.damage(v)
    assert v["hp"] == 2 and war2.t - v["hurt"] < 0.01
    war2.damage(v), war2.damage(v)
    assert v["hp"] == 0 and v.get("dies") is not None                     # 3 coups = K.O.
    war2.launch(0, "secret")
    war2.damage(war2.mains(0)[0])
    assert war2.mains(0)[0]["hp"] == 3                                    # transformé : esquive (MISS)


def test_new_sfx_and_optional_clip(cfg):
    from clipper.slides import sfxdesign
    for fam in ("transform", "clash", "vanish", "miss"):
        assert len(sfxdesign.build(fam)) > 1000
    assert domain.clip_for("Son Goku") is None
    d = library.root() / "_domain" / "clips"
    d.mkdir(parents=True)
    (d / "Goku secret.gif").write_bytes(b"x")
    assert domain.clip_for("Son Goku").name == "Goku secret.gif"


def test_attack_images_cutin_and_quick_finish(cfg):
    from PIL import Image as Im, ImageDraw
    fx = library.root() / "_domain" / "fx"
    fx.mkdir(parents=True)
    im = Im.new("RGB", (200, 80), (255, 255, 255))                       # rayon sur fond blanc (jpg)
    ImageDraw.Draw(im).rectangle((10, 30, 190, 50), fill=(0, 200, 255))
    ImageDraw.Draw(im).ellipse((152, 34, 172, 46), fill=(255, 255, 255))   # cœur blanc entouré d'énergie
    im.save(fx / "Kamehameha.jpg")
    spr = domain.fx_sprite("Kamehameha", "Son Goku", "front")
    assert spr is not None and spr.getpixel((0, 0))[3] < 50              # fond blanc détouré
    assert spr.getpixel((spr.width - 25, spr.height // 2))[3] > 200       # cœur gardé
    assert domain.fx_sprite("Nope") is None
    assert domain.clip_window("2-6") == (2.0, 4.0) and domain.clip_window(None) == (0.0, 4.0)
    d = library.root() / "_domain" / "cine" / "Son Goku"
    d.mkdir(parents=True)
    for n in ("Goku Chara", "Goku Aura", "Goku Cutin"):
        Im.new("RGBA", (100, 160), (200, 100, 50, 255)).save(d / f"{n}.png")
    ly = domain.cine_layers("Son Goku", 216, 384)
    assert {"chara", "aura", "cutin"} <= set(ly) and domain.cine_layers("Vegeta", 216, 384) == {}
    sheets = _sheets("Son Goku", "Vegeta")                                # fin rapide : la vague prend tout
    war, dr = domain.make(5, 20, 540, 960, sheets, 0)
    while not domain.finished(war, 20):
        dr.tick()
        for _ in range(4):
            war.step(1 / 120)
    assert dr.wipe_at is not None and war.t - dr.wipe_at < 4.0
