"""Luffy vs Kaido (05/11) : ultis plein écran 9:16 à partir des GIF de l'utilisateur → library/_domain/ulti/.
Fond = l'image floutée/assombrie, devant = l'image agrandie (hauteur 900, recadrée au centre), nom en haut."""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from clipper.slides import render  # noqa: E402

LIB = Path(__file__).resolve().parents[1] / "library" / "_domain"
W, H, FPS = 1080, 1920, 30


def frames_of(src: Path, start: float, end: float, crop_bottom: float = 0.0):
    im = Image.open(src)
    seq, t = [], 0.0
    for i in range(getattr(im, "n_frames", 1)):
        im.seek(i)
        d = (im.info.get("duration") or 100) / 1000
        seq.append((t, im.convert("RGB").copy()))
        t += d
    out, k = [], 0
    tt = start
    while tt < min(end, t):
        while k + 1 < len(seq) and seq[k + 1][0] <= tt:
            k += 1
        f = seq[k][1]
        if crop_bottom:
            f = f.crop((0, 0, f.width, int(f.height * (1 - crop_bottom))))
        out.append(f)
        tt += 1 / FPS
    return out


def compose(f: Image.Image, who: str, move: str, col, i: int, n: int) -> Image.Image:
    bg = f.resize((int(H * f.width / f.height), H), Image.BILINEAR)
    bg = bg.crop(((bg.width - W) // 2, 0, (bg.width - W) // 2 + W, H)).filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg).enhance(0.45)
    fh = 900
    fg = f.resize((int(fh * f.width / f.height), fh), Image.LANCZOS)
    if fg.width > W:
        fg = fg.crop(((fg.width - W) // 2, 0, (fg.width - W) // 2 + W, fh))
    y0 = (H - fh) // 2
    bg.paste(fg, ((W - fg.width) // 2, y0))
    d = ImageDraw.Draw(bg)
    d.rectangle((0, y0 - 6, W, y0), fill=col)
    d.rectangle((0, y0 + fh, W, y0 + fh + 6), fill=col)
    a = min(1.0, i / 6)                                      # le texte arrive en 0,2 s
    d.text((W / 2, y0 - 150), who, font=render.font(64), anchor="mm", fill=(255, 255, 255),
           stroke_width=5, stroke_fill=(0, 0, 0))
    if a > 0:
        fs = render.font(int(92 * (1.25 - 0.25 * a)))
        d.text((W / 2, y0 - 60), move, font=fs, anchor="mm", fill=col, stroke_width=6, stroke_fill=(0, 0, 0))
    return bg


def make(name: str, parts, who: str, move: str, col):
    fr = []
    for src, s, e, cb in parts:
        fr += frames_of(LIB / "ulti_src" / src, s, e, cb)
    out = LIB / "ulti" / f"{name}.mp4"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                          "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    for i, f in enumerate(fr):
        p.stdin.write(compose(f, who, move, col, i, len(fr)).tobytes())
    p.stdin.close()
    p.wait()
    print(out, len(fr) / FPS)


if __name__ == "__main__":
    make("Kaido stage Dragon", [("Kaido/Kaido Transfo en dragon.gif", 0, 9, 0)], "KAIDO", "DRAGON FORM",
         (168, 85, 247))
    make("Kaido Ragnaraku", [("Kaido/Kaido Hybrid Attack.gif", 0, 2.9, 0.24),
                             ("Kaido/Kaido Hybrid Attack.gif", 5.9, 9, 0.24)], "KAIDO", "RAGNARAKU", (168, 85, 247))
    make("Monkey D. Luffy Gear 5", [("Luffy/Gear 5 transformation 3.gif", 0, 9, 0),
                                    ("Luffy/Gear 5 transformation 2.webp", 0, 2.0, 0),
                                    ("Luffy/Gear 5 attaque.webp", 2.0, 4.4, 0)], "LUFFY", "GEAR 5",
         (255, 255, 255))


def clash_still():
    """Image fixe du choc (Haki des rois) : zoom lent, secousse qui décroît, flash, « CLASH! »."""
    import math
    import random
    src = Image.open(LIB / "ulti_src" / "Kaido" / "Kaido Luffy Clash.jpg").convert("RGB")
    src = src.crop((0, int(src.height * 0.2), src.width, src.height))          # sans le logo de la chaîne
    out = LIB / "ulti" / "Kaido clash.mp4"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                          "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    n = int(2.8 * FPS)
    for i in range(n):
        t = i / FPS
        z = 1.0 + 0.12 * t / 2.8
        sh = 26 * math.exp(-t * 2.2)
        rr = random.Random(i)
        fh = int(1000 * z)
        fg = src.resize((int(fh * src.width / src.height), fh), Image.LANCZOS)
        cx = fg.width // 2 + int(rr.uniform(-sh, sh))
        fg = fg.crop((cx - W // 2, 0, cx + W // 2, fh))
        img = compose(src, "", "", (239, 68, 68), 0, 1)
        img.paste(fg, (0, (H - fh) // 2 + int(rr.uniform(-sh, sh))))
        d = ImageDraw.Draw(img)
        a = min(1.0, max(0.0, (t - 0.15) / 0.2))
        if a > 0:
            fs = render.font(int(120 * (1.4 - 0.4 * a)))
            d.text((W / 2, H * 0.2), "CLASH!", font=fs, anchor="mm", fill=(255, 70, 70), stroke_width=8,
                   stroke_fill=(0, 0, 0))
            d.text((W / 2, H * 0.8), "LUFFY vs KAIDO", font=render.font(64), anchor="mm", fill=(255, 255, 255),
                   stroke_width=5, stroke_fill=(0, 0, 0))
        if t < 0.18:                                         # flash blanc d'entrée
            img = Image.blend(img, Image.new("RGB", img.size, (255, 255, 255)), 1 - t / 0.18)
        elif int(t * 10) % 7 == 0:                           # éclairs rouges sur les bords
            img = Image.blend(img, Image.new("RGB", img.size, (255, 40, 40)), 0.18)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    p.wait()
    print(out)


if __name__ == "__main__":
    clash_still()
