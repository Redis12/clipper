"""Test : bras élastiques de Luffy (Jet Pistol, Jet Gatling, King Kong Gun) dans une arène façon Domain War."""
import sys, math, random, subprocess
sys.path.insert(0, "/home/claude/clipper")
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
from clipper.slides import faces, vfxgen, render

SP = Path("/tmp/claude-0/-home-claude/21bbeec3-7caf-5d02-b598-3bc7fb9936c1/scratchpad")
W, H, FPS = 1080, 1920, 30
SC = 4                                     # pixel-art agrandi ×4, net
A = SP / "arms"
arm_src = Image.open(A / "1476.png")       # bras + poing, poing à droite
FIST_W = 16
fist = arm_src.crop((arm_src.width - FIST_W, 0, arm_src.width, arm_src.height))
seg = arm_src.crop((20, 0, 50, arm_src.height))          # morceau de bras pur
fist = fist.resize((fist.width * SC, fist.height * SC), Image.NEAREST)
giant = Image.open(A / "1573.png")
giant = giant.resize((giant.width * SC * 2, giant.height * SC * 2), Image.NEAREST)


def haki(im, red=0.0):
    """Haki de l'armement : le poing devient noir brillant, liseré rouge (Haki des rois)."""
    px = im.convert("RGBA")
    r, g, b, a = px.split()
    lum = Image.merge("RGB", (r, g, b)).convert("L")
    dark = Image.merge("RGBA", (lum.point(lambda v: int(v * 0.28 + 10 + 40 * red)), lum.point(lambda v: int(v * 0.18)),
                                lum.point(lambda v: int(v * 0.25 + 12)), a))
    return dark


giant_haki = haki(giant, red=0.6)

lf = Path("/home/claude/clipper/library/_fusion/Luffy/2 Base Luffy.jpg")
icon = faces.head_square(Image.open(lf).convert("RGB"), lf).resize((150, 150), Image.LANCZOS)
mask = Image.new("L", (150, 150), 0)
ImageDraw.Draw(mask).ellipse((0, 0, 149, 149), fill=255)

# arène : grille 26 colonnes, gauche rouge (Luffy), droite violette (Kaido)
gx0, gy0, cell = 43, 260, 38
nx, ny = 26, 33
bg = Image.new("RGBA", (W, H), (12, 10, 22, 255))
d = ImageDraw.Draw(bg)
for j in range(ny):
    for i in range(nx):
        c = (214, 52, 52) if i < 13 else (122, 70, 200)
        x, y = gx0 + i * cell, gy0 + j * cell
        d.rectangle((x + 1, y + 1, x + cell - 2, y + cell - 2), fill=c)
        d.line((x + 1, y + 1, x + cell - 2, y + 1), fill=tuple(min(255, v + 40) for v in c))
fnt = render.font(64)
fsm = render.font(40)
LX, LY = 300, 1000
TX, TY = 820, 980
expl = vfxgen.frames("explosion", 256, (255, 210, 120))
hit = vfxgen.frames("hit", 160, (255, 240, 200))
bolt = vfxgen.frames("lightning", 320, (255, 40, 40))


