"""Découpe et miniatures sur une vraie vidéo synthétique (ffmpeg requis)."""
from pathlib import Path

import pytest
from PIL import Image

from clipper import cut, db, thumbs
from clipper.util import ffprobe, video_stream


def test_target_size():
    assert cut.target_size(3840, 2160) == (1920, 1080)
    assert cut.target_size(1280, 720) == (1280, 720)      # pas d'upscale
    assert cut.target_size(1080, 1920) == (1920, 1080)    # vertical → pad en 16:9
    assert cut.target_size(854, 480) == (852, 480)


def test_render_frame_accurate_and_loudness(video_in_db):
    cid = db.insert_clip(video_in_db, start=61.32, end=183.72, topic="t", score=1, reason="", status="review")
    out = cut.render(cid)
    info = ffprobe(out)
    v = video_stream(info)
    assert (int(v["width"]), int(v["height"])) == (1280, 720)
    dur = float(info["format"]["duration"])
    assert abs(dur - 122.4) < 0.1, dur
    assert abs(cut.integrated_loudness(out) - (-14)) < 1.0
    assert db.get_clip(cid)["render_needed"] == 0
    mtime = out.stat().st_mtime
    cut.render(cid)                                   # rien à refaire
    assert out.stat().st_mtime == mtime


def test_thumbnail(video_in_db, cfg):
    cid = db.insert_clip(video_in_db, start=30.0, end=200.0, topic="t", score=1, reason="", status="review",
                         thumb_text="Le vrai coût caché")
    p = thumbs.make(cid)
    c = db.get_clip(cid)
    assert len(c["frames"]) == 10 and c["frame_idx"] is not None
    with Image.open(p) as im:   # fermer avant de régénérer : Windows bloque le remplacement sinon
        assert im.size == (1280, 720) and im.format == "JPEG"
    assert p.stat().st_size < 2_000_000
    # Changer d'image recompose sans réextraire
    first = [f["path"] for f in c["frames"]]
    db.update_clip(cid, frame_idx=3)
    thumbs.make(cid)
    assert [f["path"] for f in db.get_clip(cid)["frames"]] == first


def test_best_index_prefers_face_then_sharpness():
    frames = [{"sharp": 900, "face": 0}, {"sharp": 300, "face": 0.02}, {"sharp": 500, "face": 0.05}]
    assert thumbs.best_index(frames) == 2
    assert thumbs.best_index([{"sharp": 1, "face": 0}, {"sharp": 5, "face": 0}]) == 1


@pytest.mark.parametrize("pos", ["bottom-left", "top-right", "center"])
def test_compose_positions(tmp_path, cfg, pos):
    cfg["thumbnail"]["position"] = pos
    src = tmp_path / "f.jpg"
    Image.new("RGB", (1920, 1080), (90, 120, 160)).save(src)
    out = thumbs.compose(src, "Une phrase un peu trop longue pour une ligne", tmp_path / "t.jpg")
    with Image.open(out) as im:
        assert im.size == (1280, 720)
