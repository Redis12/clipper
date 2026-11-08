"""Rendu d'un stickfigure Stick Nodes (.nodes) en Python (07/11, Goku SSJ1 fourni par l'utilisateur).

Le .nodes est lu par sticknodes-rs (MIT, github.com/vinceTheProgrammer/sticknodes-rs) → JSON (arbre de nœuds).
Chaque nœud : type (RoundedSegment, Segment, Circle, Triangle…), longueur, épaisseur, angle LOCAL (relatif au parent),
couleur. On le pose avec des angles modifiés (dict draw_index → angle local) pour l'animer.

render(fig, overrides, scale) -> image RGBA + positions de chaque nœud (pour coller des effets au poing…).
"""
import json
import math

from PIL import Image, ImageDraw


def load(path):
    return json.load(open(path))


def _col(c):
    return (c["red"], c["green"], c["blue"], c["alpha"])


def layout(fig, overrides=None, flip=False, absolute=None):
    """Positions absolues : liste (draw_index, node, p_parent, p, angle_abs).
    absolute = {draw_index: angle absolu en degrés (0 = droite, 90 = haut, 270 = bas)} : impose l'angle d'un membre,
    ses enfants (mains, cheveux…) suivent avec leur angle local."""
    overrides = overrides or {}
    absolute = absolute or {}
    out = []

    def walk(n, p, ang):
        for c in n["children"]:
            la = overrides.get(c["draw_order_index"], c["local_angle"])
            a = absolute[c["draw_order_index"]] if c["draw_order_index"] in absolute else ang + la
            r = math.radians(a)
            q = (p[0] + math.cos(r) * c["length"], p[1] - math.sin(r) * c["length"])
            out.append((c["draw_order_index"], c, p, q, a))
            walk(c, q, a)
    root = fig["nodes"][0]
    walk(root, (0.0, 0.0), 0.0)
    if flip:
        out = [(i, n, (-a[0], a[1]), (-b[0], b[1]), 180 - g) for i, n, a, b, g in out]
    return out


def render(fig, overrides=None, scale=1.0, flip=False, pad=60, color_map=None, absolute=None):
    lay = layout(fig, overrides, flip, absolute)
    xs = [v for _, _, a, b, _ in lay for v in (a[0], b[0])]
    ys = [v for _, _, a, b, _ in lay for v in (a[1], b[1])]
    maxt = max(n["thickness"] for _, n, *_ in lay)
    x0, y0 = min(xs) - maxt - pad, min(ys) - maxt - pad
    Wd, Hd = int((max(xs) - x0 + maxt + pad) * scale), int((max(ys) - y0 + maxt + pad) * scale)
    ss = 2
    im = Image.new("RGBA", (Wd * ss, Hd * ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    figc = _col(fig["color"])
    k = scale * ss

    def P(p):
        return ((p[0] - x0) * k, (p[1] - y0) * k)
    pos = {}
    ends = {idx: P(b) for idx, n, a, b, ang in lay}
    starts = {idx: P(a) for idx, n, a, b, ang in lay}
    fills = {}                                       # polyfills (08/11) : dessinés juste avant leur nœud d'ancrage
    for pf in fig.get("polyfills") or []:
        fills.setdefault(pf["anchor_node_draw_index"], []).append(pf)
    for idx, n, a, b, ang in sorted(lay, key=lambda x: x[0]):
        for pf in fills.get(idx, []):
            ids = pf["attached_node_draw_indices"]
            pts = [ends[i] for i in ids if i in ends]
            if ids and ids[0] in starts:
                pts = [starts[ids[0]]] + pts
            if len(pts) >= 3:
                pc = _col(pf["color"]) if pf.get("use_polyfill_color", True) else figc
                if color_map:
                    pc = color_map(ids[0], pc)
                d.polygon(pts, fill=pc)
        col = _col(n["color"]) if n["use_segment_color"] else figc
        if color_map:
            col = color_map(idx, col)
        A, B = P(a), P(b)
        w = max(1.0, n["thickness"] * k)
        t = n["node_type"]
        if t in ("RoundedSegment", "Segment"):
            d.line((A, B), fill=col, width=int(w))
            if t == "RoundedSegment":
                for q in (A, B):
                    d.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=col)
        elif t == "Circle":
            c = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
            r = math.hypot(B[0] - A[0], B[1] - A[1]) / 2
            if n["circle_is_hollow"]:
                d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=col, width=int(w))
            else:
                d.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=col)
        elif t == "Triangle":
            dx, dy = B[0] - A[0], B[1] - A[1]
            L = math.hypot(dx, dy) or 1
            px, py = -dy / L * w / 2, dx / L * w / 2
            if n["triangle_upside_down"]:
                d.polygon([(B[0] + px, B[1] + py), (B[0] - px, B[1] - py), A], fill=col)
            else:
                d.polygon([(A[0] + px, A[1] + py), (A[0] - px, A[1] - py), B], fill=col)
        pos[idx] = (P(b)[0] / ss, P(b)[1] / ss)
    out = im.resize((Wd, Hd), Image.LANCZOS)
    origin = ((0 - x0) * scale, (0 - y0) * scale)
    return out, pos, origin


if __name__ == "__main__":
    import sys
    fig = load(sys.argv[1])
    im, pos, o = render(fig, scale=float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
    bg = Image.new("RGBA", im.size, (150, 190, 220, 255))
    bg.alpha_composite(im)
    bg.save(sys.argv[2])
    print(im.size, len(pos))


def lerp_pose(a, b, t):
    """Mélange de 2 poses (angles absolus), par le chemin le plus court."""
    out = {}
    for k in set(a) | set(b):
        x, y = a.get(k, b.get(k)), b.get(k, a.get(k))
        dlt = (y - x + 180) % 360 - 180
        out[k] = x + dlt * t
    return out