def draw_arm(img, x1, y1, x2, y2, t, thick=1.0, wob=1.0):
    """Bras élastique de (x1,y1) à (x2,y2) : segment étiré (ondule un peu) + poing net au bout."""
    L = math.hypot(x2 - x1, y2 - y1)
    if L < 20:
        return
    h = int(seg.height * SC * thick)
    body = seg.resize((max(4, int(L - fist.width * 0.6)), h), Image.NEAREST)
    f = fist.resize((int(fist.width * thick), int(fist.height * thick)), Image.NEAREST)
    strip = Image.new("RGBA", (body.width + f.width, max(h, f.height) + 40), (0, 0, 0, 0))
    yy = (strip.height - h) // 2
    # ondulation du caoutchouc : on décale les colonnes du bras
    cols = body.width
    for cx in range(0, cols, 4):
        off = int(math.sin(cx / 38.0 + t * 30) * 8 * wob * (1 - cx / cols))
        strip.alpha_composite(body.crop((cx, 0, min(cols, cx + 4), h)), (cx, yy + off))
    strip.alpha_composite(f, (body.width, (strip.height - f.height) // 2))
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    rs = strip.rotate(-ang, expand=True, resample=Image.NEAREST)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    img.alpha_composite(rs, (int(mx - rs.width / 2), int(my - rs.height / 2)))


def paste_c(img, im, x, y, alpha=1.0):
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    img.alpha_composite(im, (int(x - im.width / 2), int(y - im.height / 2)))


def punch(t, t0, x2, y2, out=0.16, hold=0.10, back=0.18):
    """Position de la main à l'instant t pour un coup lancé à t0 (aller rapide, retour élastique)."""
    a = t - t0
    if a < 0 or a > out + hold + back:
        return None
    if a < out:
        q = 1 - (1 - a / out) ** 3
    elif a < out + hold:
        q = 1.0
    else:
        q = 1 - ((a - out - hold) / back) ** 2
    return LX + (x2 - LX) * q, LY + (y2 - LY) * q, a >= out - 0.02 and a < out + hold


def frame(t):
    img = bg.copy()
    shake = 0
    label = None
    energy = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    # cible
    ImageDraw.Draw(img).ellipse((TX - 70, TY - 70, TX + 70, TY + 70), fill=(60, 30, 90), outline=(190, 140, 255), width=8)
    ImageDraw.Draw(img).text((TX, TY), "KAIDO", font=fsm, anchor="mm", fill=(230, 220, 255))
    if t < 2.4:                                     # JET PISTOL : 2 coups droits
        label = "JET PISTOL"
        for t0 in (0.35, 1.35):
            p = punch(t, t0, TX - 60, TY)
            if p:
                draw_arm(img, LX + 60, LY, p[0], p[1], t, wob=1.0)
                if p[2]:
                    k = int((t - t0 - 0.14) * 30) % len(hit)
                    paste_c(energy, hit[k], TX - 40, TY)
                    shake = 10
    elif t < 5.0:                                   # JET GATLING : rafale
        label = "JET GATLING"
        rr = random.Random(5)
        for i in range(22):
            t0 = 2.6 + i * 0.09
            ty = TY + rr.uniform(-120, 120)
            p = punch(t, t0, TX - 50 + rr.uniform(-30, 20), ty, out=0.07, hold=0.04, back=0.09)
            if p:
                draw_arm(img, LX + 60, LY + rr.uniform(-20, 20), p[0], p[1], t + i, thick=0.85, wob=0.4)
                if p[2]:
                    paste_c(energy, hit[i % len(hit)].resize((110, 110)), p[0] + 20, p[1])
                    shake = 6
    else:                                           # KING KONG GUN : le poing gonfle (Haki) puis frappe
        label = "KING KONG GUN"
        a = t - 5.0
        if a < 1.0:                                 # gonfle derrière Luffy
            s = 0.4 + 0.6 * (a / 1.0)
            g = giant_haki.resize((int(giant_haki.width * s), int(giant_haki.height * s)), Image.NEAREST)
            paste_c(img, g, LX - 120, LY - 40)
            if int(a * 20) % 2 == 0:
                k = int(a * 24) % len(bolt)
                paste_c(energy, bolt[k].resize((300, 300)), LX - 120, LY - 40, 0.9)
        elif a < 1.25:                              # part
            q = (a - 1.0) / 0.25
            x = LX - 120 + (TX - 60 - (LX - 120)) * q ** 1.5
            draw_arm(img, LX + 40, LY, x - 120, LY, t, thick=2.2, wob=0.2)
            paste_c(img, giant_haki, x, LY - 20)
            k = int(a * 24) % len(bolt)
            paste_c(energy, bolt[k].resize((360, 360)), x, LY - 20, 0.8)
        elif a < 2.6:                               # impact
            b = a - 1.25
            k = min(len(expl) - 1, int(b * 24))
            paste_c(energy, expl[k].resize((640, 640)), TX, TY)
            k2 = int(b * 24) % len(bolt)
            paste_c(energy, bolt[k2].resize((520, 520)), TX, TY, max(0, 1 - b))
            if b < 0.4:
                paste_c(img, giant_haki, TX - 60, LY - 20, 1 - b / 0.4)
            shake = int(30 * max(0, 1 - b / 0.8))
    # Luffy
    ring = Image.new("RGBA", (170, 170), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, 169, 169), fill=(230, 60, 60))
    paste_c(img, ring, LX, LY)
    ic = icon.copy().convert("RGBA")
    ic.putalpha(mask)
    paste_c(img, ic, LX, LY)
    # halo de l'énergie
    glow = energy.filter(ImageFilter.GaussianBlur(14))
    img.alpha_composite(glow)
    img.alpha_composite(energy)
    if label:
        dd = ImageDraw.Draw(img)
        dd.text((W / 2, 170), "LUFFY · " + label, font=fnt, anchor="mm", fill=(255, 230, 120), stroke_width=6,
                stroke_fill=(0, 0, 0))
    if shake:
        rs = random.Random(int(t * 1000))
        img = img.transform(img.size, Image.AFFINE, (1, 0, rs.uniform(-shake, shake), 0, 1, rs.uniform(-shake, shake)))
    return img.convert("RGB")


out = SP / "luffy_arms.mp4"
p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                      "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                      "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
for f in range(int(7.8 * FPS)):
    p.stdin.write(frame(f / FPS).tobytes())
p.stdin.close()
p.wait()
print(out)
