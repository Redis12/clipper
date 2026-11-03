"""Test : Kaido en vrai dragon pixel-art (pas une icône) dans l'arène : apparition, vol, Boro Breath, foudre."""
import sys, math, random, subprocess, json
sys.path.insert(0, "/home/claude/clipper")
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from clipper.slides import vfxgen, render

SP = Path("/tmp/claude-0/-home-claude/21bbeec3-7caf-5d02-b598-3bc7fb9936c1/scratchpad")
K = SP / "kd"
W, H, FPS = 1080, 1920, 30


def clean(p, scale):
    """Retire le liseré vert du JPG (despill + bord rogné) puis agrandit en pixel-art net."""
    a = np.array(Image.open(p).convert("RGBA")).astype(int)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    spill = (g > r + 25) & (g > b + 25)
    al[spill & (g > 120)] = 0
    a[..., 1] = np.minimum(g, np.maximum(r, b) + 10)
    from scipy import ndimage
    al = (ndimage.binary_erosion(al > 0, iterations=1) * 255)
    a[..., 3] = al
    im = Image.fromarray(a.astype(np.uint8))
    return im.resize((im.width * scale // 2, im.height * scale // 2), Image.NEAREST)


S = 5                                            # ×2,5
idle = []
g = Image.open("/home/claude/clipper/library/_domain/fx/_kaido_sheet/dragon_idle.gif")
for i in range(g.n_frames):
    g.seek(i)
    fr = g.convert("RGBA")
    tmp = SP / f"kd/idle{i}.png"
    fr.save(tmp)
    idle.append(ImageOps.mirror(clean(tmp, S)))  # tourné vers la gauche (vers Luffy)
breath = [ImageOps.mirror(clean(K / f"f{k:02d}.png", S)) for k in range(4, 15)]
fly = [clean(K / f"f{k:02d}.png", S) for k in range(15, 27)]
bolts = [clean(K / f"f{k:02d}.png", 6) for k in range(30, 37)]

gx0, gy0, cell = 43, 260, 38
bg = Image.new("RGBA", (W, H), (12, 10, 22, 255))
d = ImageDraw.Draw(bg)
for j in range(33):
    for i in range(26):
        c = (214, 52, 52) if i < 13 else (122, 70, 200)
        x, y = gx0 + i * cell, gy0 + j * cell
        d.rectangle((x + 1, y + 1, x + cell - 2, y + cell - 2), fill=c)
        d.line((x + 1, y + 1, x + cell - 2, y + 1), fill=tuple(min(255, v + 40) for v in c))
fnt = render.font(64)
flash = vfxgen.frames("ring", 400, (200, 230, 255))
expl = vfxgen.frames("explosion", 300, (255, 190, 90))


def paste_c(img, im, x, y, alpha=1.0):
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))


def frame(t):
    img = bg.copy()
    energy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    label, shake = None, 0
    if t < 2.0:                                         # apparition : flash, le dragon surgit, reste en l'air
        label = "KAIDO · DRAGON FORM"
        a = t / 0.35
        fr = idle[int(t * 8) % len(idle)]
        y = 900 + math.sin(t * 3) * 18
        if t < 0.35:
            fr = fr.resize((max(2, int(fr.width * a)), max(2, int(fr.height * a))), Image.NEAREST)
        paste_c(img, fr, 760, y)
        if t < 0.6:
            paste_c(energy, flash[min(len(flash) - 1, int(t * 24))], 760, y)
            shake = int(20 * (1 - t / 0.6))
    elif t < 4.6:                                       # il vole autour de l'arène
        label = "KAIDO · FLYING"
        a = t - 2.0
        fr = fly[int(a * 10) % len(fly)]
        x = 540 + math.cos(a * 1.4) * 260
        y = 1000 + math.sin(a * 2.0) * 330
        paste_c(img, fr, x, y)
    elif t < 8.0:                                       # BORO BREATH vers Luffy
        label = "KAIDO · BORO BREATH"
        a = t - 4.6
        if a < 0.8:
            fr = breath[min(4, int(a / 0.8 * 5))]
        elif a < 2.6:
            fr = breath[5 + int(a * 12) % 4]
            shake = 8
        else:
            fr = breath[9 + min(1, int((a - 2.6) * 4))]
        # ancré sur la tête : le souffle part vers la gauche
        paste_c(img, fr, 760 - (fr.width - breath[0].width) / 2, 900)
        if 0.8 < a < 2.6 and int(a * 10) % 3 == 0:
            paste_c(energy, expl[int(a * 24) % len(expl)], 160, 900, 0.9)
    else:                                               # foudre
        label = "KAIDO · THUNDER BAGUA"
        a = t - 8.0
        paste_c(img, idle[int(t * 8) % len(idle)], 760, 900)
        rr = random.Random(int(a * 6))
        for k in range(3):
            bx = 120 + rr.random() * 500
            b_ = bolts[(int(a * 14) + k) % len(bolts)]
            paste_c(energy, b_, bx, 260 + b_.height / 2)
            paste_c(energy, expl[int(a * 24 + k * 3) % len(expl)].resize((160, 160)), bx, 260 + b_.height)
        shake = 10
    glow = energy.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(glow)
    img.alpha_composite(energy)
    ImageDraw.Draw(img).text((W / 2, 170), label, font=fnt, anchor="mm", fill=(180, 220, 255), stroke_width=6,
                             stroke_fill=(0, 0, 0))
    if shake:
        rs = random.Random(int(t * 1000))
        img = img.transform(img.size, Image.AFFINE, (1, 0, rs.uniform(-shake, shake), 0, 1, rs.uniform(-shake, shake)))
    return img.convert("RGB")


out = SP / "kaido_dragon.mp4"
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                      "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                      "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
for f in range(int(9.5 * FPS)):
    p.stdin.write(frame(f / FPS).tobytes())
p.stdin.close()
p.wait()
print(out)
