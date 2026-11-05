"""Prototype « Hydraulic Press » anime : la presse écrase les persos → ils ressortent en plusieurs, forme suivante."""
import math, random, subprocess, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, "/home/claude/clipper")
from clipper.slides import fusion
W, H, FPS = 1080, 1920, 30
CX, CY, RC = 540, 1010, 470
LIB = "/home/claude/clipper/library/_fusion/Goku/"
TIERS = [("Kid Goku.webp", "KID GOKU", (255, 140, 40)), ("1 Base.png", "BASE", (70, 120, 255)),
         ("2 SSJ1.jpg", "SSJ", (255, 215, 60)), ("4 SSJ3.jpg", "SSJ3", (255, 170, 30)),
         ("5 SSJBLUE.jpg", "SSJ BLUE", (60, 210, 255)), ("7 ui.jpg", "ULTRA INSTINCT", (220, 225, 255))]
TITLE2 = "ULTRA INSTINCT GOKU"
SPLIT = 3; MAXB = 320; DUR = 38.0; PERIOD = 3.2
FONT = "/home/claude/clipper/tools/money_sim/fonts/"
F = lambda n, s: ImageFont.truetype(FONT + n + ".woff2", s)
U = np.array([math.cos(-math.pi/4), math.sin(-math.pi/4)])     # axe du rail (bas-gauche → haut-droite)
V = np.array([-U[1], U[0]])
HW, ARM, OPEN, SHUT = 150, 105, 330, 46                          # demi-largeur, bras, ouvert, fermé
def jaw_s(t):
    p = t % PERIOD
    if p < 1.5: return OPEN
    if p < 2.1: f = (p-1.5)/0.6; return OPEN - (OPEN-SHUT)*(f*f)            # se ferme en accélérant
    if p < 2.3: return SHUT
    f = (p-2.3)/0.9; return SHUT + (OPEN-SHUT)*(1-(1-f)**2)
def segments(s):
    out = []
    for sg in (-1, 1):
        b = sg*s*U
        p1, p2 = b + HW*V, b - HW*V
        out += [(p1, p2), (p1, p1 - sg*ARM*U), (p2, p2 - sg*ARM*U)]
    return out
def r_of(n):
    return 78 if n < 4 else 54 if n < 20 else 40 if n < 60 else 30 if n < 150 else 23
class Ball:
    __slots__ = ("p", "v", "tier", "born")
    def __init__(s, p, v, tier, born): s.p, s.v, s.tier, s.born = np.array(p, float), np.array(v, float), tier, born
