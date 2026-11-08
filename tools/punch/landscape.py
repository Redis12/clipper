"""Beaux décors en parallaxe pour les vidéos stickman (08/11, l'utilisateur : « le terrain ne donne pas envie, il
faut des beaux landscapes »). Vallée façon Dragon Ball à l'heure dorée : ciel en dégradé, soleil + halo + rayons,
nuages doux, 4 chaînes de montagnes de plus en plus brumeuses (perspective atmosphérique, crête éclairée), pitons
rocheux à sommet plat (Namek / désert DBZ), collines vertes avec arbres, prairie texturée au premier plan.
Toutes les couches bouclent sans raccord (bruit périodique) : la caméra peut aller aussi loin qu'elle veut.

    L = Landscape(W, H, ground=1340, theme="golden")
    img = L.frame(cx)            # RGB, cx = position de la caméra (px monde)
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

THEMES = {
    "golden": dict(sky=[(0.0, (38, 84, 178)), (0.42, (96, 150, 222)), (0.62, (255, 196, 150)), (0.7, (255, 224, 170))],
                   haze=(255, 214, 178), sun=(0.7, 0.27), mtn=[(150, 140, 200), (112, 112, 178), (84, 104, 150), (62, 112, 92)],
                   rock=(206, 128, 76), hill=(74, 140, 70), tree=(40, 96, 52), grass=((112, 178, 78), (70, 140, 58)),
                   path=(214, 186, 132)),
    "day": dict(sky=[(0.0, (40, 120, 235)), (0.5, (120, 190, 255)), (0.7, (200, 232, 255))],
                haze=(205, 228, 250), sun=(0.25, 0.22), mtn=[(150, 175, 215), (120, 150, 196), (96, 128, 170), (80, 120, 120)],
                rock=(214, 150, 96), hill=(84, 160, 78), tree=(46, 110, 58), grass=((120, 196, 88), (78, 156, 64)),
                path=(222, 200, 150)),
}


def periodic_noise(n, rnd, octaves=((2, 1.0), (5, 0.5), (11, 0.25), (23, 0.12), (47, 0.06))):
    """courbe 1D de longueur n qui boucle (somme de sinus à nombre entier de périodes)."""
    x = np.arange(n) / n * 2 * math.pi
    y = np.zeros(n)
    for f, a in octaves:
        y += a * np.sin(f * x + rnd.uniform(0, 6.3)) + a * 0.5 * np.sin((f + 1) * x + rnd.uniform(0, 6.3))
    y -= y.min()
    return y / (y.max() or 1)


def soft(im, r):
    """flou sans halo noir : on floute seulement l'alpha, la couleur reste celle des pixels opaques voisins."""
    from scipy import ndimage as ndi
    a = np.asarray(im).copy()
    al = a[..., 3] > 0
    if al.any():
        _, (iy, ix) = ndi.distance_transform_edt(~al, return_indices=True)
        a[..., :3] = a[iy, ix, :3]
    out = Image.fromarray(a)
    out.putalpha(im.getchannel("A").filter(ImageFilter.GaussianBlur(r)))
    return out


def mix(a, b, k):
    return tuple(int(a[i] * (1 - k) + b[i] * k) for i in range(3))


