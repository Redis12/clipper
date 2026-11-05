import math, random, subprocess, sys, bisect
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from sim import simulate
W, H, FPS = 1080, 1920, 30
END = 1.8
import json
CFG = json.load(open(sys.argv[1]))
SEED = CFG["seed"]; OUT = CFG["out"]
START, TARGET = CFG["start"], CFG["target"]
T = float(CFG.get("seconds", 60))
F = lambda n, s: ImageFont.truetype(f"fonts/{n}.woff2", s)
GOLD, GREEN, RED, WHITE = (255, 200, 61), (61, 220, 132), (255, 71, 87), (245, 245, 240)
BG1, BG2 = (6, 18, 13), (12, 34, 24)
L, R = 900, 62
BX, BY = (W - L)//2, 600
hits, path = simulate(SEED, T, r=R, **CFG.get("sim", {}))
N = len(hits); m = CFG.get("mult") or (TARGET/START) ** (1/N)
if CFG.get("mode") == "fib":
    VALS = [START, 2*START]
    while len(VALS) <= N: VALS.append(VALS[-1] + VALS[-2])
else:
    VALS = [START * m**k for k in range(N + 1)]
WIN = VALS[N] >= TARGET * 0.999
LAST = hits[-1][0]
ht = [h[0] for h in hits]
pt = [p[0] for p in path]
def money_at(t):
    k = bisect.bisect_right(ht, t); v = VALS[k]
    if WIN and k == N and not CFG.get("mult") and CFG.get("mode") != "fib": v = TARGET
    return v, k
def fmt(x):
    return f"${x:,.0f}" if x >= 10 else f"${x:,.2f}"
def short(x):
    for d, u in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e4, "K")):
        if x >= d: return f"${x/d:,.1f}{u}"
    return fmt(x)
def fit(d, txt, name, size, maxw):
    f = F(name, size)
    while d.textlength(txt, font=f) > maxw and size > 20:
        size -= 4; f = F(name, size)
    return f
# fond : dégradé + guilloches façon billet + grain
def make_bg():
    y = np.linspace(0, 1, H)[:, None]
    a = np.zeros((H, W, 3), np.float32)
    for c in range(3): a[..., c] = BG1[c] + (BG2[c]-BG1[c]) * (0.5 - 0.5*np.cos(y*math.pi))
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for i in range(60):
        pts = [(x, 300 + i*28 + 18*math.sin(x/37 + i*0.7) + 9*math.sin(x/11 + i)) for x in range(-10, W+10, 6)]
        d.line(pts, fill=(61, 220, 132, 10), width=2)
    im = Image.alpha_composite(im.convert("RGBA"), ov)
    g = (np.random.default_rng(1).normal(0, 7, (H, W, 1))).astype(np.int16)
    arr = np.clip(np.asarray(im.convert("RGB")).astype(np.int16) + g, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr).convert("RGBA")
    d = ImageDraw.Draw(im)
    # boîte
    d.rounded_rectangle((BX-10, BY-10, BX+L+10, BY+L+10), 22, fill=(4, 12, 9, 255), outline=(61, 220, 132, 90), width=3)
    for i in range(1, 15):
        p = i*L/15
        d.line((BX+p, BY, BX+p, BY+L), fill=(61, 220, 132, 18), width=1)
        d.line((BX, BY+p, BX+L, BY+p), fill=(61, 220, 132, 18), width=1)
    return im
