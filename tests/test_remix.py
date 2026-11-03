"""Mini-éditeur : musique sous une vidéo générée."""
import json
import subprocess

from clipper.slides import battle, remix
from clipper.util import ffprobe, require_bin


def _fake_video(path, seconds=3):
    subprocess.run([require_bin("ffmpeg"), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"color=c=blue:s=216x384:d={seconds}", "-f", "lavfi", "-i", f"sine=f=880:d={seconds}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


def _fake_music(path, seconds=1.5):
    subprocess.run([require_bin("ffmpeg"), "-y", "-loglevel", "error", "-f", "lavfi", "-i",
                    f"sine=f=220:d={seconds}", str(path)], check=True)


def test_add_music_keeps_length_and_meta(cfg):
    v = battle.out_dir() / "battle_1.mp4"
    _fake_video(v)
    v.with_suffix(".json").write_text(json.dumps({"winner": "Gojo", "title": "T"}))
    m = remix.music_dir() / "song.mp3"
    _fake_music(m)                                         # plus courte que la vidéo : bouclée
    assert remix.musics()[0]["name"] == "song.mp3"
    out = remix.add_music(v, m, start=0.5, music_volume=0.4)
    info = ffprobe(out)
    assert out.name == "battle_1_music.mp4" and abs(float(info["format"]["duration"]) - 3) < 0.3
    assert {s["codec_type"] for s in info["streams"]} == {"video", "audio"}
    meta = json.loads(out.with_suffix(".json").read_text())
    assert meta["winner"] == "Gojo" and meta["music"] == "song.mp3"
    again = remix.add_music(out, m)                        # refaire depuis la version musique : pas de _music_music
    assert again.name == "battle_1_music.mp4"


def test_music_page(cfg):
    from fastapi.testclient import TestClient
    from clipper.web import app as appmod
    v = battle.out_dir() / "battle_2.mp4"
    _fake_video(v, 2)
    _fake_music(remix.music_dir() / "a.mp3")
    with TestClient(appmod.app) as c:
        page = c.get("/music").text
        assert "battle_2.mp4" in page and "a.mp3" in page
        r = c.post("/music", data={"video": "battle/battle_2.mp4", "music": "a.mp3", "music_volume": "30"},
                   follow_redirects=False)
        assert r.status_code == 303 and "done=battle/battle_2_music.mp4" in r.headers["location"]
        assert c.get("/media/battle/battle_2_music.mp4").status_code == 200
        assert c.get("/music/preview.mp3?name=a.mp3&start=0").status_code == 200
        assert c.post("/music/upload", files={"file": ("x.exe", b"MZ")}).status_code == 400
        bad = c.post("/music", data={"video": "battle/../../etc", "music": "a.mp3"}, follow_redirects=False)
        assert "err=" in bad.headers["location"]


def test_remove_button_archives_video(cfg):
    from fastapi.testclient import TestClient
    from clipper import config
    from clipper.slides import fusion
    from clipper.web import app as appmod
    v = fusion.out_dir() / "domain_7.mp4"
    _fake_video(v, 1)
    v.with_suffix(".json").write_text(json.dumps({"kind": "domain", "names": ["Gojo", "Sukuna"], "winner": "Gojo"}))
    with TestClient(appmod.app) as c:
        assert "domain_7.mp4/remove" in c.get("/battle").text
        assert "domain_7.mp4/remove" in c.get("/m").text
        r = c.post("/media/fusion/domain_7.mp4/remove", headers={"referer": "/battle"}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/battle"
        assert "domain_7.mp4" not in c.get("/battle").text
        assert c.post("/media/fusion/nope.mp4/remove").status_code == 404
    arch = config.data_dir() / "archive" / "fusion"
    assert (arch / "domain_7.mp4").exists() and (arch / "domain_7.json").exists() and not v.exists()