def simulate(seed):
    rnd = random.Random(seed)
    balls = [Ball((rnd.uniform(-60, 60), rnd.uniform(-60, 60)), (rnd.uniform(-1, 1)*260, rnd.uniform(-1, 1)*260), 0, -9)]
    dt = 1/120; t = 0; frames = []; events = []; prev_s = jaw_s(0); crushed_cycle = -1
    while t < DUR:
        s = jaw_s(t); vs = (s - prev_s)/dt; prev_s = s
        r = r_of(len(balls)); segs = segments(s)
        for b in balls:
            b.p += b.v*dt
            d = np.linalg.norm(b.p)
            if d > RC - r:
                n = b.p/d; b.p = n*(RC - r); b.v -= 2*np.dot(b.v, n)*n
            for a, c in segs:
                ab = c - a; q = a + np.clip(np.dot(b.p - a, ab)/np.dot(ab, ab), 0, 1)*ab
                dv = b.p - q; dd = np.linalg.norm(dv)
                if 1e-6 < dd < r:
                    n = dv/dd; b.p = q + n*r
                    if np.dot(b.v, n) < 0: b.v -= 2*np.dot(b.v, n)*n
                    sp = np.dot(b.v, n); 
                    if vs < 0 and abs(np.dot(n, U)) > 0.7: b.v += n*abs(vs)*0.6      # la mâchoire pousse
            sp = np.linalg.norm(b.v)
            if sp > 900: b.v *= 900/sp
            if sp < 180: b.v *= 180/max(sp, 1e-3)
        cyc = int(t // PERIOD)
        if t % PERIOD >= 2.1 and cyc != crushed_cycle:
            crushed_cycle = cyc; new = []; nc = 0
            for b in balls:
                pu, pv = np.dot(b.p, U), np.dot(b.p, V)
                if abs(pu) < SHUT + 6 and abs(pv) < HW - 4:
                    nc += 1
                    k = SPLIT if len(balls) + len(new) + SPLIT < MAXB else 1
                    for j in range(k):
                        side = rnd.choice((-1, 1))
                        pos = side*V*(HW + 30) + U*rnd.uniform(-30, 30)
                        vel = side*V*rnd.uniform(380, 650) + U*rnd.uniform(-250, 250)
                        new.append(Ball(pos, vel, min(b.tier + 1, len(TIERS) - 1), t))
                else:
                    new.append(b)
            if nc: events.append((t, nc, max(x.tier for x in new)))
            balls = new
        if abs((t*FPS) - round(t*FPS)) < dt*FPS/2:
            frames.append((t, s, [(b.p[0], b.p[1], b.tier, t - b.born) for b in balls]))
        t += dt
    return frames, events
if __name__ == "__main__":
    for seed in range(int(sys.argv[1]) if len(sys.argv) > 1 else 0, 40):
        fr, ev = simulate(seed)
        last = fr[-1][2]; top = sum(1 for b in last if b[3 - 1] == len(TIERS)-1)
        print(seed, len(last), "UI:", top, "events:", [(round(a, 1), b, c) for a, b, c in ev][:14], flush=True)
        if seed >= 3: break

def render(seed, out):
    frames, events = simulate(seed)
    icons = {}
    def icon(tier, r):
        k = (tier, r)
        if k not in icons:
            icons[k] = fusion.icon(TIERS[tier][0] if TIERS[tier][0].startswith('/') else LIB + TIERS[tier][0], 2*r, TIERS[tier][2])
        return icons[k]
    bg = Image.new("RGBA", (W, H), (0, 0, 0, 255)); d = ImageDraw.Draw(bg)
    d.ellipse((CX-RC, CY-RC, CX+RC, CY+RC), outline=(200, 200, 210, 255), width=3)
    e = U*(RC + 120)
    d.line((CX-e[0], CY-e[1], CX+e[0], CY+e[1]), fill=(170, 175, 195, 255), width=4)
    d.text((W/2, 270), "HOW MANY", font=F("anton", 92), anchor="mm", fill=(255, 255, 255, 255))
    l2 = TITLE2; f2 = F("anton", 92)
    while d.textlength(l2, font=f2) > W - 90: f2 = F("anton", f2.size - 4)
    d.text((W/2, 380), l2, font=f2, anchor="mm", fill=TIERS[-1][2] + (255,))
    d.text((W/2, 480), "AT THE END?", font=F("anton", 92), anchor="mm", fill=(255, 255, 255, 255))
    ev_t = [e_[0] for e_ in events]
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    hold = frames[-1]
    for i, (t, s, balls) in enumerate(frames + [hold]*FPS):
        im = bg.copy(); d = ImageDraw.Draw(im)
        r = r_of(len(balls))
        # tremblement à l'écrasement
        sh = 0
        for et in ev_t:
            if 0 <= t - et < 0.25: sh = 10*(1 - (t-et)/0.25)
        ox = int(random.Random(i).uniform(-sh, sh)); oy = int(random.Random(i+7).uniform(-sh, sh))
        for (x, y, tier, age) in balls:
            sc = 1 if age > 0.18 else 0.4 + 0.6*age/0.18
            rr = max(6, int(r*sc))
            ic = icon(tier, r) if rr == r else icon(tier, r).resize((2*rr, 2*rr))
            im.alpha_composite(ic, (int(CX + x - rr + ox), int(CY + y - rr + oy)))
        # mâchoires (blanc « métal », dégradé sur les bras)
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
        for a, c in segments(s):
            pa = (CX + a[0] + ox, CY + a[1] + oy); pc = (CX + c[0] + ox, CY + c[1] + oy)
            od.line((pa, pc), fill=(120, 125, 140, 255), width=22)
            od.line((pa, pc), fill=(245, 245, 250, 255), width=14)
        im.alpha_composite(ov)
        for et in ev_t:
            if 0 <= t - et < 0.12:
                im = Image.blend(im, Image.new("RGBA", im.size, (255, 255, 255, 255)), 0.35*(1-(t-et)/0.12))
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    json.dump({"events": events, "n_end": len(frames[-1][2]), "ui_end": sum(1 for b in frames[-1][2] if b[2] == len(TIERS)-1)},
              open(out + ".json", "w"))