BG = make_bg()
def coin(r):
    s = 4; S = r*2*s
    im = Image.new("RGBA", (S+8*s, S+8*s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = S//2 + 4*s
    for i in range(S//2, 0, -s):
        f = i/(S/2); col = tuple(int(a*(0.75+0.35*(1-f))) for a in (255, 196, 48))
        d.ellipse((c-i, c-i, c+i, c+i), fill=col + (255,))
    d.ellipse((c-S//2, c-S//2, c+S//2, c+S//2), outline=(150, 100, 10, 255), width=3*s)
    d.ellipse((c-S//2+7*s, c-S//2+7*s, c+S//2-7*s, c+S//2-7*s), outline=(255, 235, 150, 255), width=2*s)
    d.text((c, c+2*s), "$", font=F("anton", int(S*0.62)), anchor="mm", fill=(140, 90, 0, 255))
    d.text((c-2*s, c), "$", font=F("anton", int(S*0.62)), anchor="mm", fill=(255, 240, 170, 255))
    im = im.resize((im.width//s, im.height//s), Image.LANCZOS)
    glow = Image.new("RGBA", (im.width+80, im.height+80), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow); gd.ellipse((30, 30, glow.width-30, glow.height-30), fill=(255, 200, 61, 90))
    glow = glow.filter(ImageFilter.GaussianBlur(22)); glow.alpha_composite(im, (40, 40))
    return glow
COIN = coin(R)
def pos(t):
    i = bisect.bisect_right(pt, t) - 1; i = max(0, min(i, len(path)-2))
    t0, x0, y0 = path[i]; t1, x1, y1 = path[i+1]
    f = 0 if t1 == t0 else (t - t0)/(t1 - t0)
    return x0 + (x1-x0)*f, y0 + (y1-y0)*f
def center_text(d, y, parts, font):
    w = sum(d.textlength(p, font=font) for p, _ in parts); x = W/2 - w/2
    for p, c in parts:
        d.text((x, y), p, font=font, fill=c, anchor="lm", stroke_width=6, stroke_fill=(0, 0, 0)); x += d.textlength(p, font=font)
rnd = random.Random(3)
bills = [(rnd.uniform(0, W), rnd.uniform(-600, -40), rnd.uniform(-1, 1), rnd.uniform(380, 760), rnd.uniform(-200, 200)) for _ in range(70)]
def frame(t):
    im = BG.copy(); d = ImageDraw.Draw(im)
    tt = min(t, T)
    money, k = money_at(tt)
    left = max(0, math.ceil(T - tt - 1e-9))
    # titre
    center_text(d, 150, [tuple(p) if p[1] != "gold" else (p[0], GOLD) for p in [(a, WHITE if b == "white" else b) for a, b in CFG["title1"]]], F("anton", 104))
    center_text(d, 285, [(CFG["title2"], GOLD)], fit(d, CFG["title2"], "anton", 150, W - 80))
    urgent = tt > T - 10 and t < T
    sc = 1 + (0.08*max(0, 1 - ((tt*1) % 1)*4) if urgent else 0)
    col = RED if urgent else WHITE
    center_text(d, 420, [(f"IN {left} SECOND{'' if left == 1 else 'S'}?", col)], F("anton", int(96*sc)))
    # flash des murs touchés + gains flottants (calque transparent)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    for (th, (hx, hy)) in hits[max(0, k-12):k]:
        a = tt - th
        if a < 0.25:
            al = int(255*(1 - a/0.25))
            if hx in (0, L): d.line((BX+hx, BY+hy-90, BX+hx, BY+hy+90), fill=GOLD + (al,), width=10)
            else: d.line((BX+hx-90, BY+hy, BX+hx+90, BY+hy), fill=GOLD + (al,), width=10)
        if a < 0.8:
            ki = hits.index((th, (hx, hy))); gain = VALS[ki+1] - VALS[ki]
            al = int(255*(1 - a/0.8))
            gx = min(max(BX+hx, BX+120), BX+L-120); gy = min(max(BY+hy, BY+60), BY+L-60) - 70*a
            d.text((gx, gy), "+" + short(gain), font=F("mont900", 46), anchor="mm", fill=(61, 220, 132, al), stroke_width=4, stroke_fill=(0, 0, 0, al))
    for j in range(6, 0, -1):
        tx, ty = pos(max(0, tt - j*0.018))
        rr = R*(1 - j*0.11)
        d.ellipse((BX+tx-rr, BY+ty-rr, BX+tx+rr, BY+ty+rr), fill=(255, 200, 61, int(70*(1-j/7))))
    im.alpha_composite(ov)
    x, y = pos(tt)
    im.alpha_composite(COIN, (int(BX + x - COIN.width/2), int(BY + y - COIN.height/2)))
    d = ImageDraw.Draw(im)
    # compteur
    d.text((W/2, BY+L+70), CFG.get("counter", "MONEY"), font=F("mont900", 40), anchor="mm", fill=(170, 200, 185))
    d.text((W/2, BY+L+150), fmt(money), font=fit(d, fmt(money), "anton", 120, W - 100), anchor="mm", fill=GOLD, stroke_width=6, stroke_fill=(0, 0, 0))
    # barre log 0→1M
    x0, x1, yb = 110, W-110, BY+L+250
    d.rounded_rectangle((x0, yb, x1, yb+26), 13, fill=(20, 40, 30))
    lo, hi = math.log10(START), math.log10(TARGET)
    f = min(1, (math.log10(max(money, START)) - lo)/(hi - lo))
    if f > 0: d.rounded_rectangle((x0, yb, x0 + (x1-x0)*f, yb+26), 13, fill=GREEN)
    for v, lab in CFG["marks"]:
        px = x0 + (x1-x0)*(math.log10(v) - lo)/(hi - lo)
        d.line((px, yb-6, px, yb+32), fill=(255, 255, 255, 120), width=2)
        d.text((px, yb+58), lab, font=F("mont800", 30), anchor="mm", fill=(200, 215, 205))
    d.text((W/2, yb+115), CFG.get("mult_label") or f"×{m:.2f} every bounce", font=F("mont800", 38), anchor="mm", fill=(200, 215, 205))
    # fin
    TE = LAST if WIN else T
    if t >= TE:
        e = t - TE
        if e < 0.15: im = Image.blend(im, Image.new("RGBA", im.size, (255, 255, 255, 255)), 0.85*(1 - e/0.15))
        d = ImageDraw.Draw(im)
        dk = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(dk).rectangle((BX-10, BY-10, BX+L+10, BY+L+10), fill=(0, 0, 0, int(min(1, e/0.3)*150))); im.alpha_composite(dk); d = ImageDraw.Draw(im)
        for (bx, by, rot, vy, vx) in (bills if WIN else []):
            yy = by + vy*e; xx = bx + vx*e*0.3 + 30*math.sin(e*3 + bx)
            if -60 < yy < H+60:
                b = Image.new("RGBA", (90, 44), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
                bd.rounded_rectangle((0, 0, 89, 43), 6, fill=(110, 190, 120, 235), outline=(40, 110, 60, 255), width=3)
                bd.text((45, 22), "$", font=F("anton", 30), anchor="mm", fill=(30, 90, 50))
                b = b.rotate(rot*60 + e*rot*120, expand=True)
                im.alpha_composite(b, (int(xx), int(yy)))
        d = ImageDraw.Draw(im)
        if e > 0.1:
            s = max(1, 1.6 - (e-0.1)*4)
            cd = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(cd).rounded_rectangle((70, 820, W-70, 1240), 30, fill=(0, 0, 0, 200), outline=GOLD, width=4); im.alpha_composite(cd); d = ImageDraw.Draw(im)
            big = CFG["win_big"] if WIN else CFG.get("lose_big", "TIME'S UP!")
            d.text((W/2, 940), big, font=fit(d, big, "anton", int(130*s), W - 180), anchor="mm", fill=GOLD if WIN else RED, stroke_width=7, stroke_fill=(0, 0, 0))
            small = f"with {T - LAST:.2f}s left" if WIN else CFG["lose_small"].format(pct=100*VALS[N]/TARGET, money=short(VALS[N]))
            d.text((W/2, 1070), small, font=F("mont900", 50), anchor="mm", fill=WHITE)
        if e > 0.9:
            cta = CFG["cta"].replace(" 👇", "").replace("👇", "")
            d.text((W/2, 1180), cta, font=fit(d, cta, "mont900", 44, W - 200), anchor="mm", fill=WHITE, stroke_width=4, stroke_fill=(0, 0, 0))
    return im.convert("RGB")
if __name__ == "__main__":
    if len(sys.argv) > 2:
        for t in map(float, sys.argv[2].split(",")):
            frame(t).save(f"prev_{t}.png")
        sys.exit()
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "v_" + OUT.replace(" ", "_")], stdin=subprocess.PIPE)
    n = int((T + END) * FPS)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); p.wait()
    import json; json.dump({"hits": ht, "N": N, "m": m}, open("hits.json", "w"))