class Landscape:
    def __init__(self, W, H, ground, theme="golden", seed=3):
        self.W, self.H, self.G = W, H, ground
        T = THEMES[theme]
        rnd = random.Random(seed)
        self.sky = self._sky(T)
        self.layers = []                                  # (image RGBA largeur TW+W, TW, parallaxe)
        TW = 3 * W
        self.layers.append((self._clouds(TW, rnd, 0.55, (255, 240, 225)), TW, 0.03))
        for i, (base, amp, par, blur) in enumerate(((ground - 470, 300, 0.06, 3), (ground - 360, 260, 0.11, 2),
                                                     (ground - 250, 220, 0.18, 1), (ground - 150, 170, 0.27, 0))):
            col = mix(T["mtn"][i], T["haze"], 0.32 - i * 0.1)
            self.layers.append((self._ridge(TW, rnd, base, amp, col, T["haze"], blur, snow=(i == 0)), TW, par))
        self.layers.append((self._clouds(TW, rnd, 0.35, (255, 236, 220), low=True), TW, 0.2))
        self.layers.append((self._mesas(TW, rnd, T), TW, 0.42))
        self.layers.append((self._hills(TW * 2, rnd, T), TW * 2, 0.65))
        self.groundL = (self._ground(W * 2, rnd, T), W * 2)

    # ------------------------------------------------------------------ couches
    def _sky(self, T):
        W, H = self.W, self.H
        y = np.linspace(0, 1, H)
        st = T["sky"]
        col = np.zeros((H, 3))
        for i in range(H):
            v = y[i]
            for (a, ca), (b, cb) in zip(st, st[1:] + [(1.01, st[-1][1])]):
                if a <= v <= b:
                    k = (v - a) / max(1e-6, b - a)
                    col[i] = [ca[j] * (1 - k) + cb[j] * k for j in range(3)]
                    break
        im = Image.fromarray(np.repeat(col[:, None, :], W, 1).clip(0, 255).astype(np.uint8)).convert("RGBA")
        sx, sy = T["sun"][0] * W, T["sun"][1] * H
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g = ImageDraw.Draw(glow)
        for r, al in ((620, 60), (420, 80), (260, 110), (150, 150)):
            g.ellipse((sx - r, sy - r, sx + r, sy + r), fill=(255, 236, 190, al))
        glow = glow.filter(ImageFilter.GaussianBlur(80))
        im.alpha_composite(glow)
        rays = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        rd = ImageDraw.Draw(rays)
        for j in range(0):                                 # (rayons retirés : faisaient des bandes)
            an = math.radians(j * 22.5 + 7)
            rd.polygon([(sx, sy), (sx + math.cos(an - .05) * 2200, sy + math.sin(an - .05) * 2200),
                        (sx + math.cos(an + .05) * 2200, sy + math.sin(an + .05) * 2200)], fill=(255, 245, 210, 22))
        im.alpha_composite(rays.filter(ImageFilter.GaussianBlur(30)))
        d = ImageDraw.Draw(im)
        d.ellipse((sx - 95, sy - 95, sx + 95, sy + 95), fill=(255, 246, 214))
        d.ellipse((sx - 80, sy - 80, sx + 80, sy + 80), fill=(255, 251, 232))
        return im

    def _clouds(self, TW, rnd, alpha, col, low=False):
        W, H = self.W, self.H
        im = Image.new("RGBA", (TW, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        n = 9 if not low else 6
        for k in range(n):
            cx = (k + rnd.uniform(0.1, 0.9)) * TW / n
            cy = (rnd.uniform(380, 780) if not low else rnd.uniform(self.G - 640, self.G - 480))
            w = rnd.uniform(260, 520)
            for j in range(7):                              # amas de bulles, base plate
                bx = cx + rnd.uniform(-w * 0.5, w * 0.5)
                r = rnd.uniform(50, 110) * (1.2 if j < 3 else 0.9)
                for off in (-TW, 0, TW):
                    d.ellipse((bx + off - r * 1.4, cy - r, bx + off + r * 1.4, cy + r * 0.55), fill=col + (int(255 * alpha),))
        return self._wrap(soft(im, 12), TW)

    def _ridge(self, TW, rnd, base, amp, col, haze, blur, snow=False):
        H = self.H
        y = base - periodic_noise(TW, rnd) * amp
        top = int(y.min()) - 4
        im = Image.new("RGBA", (TW, H), (0, 0, 0, 0))
        a = np.zeros((H, TW, 4), np.uint8)
        rows = np.arange(H)[:, None]
        mask = rows >= y[None, :]
        # dégradé vertical : crête plus claire (lumière du soir), pied dans la brume
        depth = np.clip((rows - y[None, :]) / 260.0, 0, 1)
        c0 = np.array(mix(col, (255, 236, 205), 0.35), float)
        c1 = np.array(mix(col, haze, 0.45), float)
        rgb = c0[None, None, :] * (1 - depth[..., None]) + c1[None, None, :] * depth[..., None]
        if snow:
            thick = np.clip((base - amp * 0.62 - y) * 0.45, 0, 46) * (1 + 0.25 * np.sin(np.arange(TW) / 23.0))
            sn = (rows - y[None, :]) < thick[None, :]
            rgb[sn] = [246, 240, 236]
        a[..., :3] = rgb.clip(0, 255).astype(np.uint8)
        a[..., 3] = mask * 255
        im = Image.fromarray(a)
        if blur:
            im = soft(im, blur)
        return self._wrap(im, TW)

    def _mesas(self, TW, rnd, T):
        """pitons rocheux à sommet plat (désert de Dragon Ball), éclairés à droite."""
        H, G = self.H, self.G
        im = Image.new("RGBA", (TW, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        x = 200.0
        while x < TW - 300:
            w = rnd.uniform(130, 250)
            h = rnd.uniform(200, 420)
            base = G - 120
            lit = mix(T["rock"], (255, 220, 170), 0.25)
            dark = mix(T["rock"], (70, 50, 70), 0.45)
            top_w = w * rnd.uniform(1.0, 1.35)
            pts = [(x - w * 0.62, base), (x - w * 0.5, base - h * 0.55), (x - top_w / 2, base - h), (x + top_w / 2, base - h),
                   (x + w * 0.5, base - h * 0.5), (x + w * 0.66, base)]
            d.polygon(pts, fill=dark)
            d.polygon([(x + 4, base), (x + 4, base - h + 6), (x + top_w / 2, base - h), (x + w * 0.5, base - h * 0.5),
                       (x + w * 0.66, base)], fill=lit)
            d.polygon([(x - top_w / 2, base - h), (x + top_w / 2, base - h), (x + top_w / 2 - 8, base - h + 14),
                       (x - top_w / 2 + 6, base - h + 12)], fill=mix(lit, (255, 255, 230), 0.3))
            for k in range(3):                               # strates
                yy = base - h * (0.25 + 0.2 * k)
                d.line((x - w * 0.55, yy, x + w * 0.6, yy + 6), fill=mix(dark, (40, 30, 40), 0.2), width=3)
            x += rnd.uniform(380, 900)
        haze = Image.new("RGBA", (TW, H), T["haze"] + (0,))
        hz = np.zeros((H, TW), np.uint8)
        hz[:] = (np.clip((np.arange(H) - (G - 300)) / 200.0, 0, 1) * 70)[:, None].astype(np.uint8)
        haze.putalpha(Image.fromarray(hz))
        im2 = Image.new("RGBA", (TW, H), (0, 0, 0, 0))
        im2.alpha_composite(im)
        im2.alpha_composite(Image.composite(haze, Image.new("RGBA", (TW, H), (0, 0, 0, 0)), im.getchannel("A")))
        return self._wrap(im2, TW)

    def _hills(self, TW, rnd, T):
        H, G = self.H, self.G
        y = G - 60 - periodic_noise(TW, rnd, ((3, 1.0), (7, 0.4), (17, 0.15))) * 130
        a = np.zeros((H, TW, 4), np.uint8)
        rows = np.arange(H)[:, None]
        mask = rows >= y[None, :]
        k = np.clip((rows - y[None, :]) / 140.0, 0, 1)[..., None]
        c0 = np.array(mix(T["hill"], (230, 230, 150), 0.25), float)
        c1 = np.array(mix(T["hill"], (30, 60, 40), 0.25), float)
        a[..., :3] = (c0 * (1 - k) + c1 * k).clip(0, 255).astype(np.uint8)
        a[..., 3] = mask * 255
        im = Image.fromarray(a)
        d = ImageDraw.Draw(im)
        x = 60.0
        while x < TW - 60:                                   # arbres ronds sur les crêtes
            yy = y[int(x)]
            n = rnd.randint(1, 4)
            for j in range(n):
                tx = x + j * rnd.uniform(26, 40)
                if tx >= TW:
                    break
                ty = y[int(tx)] + 6
                r = rnd.uniform(22, 40)
                d.rectangle((tx - 4, ty - r * 0.6, tx + 4, ty + 6), fill=(80, 60, 40))
                d.ellipse((tx - r, ty - r * 2.1, tx + r, ty - r * 0.3), fill=T["tree"])
                d.ellipse((tx - r * 0.55 + r * 0.25, ty - r * 2.0, tx + r * 0.55 + r * 0.25, ty - r * 1.0),
                          fill=mix(T["tree"], (200, 220, 120), 0.3))
            x += rnd.uniform(180, 520)
            _ = yy
        return self._wrap(im, TW)

    def _ground(self, TW, rnd, T):
        H, G = self.H, self.G
        a = np.zeros((H, TW, 4), np.uint8)
        rows = np.arange(H)[:, None]
        k = np.clip((rows - G) / (H - G), 0, 1)[..., None] * np.ones((1, TW, 1))
        g0, g1 = np.array(T["grass"][0], float), np.array(T["grass"][1], float)
        noise = (np.sin(np.arange(TW) / TW * 2 * math.pi * 40)[None, :] * 0.5 +
                 np.sin(np.arange(TW) / TW * 2 * math.pi * 97 + 1.3)[None, :] * 0.5) * 0.04
        rgb = g0 * (1 - k) + g1 * k
        a[..., :3] = rgb.clip(0, 255).astype(np.uint8)
        a[..., 3] = (rows >= G - 2) * 255
        im = Image.fromarray(a)
        d = ImageDraw.Draw(im)
        d.rectangle((0, G - 2, TW, G + 34), fill=T["path"])                        # chemin de terre où ils marchent
        d.line((0, G + 34, TW, G + 34), fill=mix(T["path"], (90, 70, 40), 0.35), width=4)
        for _ in range(160):                                                       # cailloux du chemin
            x, y = rnd.uniform(0, TW), rnd.uniform(G + 4, G + 30)
            r = rnd.uniform(2, 6)
            d.ellipse((x - r, y - r * 0.6, x + r, y + r * 0.6), fill=mix(T["path"], (120, 100, 70), 0.4))
        for _ in range(700):                                                       # touffes d'herbe
            x = rnd.uniform(0, TW)
            y = rnd.uniform(G + 50, H)
            s = 0.6 + (y - G) / (H - G) * 1.6
            c = mix(T["grass"][1], (40, 90, 40), rnd.uniform(0.1, 0.4))
            for j in range(3):
                d.line((x + j * 4 * s, y, x + (j - 1) * 7 * s, y - rnd.uniform(10, 20) * s), fill=c, width=max(2, int(2 * s)))
        for _ in range(220):                                                       # fleurs
            x, y = rnd.uniform(0, TW), rnd.uniform(G + 60, H)
            s = 0.6 + (y - G) / (H - G) * 1.4
            c = rnd.choice([(255, 240, 120), (255, 255, 255), (255, 150, 180), (190, 160, 255)])
            d.ellipse((x - 4 * s, y - 4 * s, x + 4 * s, y + 4 * s), fill=c)
        return self._wrap(im, TW)

    # ------------------------------------------------------------------ outils
    def _wrap(self, im, TW):
        out = Image.new("RGBA", (TW + self.W, self.H), (0, 0, 0, 0))
        out.paste(im, (0, 0))
        out.paste(im.crop((0, 0, self.W, self.H)), (TW, 0))
        return out

    def frame(self, cx, shift_y=0):
        img = self.sky.copy()
        for lay, TW, par in self.layers:
            o = int(cx * par) % TW
            img.alpha_composite(lay.crop((o, 0, o + self.W, self.H)), (0, shift_y) if shift_y else (0, 0))
        gl, TW = self.groundL
        o = int(cx) % TW
        img.alpha_composite(gl.crop((o, 0, o + self.W, self.H)), (0, shift_y) if shift_y else (0, 0))
        return img.convert("RGB")


if __name__ == "__main__":
    import sys
    L = Landscape(1080, 1920, 1340, theme=sys.argv[1] if len(sys.argv) > 1 else "golden")
    ims = [L.frame(x) for x in (0, 2500, 9000)]
    S = Image.new("RGB", (1080 * 3, 1920))
    for i, im in enumerate(ims):
        S.paste(im, (i * 1080, 0))
    S.resize((1620, 960)).save(sys.argv[2] if len(sys.argv) > 2 else "/tmp/land.png")


DECORS = __import__("pathlib").Path(__file__).resolve().parents[2] / "library" / "_decors"


class PixelScene:
    """Décor pixel-art en couches (pack « Nature Landscapes » de l'utilisateur, craftpix, library/_decors/nature/) :
    chaque couche agrandie au plus proche voisin, défile à sa vitesse (parallaxe) et boucle (couches raccordables).
    ground = où les persos posent les pieds : l'image est remontée pour que l'herbe du 1er plan y soit."""

    PAR = {"nature_5": [0.0, 0.04, 0.22, 1.0, 0.5], "nature_2": [0.0, 0.05, 0.3, 1.0],
           "nature_1": [0.0, 0.04, 0.12, 0.2, 0.35, 0.45, 1.0, 1.0], "nature_4": [0.0, 0.1, 0.35, 1.0],
           "nature_3": [0.0, 0.08, 0.3, 1.0]}

    def __init__(self, W, H, ground, name="nature_5", ground_frac=None, scale=None, oy=None):
        self.W, self.H = W, H
        d = DECORS / "nature" / name
        fs = sorted([f for f in d.glob("*.png") if f.stem.isdigit()], key=lambda f: int(f.stem))
        raw = [Image.open(f).convert("RGBA") for f in fs]
        w0, h0 = raw[0].size
        self.s = s = scale or H / h0
        # ligne d'herbe du 1er plan : 1re ligne (en partant du haut) où la dernière couche pleine devient opaque
        if ground_frac is None:
            last = np.asarray(raw[-1] if (np.asarray(raw[-1])[..., 3] > 0).mean() > 0.05 else raw[-2])[..., 3]
            rows = np.nonzero((last > 0).mean(1) > 0.9)[0]
            ground_frac = (rows.min() + 6) / h0 if len(rows) else 0.85
        self.oy = int(ground - ground_frac * h0 * s) if oy is None else int(oy)
        par = self.PAR.get(name, [0.0] + [0.15 * i for i in range(1, len(raw))])
        self.layers = []
        for im, p in zip(raw, par + [1.0] * (len(raw) - len(par))):
            if (np.asarray(im)[..., 3] > 0).mean() < 0.002:
                continue
            big = im.resize((round(w0 * s), round(h0 * s)), Image.NEAREST)
            TW = big.width
            wrap = Image.new("RGBA", (TW + W, big.height), (0, 0, 0, 0))
            wrap.paste(big, (0, 0))
            wrap.paste(big.crop((0, 0, W, big.height)), (TW, 0))
            self.layers.append((wrap, TW, p))
        # au-dessus / en dessous de l'image : on prolonge la 1re et la dernière ligne
        sky = np.asarray(self.layers[0][0])
        self.top_col = tuple(int(v) for v in sky[0, :W, :3].mean(0))
        comp = Image.new("RGBA", (W, self.layers[0][0].height), (0, 0, 0, 0))
        for lay, TW, p in self.layers:
            comp.alpha_composite(lay.crop((0, 0, W, lay.height)))
        self.bot_col = tuple(int(v) for v in np.asarray(comp)[-2, :, :3].mean(0))

    def frame(self, cx, shift=0):
        """shift > 0 : la caméra monte (le décor descend), le haut est complété par la couleur du ciel."""
        img = Image.new("RGBA", (self.W, self.H), self.top_col + (255,))
        hh = self.layers[0][0].height
        oy = self.oy + int(shift)
        if oy >= self.H:
            return img.convert("RGB")
        for lay, TW, p in self.layers:
            o = int(cx * p) % TW
            img.alpha_composite(lay.crop((o, 0, o + self.W, hh)), (0, oy))
        y_end = oy + hh
        if y_end < self.H:                                  # sous l'image du pack : prairie générée (jamais répétée)
            if self.meadow is None:
                self.meadow = self._meadow(self.H)
            mw, TW = self.meadow
            o = int(cx) % TW
            img.alpha_composite(mw.crop((o, 0, o + self.W, self.H - y_end)), (0, y_end))
        return img.convert("RGB")

    meadow = None

    def _meadow(self, need):
        """herbe du 1er plan dessinée au même grain que le pack (pixels de self.s), couleurs prises dans sa dernière
        rangée : rangées d'herbe ondulées de plus en plus grandes vers le bas (perspective), brins, fleurs."""
        s = self.s
        rnd = random.Random(11)
        w0 = self.layers[-1][1] / s                          # largeur de la scène en pixels du pack
        cw = int(round(w0))
        ch = int(need / s) + 2
        greens = [(69, 164, 96), (66, 143, 65), (31, 127, 65), (81, 173, 98), (21, 106, 51)]
        a = np.zeros((ch, cw, 3), np.uint8)
        a[:] = (31, 127, 65)                                  # couleur de la dernière rangée du pack (pas de trou)
        y = -2.0
        row = 0
        xs = np.arange(cw)
        while y < ch:
            hgt = 5 + row * 1.6                               # rangées plus hautes vers le bas
            col = np.array(greens[row % 4], np.uint8)
            dark = np.array(greens[(row % 4 + 2) % 5], np.uint8)
            wav = sum(np.sin(xs / cw * 2 * math.pi * f + rnd.uniform(0, 6.3)) / f ** 0.7 for f in (7, 13, 29, 53))
            edge = y + hgt * 0.35 * (wav - wav.min()) / (np.ptp(wav) or 1)                       # bord irrégulier
            edge -= np.array([rnd.choice((0, 0, 0, 1, 2, 3)) for _ in xs])                          # pointes d'herbe
            for x in range(cw):
                y0 = int(max(0, edge[x]))
                a[y0:, x] = col                                                                      # jusqu'en bas
                if (x * 7 + row) % 5 == 0:
                    a[y0:y0 + 1, x] = dark
            y += hgt
            row += 1
        im = Image.fromarray(a).convert("RGBA")
        d = ImageDraw.Draw(im)
        for _ in range(int(cw * ch / 140)):                   # brins clairs / foncés
            x, yy = rnd.randrange(cw), rnd.randrange(ch)
            hgt = 2 + int(yy / ch * 4)
            c = rnd.choice([(8, 206, 177), (109, 151, 77), (21, 106, 51), (81, 173, 98)])
            d.line((x, yy, x, yy - hgt), fill=c)
        for _ in range(int(cw * ch / 420)):                   # fleurs
            x, yy = rnd.randrange(cw), rnd.randrange(ch)
            c = rnd.choice([(249, 199, 88), (234, 237, 235), (249, 199, 88)])
            if yy / ch > 0.4:
                d.rectangle((x - 1, yy, x + 1, yy), fill=c)
                d.rectangle((x, yy - 1, x, yy + 1), fill=c)
                d.point((x, yy), fill=(255, 240, 160))
            else:
                d.point((x, yy), fill=c)
        sh = np.linspace(1.0, 0.72, ch)[:, None, None]       # un peu plus sombre en bas
        arr = (np.asarray(im)[..., :3] * sh).astype(np.uint8)
        im = Image.fromarray(np.dstack([arr, np.full(arr.shape[:2], 255, np.uint8)]))
        big = im.resize((round(cw * s), round(ch * s)), Image.NEAREST)
        TW = big.width
        wrap = Image.new("RGBA", (TW + self.W, big.height), (0, 0, 0, 0))
        wrap.paste(big, (0, 0))
        wrap.paste(big.crop((0, 0, self.W, big.height)), (TW, 0))
        return wrap, TW
