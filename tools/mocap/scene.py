"""Décor commun des séquences Goku (ciel pâle, petit temple de notre invention, sol bleuté)."""
import numpy as np
from PIL import Image, ImageDraw

W, H = 1080, 1920


def make_bg(GY=1250):
    bg = Image.new("RGBA", (W, H))
    a = np.zeros((H, W, 4), np.uint8)
    y = np.linspace(0, 1, H)[:, None]
    top, bot = np.array([150, 205, 235]), np.array([226, 244, 248])
    a[..., :3] = (top * (1 - y[..., None]) + bot * y[..., None]).astype(np.uint8)
    a[..., 3] = 255
    bg = Image.fromarray(a, "RGBA")
    d = ImageDraw.Draw(bg)
    # petit temple au loin (formes simples, de notre invention)
    bx, by = 690, GY - 4
    d.rectangle((bx - 120, by - 70, bx + 120, by), fill=(236, 226, 205))
    d.rectangle((bx - 135, by - 12, bx + 135, by), fill=(206, 196, 176))
    d.pieslice((bx - 70, by - 160, bx + 70, by - 20), 180, 360, fill=(120, 190, 140))
    for k in (-100, 100):
        d.rectangle((bx + k - 14, by - 120, bx + k + 14, by - 40), fill=(236, 226, 205))
        d.pieslice((bx + k - 22, by - 150, bx + k + 22, by - 106), 180, 360, fill=(220, 110, 140))
    for k in range(-90, 100, 30):
        d.rectangle((bx + k - 6, by - 60, bx + k + 6, by - 30), fill=(170, 150, 120))
    d.rectangle((0, GY, W, H), fill=(156, 200, 232))
    d.rectangle((0, GY, W, GY + 5), fill=(120, 168, 210))
    for k in range(14):
        yy = GY + 40 + k * k * 4.2
        d.line((0, yy, W, yy), fill=(146, 190, 224), width=2)
    return bg


