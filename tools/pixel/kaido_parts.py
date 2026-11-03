import numpy as _np
from PIL import ImageOps as _IO
def _clean(p, scale):
    a = _np.array(Image.open(p).convert("RGBA")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    al = a[..., 3]
    al[((g > r + 25) & (g > b + 25)) & (g > 120)] = 0
    a[..., 1] = _np.minimum(g, _np.maximum(r, b) + 10)
    from scipy import ndimage as _nd
    a[..., 3] = _nd.binary_erosion(al > 0, iterations=1) * 255
    im = Image.fromarray(a.astype(_np.uint8))
    return im.resize((im.width * scale // 2, im.height * scale // 2), Image.NEAREST)
_g = Image.open("/home/claude/clipper/library/_domain/fx/_kaido_sheet/dragon_idle.gif")
K_IDLE = []
for _i in range(_g.n_frames):
    _g.seek(_i); _p = SP / f"kd/idle{_i}.png"; _g.convert("RGBA").save(_p); K_IDLE.append(_IO.mirror(_clean(_p, 5)))
K_BREATH = [_IO.mirror(_clean(SP / f"kd/f{k:02d}.png", 5)) for k in range(4, 15)]
def kaido(img, energy, t):
    """Kaido dragon à droite ; Boro Breath sur Luffy à 6,6 s → Luffy tombe à 7,6 s."""
    y = TY - 40 + math.sin(t * 3) * 14
    if 6.6 <= t < 7.8:
        a = t - 6.6
        fr = K_BREATH[min(4, int(a / 0.4 * 5))] if a < 0.4 else K_BREATH[5 + int(a * 12) % 4]
        paste_c(img, fr, TX + 40 - (fr.width - K_BREATH[0].width) / 2, y)
    else:
        paste_c(img, K_IDLE[int(t * 8) % len(K_IDLE)], TX + 40, y)
