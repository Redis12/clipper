"""Moteur d'effets : particules, additif/bloom, caméra, flipbook."""
from PIL import Image, ImageDraw

from clipper.slides import fxengine as fx


def test_particles_move_and_die():
    p = fx.Particles(1)
    p.emit(100, 100, 50, speed=(100, 200), life=(0.2, 0.3))
    p.emit(100, 100, 10, kind=fx.EMBER, life=(1, 1))
    assert len(p.p) == 60
    p.step(0.1)
    assert abs(p.p[:, 0] - 100).max() > 1                      # elles bougent
    for _ in range(5):
        p.step(0.1)
    assert len(p.p) == 10 and (p.p[:, 10] == fx.EMBER).all()    # les étincelles sont mortes, braises vivantes
    layer = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    p.draw(layer)
    assert layer.getchannel("A").getbbox()


def test_bloom_adds_light_and_camera_zooms(tmp_path):
    img = Image.new("RGBA", (200, 300), (10, 10, 20, 255))
    e = Image.new("RGBA", (200, 300), (0, 0, 0, 0))
    ImageDraw.Draw(e).ellipse((80, 130, 120, 170), fill=(50, 120, 255, 255))
    out = fx.bloom(img, e)
    assert out.getpixel((100, 150))[2] > 200 and out.getpixel((100, 125))[2] > 20   # halo autour
    assert fx.bloom(img, Image.new("RGBA", (200, 300), (0, 0, 0, 0))) is img
    cam = fx.Camera()
    cam.punch(0, 100, 150, 0.2, 0.5)
    assert cam.apply(out, 0.1).size == (200, 300) and cam.apply(out, 1.0) is out
    frames = [Image.new("RGBA", (20, 20), (i * 40, 0, 0, 255)) for i in range(4)]
    frames[0].save(tmp_path / "boom.gif", save_all=True, append_images=frames[1:])
    assert len(fx.flipbook(tmp_path / "boom.gif")) == 4
    assert fx.chroma(out, 3).size == out.size
