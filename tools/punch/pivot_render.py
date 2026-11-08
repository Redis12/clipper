"""Rendu d'une animation Pivot Animator (.piv) en Python (07/11, Goku Pivot fourni par l'utilisateur).

Lecture du .piv : décodeur de StykAnimate (GPL-3, github.com/filippocalippo/StykAnimate-App, cloné hors du dépôt dans
/tmp/styk ; on l'appelle comme un outil, on ne le copie pas). On obtient les types de figures (segments : parent,
longueur, épaisseur, couleur, ligne/cercle/invisible ; polygones de remplissage) et les images clés (objets posés :
racine, angles absolus et longueurs par segment, couleur imposée, ordre de dessin).

python3 tools/punch/pivot_render.py <fichier.piv> <dossier_sortie> [échelle]
→ une image PNG transparente par image clé + planche contact.json/png.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def decode(path, assets=None):
    sys.path.insert(0, "/tmp/styk/codecs")
    import piv_codec
    return piv_codec.decode_piv_file(str(path), assets_dir=assets)


def arc_pts(start, a, L, bend):
    """points d'un segment (courbé si bend ≠ 0), comme Pivot."""
    if abs(bend) < 1e-7:
        return [start, (start[0] + math.cos(a) * L, start[1] + math.sin(a) * L)]
    n = max(2, min(64, int(math.ceil(abs(bend) * 16))))
    r = L / bend
    return [(start[0] + r * (math.sin(a + bend * i / n) - math.sin(a)),
             start[1] + r * (math.cos(a) - math.cos(a + bend * i / n))) for i in range(n + 1)]


def geom(obj, ft, base=None, rot=0.0, ang=None):
    """articulations + points de chaque segment. Longueurs de l'objet seulement si len_flag, courbes (bend)."""
    base = base if base is not None else (obj["root_x"], obj["root_y"])
    pos, pts = {0: base}, {}
    segs = sorted(ft["segments"], key=lambda s: s["segment_id"])
    ang = ang if ang is not None else (obj.get("angles") or [])
    lens, bends = obj.get("lengths") or [], obj.get("bends") or []
    sc = obj.get("scale", 1.0)
    for i, s in enumerate(segs):
        a = (ang[i] if i < len(ang) else s["angle_rad"]) + rot
        L = (lens[i] if obj.get("len_flag") and i < len(lens) else s["length"]) * sc
        b = bends[i] if obj.get("bend_flag") and i < len(bends) else s.get("bend_rad", 0.0)
        q = pos.get(s["parent_id"], base)
        pp = arc_pts(q, a, L, b)
        pos[s["segment_id"]] = pp[-1]
        pts[s["segment_id"]] = pp
    return pos, pts


def joints(obj, ft):
    """positions des articulations (0 = racine) en coordonnées Pivot."""
    return geom(obj, ft)[0]


def poly_points(poly, ft, pos, pts):
    par = {s["segment_id"]: s["parent_id"] for s in ft["segments"]}
    v = [j for j in poly["segment_ids"] if j in pos]
    out = [pos[v[0]]] if v else []
    for k in range(1, len(v) + 1):
        a, b = v[k - 1], v[k % len(v)]
        if par.get(b) == a:
            out += pts[b][1:]
        elif par.get(a) == b:
            out += pts[a][::-1][1:]
        else:
            out.append(pos[b])
    if len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def draw_seg(d, it, ptsP, w, c):
    """dessine un segment (ligne droite/courbe, cercle)."""
    A, B = ptsP[0], ptsP[-1]
    kind = it["segment_kind"]
    if kind in ("line", "squareLine"):
        if len(ptsP) > 2:
            d.line(ptsP, fill=c, width=int(round(w)), joint="curve")
        else:
            d.line((A, B), fill=c, width=int(round(w)))
        if kind == "line":
            for q in (A, B):
                d.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=c)
    elif kind.startswith("circle"):
        cx, cy = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
        r = math.hypot(B[0] - A[0], B[1] - A[1]) / 2
        if kind == "circleClear":
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=int(max(1, w)))
        else:
            d.ellipse((cx - r - w / 2, cy - r - w / 2, cx + r + w / 2, cy + r + w / 2), fill=c)


def render_frame(doc, kf, scale=2.0, size=None, bg=None, offset=(0, 0), crop=None):
    fts = {f["figure_type_id"]: f for f in doc["figure_types"]}
    W = int((size or (doc["canvas_width"], doc["canvas_height"]))[0] * scale)
    H = int((size or (doc["canvas_width"], doc["canvas_height"]))[1] * scale)
    ss = 2
    im = Image.new("RGBA", (W * ss, H * ss), bg or (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    k = scale * ss
    ox, oy = offset

    def P(p):
        return ((p[0] - ox) * k, (p[1] - oy) * k)
    objs = {o["object_slot"]: o for o in kf["objects"]}                # l'ordre de dessin référence les emplacements
    order = kf.get("object_draw_order") or [o["object_slot"] for o in kf["objects"]]
    for uid in order:
        o = objs.get(uid)
        if not o or o.get("opacity", 1) <= 0:
            continue
        ft = fts.get(o["figure_type_id"])
        if not ft:
            continue
        pos, spts = geom(o, ft)
        ov = o.get("color_override_rgb")
        mix = (o.get("color_override_mix") or 0) / 255
        alpha = int(255 * o.get("opacity", 1.0))

        def col(c, mix=mix, ov=ov):
            c = c or (0, 0, 0)
            if ov is not None and mix > 0:
                c = [int(c[i] * (1 - mix) + ov[i] * mix) for i in range(3)]
            return tuple(c) + (alpha,)
        items = [("seg", s["z_order"], s) for s in ft["segments"]] + [("poly", p["z_order"], p) for p in ft["polyfills"]]
        for kind, _, it in sorted(items, key=lambda x: x[1]):
            if kind == "poly":
                pp = [P(q) for q in poly_points(it, ft, pos, spts)]
                if len(pp) >= 3:
                    d.polygon(pp, fill=col(it["color_rgb"]))
                continue
            if not it.get("visible", True) and it["segment_kind"] == "line":
                continue
            w = max(1.0, it["thickness"] * k * o.get("scale", 1.0))
            draw_seg(d, it, [P(q) for q in spts[it["segment_id"]]], w, col(it["color_rgb"]))
    out = im.resize((W, H), Image.LANCZOS)
    if crop:
        out = out.crop(out.getbbox() or (0, 0, W, H))
    return out


if __name__ == "__main__":
    src, outd = Path(sys.argv[1]), Path(sys.argv[2])
    sc = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    outd.mkdir(parents=True, exist_ok=True)
    doc = decode(src, outd / "assets")
    json.dump({k: doc[k] for k in ("canvas_width", "canvas_height", "fps", "total_output_frames")},
              open(outd / "info.json", "w"))
    frames = []
    for i, kf in enumerate(doc["keyframes"]):
        im = render_frame(doc, kf, sc, bg=(255, 255, 255, 255))
        im.save(outd / f"key_{i:03d}.png")
        frames.append(im)
    w, h = frames[0].size
    cols = 4
    sheet = Image.new("RGB", (cols * w // 2, ((len(frames) + cols - 1) // cols) * h // 2), (255, 255, 255))
    for i, f in enumerate(frames):
        sheet.paste(f.resize((w // 2, h // 2)), ((i % cols) * w // 2, (i // cols) * h // 2))
    sheet.save(outd / "contact.png")
    print(len(frames), "images clés")


# ============================================================================ marionnette (rig) Pivot → moteur stickman
class PivotActor:
    """Un perso Pivot (ensemble d'objets joints) animé comme une marionnette :
    les « os » (objets à 1 segment) reçoivent les angles absolus des poses `stickanim.P` (par rôle), tous les objets
    décoratifs (vêtements, cheveux, mains…) suivent l'os auquel ils sont accrochés. Même interface que stickanim.Actor.draw."""

    def __init__(self, doc, kf_index, root_slot, roles, scale=1.6, flip=False, native_left=False):
        import stickanim as sa
        self.sa = sa
        kf = doc["keyframes"][kf_index]
        self.fts = {f["figure_type_id"]: f for f in doc["figure_types"]}
        objs = {o["object_slot"]: o for o in kf["objects"]}
        par = {}
        for o in kf["objects"]:
            j = o.get("join")
            if j:
                par[o["object_slot"]] = (j["target_object_slot"], j["target_handle_id"])

        def top(s):
            while s in par:
                s = par[s][0]
            return s
        self.slots = [s for s in objs if top(s) == root_slot]
        self.objs = {s: objs[s] for s in self.slots}
        self.par = {s: par[s] for s in self.slots if s in par}
        order = kf.get("object_draw_order") or self.slots
        self.order = [s for s in order if s in self.objs]
        # ordre de parcours parent → enfants
        kids = {}
        for s, (p, h) in self.par.items():
            kids.setdefault(p, []).append(s)
        self.tree = []

        def walk(s):
            self.tree.append(s)
            for c in kids.get(s, []):
                walk(c)
        walk(root_slot)
        self.root = root_slot
        # objets « mous » (mèches de cheveux…) : enfants de la tête, ignorés pour poser le perso au sol
        hd = roles.get("head")
        self.soft = set()

        def mark(s_, inside):
            if inside:
                self.soft.add(s_)
            for c in kids.get(s_, []):
                mark(c, inside or (s_ == hd))
        mark(root_slot, False)
        self.roles, self.scale, self.flip = roles, scale, flip
        self.mirror = native_left
        self.off = {}
        # position de repos : on retourne tout le perso pour qu'il regarde à droite (convention des poses)
        rest = self._joints({})
        hip = rest[root_slot][0]
        self.cx = hip[0]
        self.mirror = native_left
        self.rest_ang = {}
        for s in self.slots:
            o = self.objs[s]
            self.rest_ang[s] = [self._m_ang(a) for a in (o.get("angles") or [])]
        self.hip0 = (hip[0], hip[1])
        # décalage réel entre la poignée du parent et la racine de l'enfant (les objets ne sont pas toujours collés pile)
        self.off = {}
        for c, (pp, h) in self.par.items():
            hb = rest[pp].get(h, rest[pp][0])
            dx, dy = self.objs[c]["root_x"] - hb[0], self.objs[c]["root_y"] - hb[1]
            self.off[c] = (-dx if self.mirror else dx, dy)
        self.last = None

    def _m_ang(self, a):
        return math.pi - a if self.mirror else a

    def _joints(self, rot, angles=None):
        """positions des articulations de chaque objet ; rot = {slot: rotation (rad)} ; angles = angles de repos."""
        J, self._pts = {}, {}
        for s in self.tree:
            o = self.objs[s]
            ft = self.fts[o["figure_type_id"]]
            if s in self.par:
                p, h = self.par[s]
                hb = J[p].get(h, J[p][0])
                off = self.off.get(s, (0.0, 0.0)) if angles is not None else (0.0, 0.0)
                rp = rot.get(p, 0.0)
                base = (hb[0] + off[0] * math.cos(rp) - off[1] * math.sin(rp),
                        hb[1] + off[0] * math.sin(rp) + off[1] * math.cos(rp))
            else:
                base = (o["root_x"], o["root_y"]) if angles is None else (0.0, 0.0)
            ang = angles.get(s) if angles is not None else None
            if self.mirror and angles is not None:
                o = dict(o, bends=[-x for x in (o.get("bends") or [])])
                ft = dict(ft, segments=[dict(g, bend_rad=-g.get("bend_rad", 0.0)) for g in ft["segments"]])
            f = (getattr(self, "lscale", None) or {}).get(s)
            if f and angles is not None:                      # raccourci (membre vu de face) : longueurs × f
                segs = sorted(ft["segments"], key=lambda q: q["segment_id"])
                L0 = o.get("lengths") if o.get("len_flag") else None
                o = dict(o, len_flag=1, lengths=[(L0[i] if L0 and i < len(L0) else g_["length"]) * f
                                                   for i, g_ in enumerate(segs)])
            J[s], self._pts[s] = geom(o, ft, base, rot.get(s, 0.0), ang)
        # bottes retournées (recopie fine) : le morceau et ses enfants en miroir par rapport à l'axe du tibia (la
        # pointe passe de l'autre côté sans sortir de la jambe ; une rotation la décalait et la mettait de travers)
        fm = getattr(self, "fmirror", None) or ()
        if fm and angles is not None:
            kids = {}
            for c, (pp, _h) in self.par.items():
                kids.setdefault(pp, []).append(c)
            for r in fm:
                if r not in J or r not in self.par:
                    continue
                p, h = self.par[r]
                a, b = J[p][0], J[p].get(h, J[p][0])          # axe : racine → poignée du parent (le tibia)
                dx, dy = b[0] - a[0], b[1] - a[1]
                n = math.hypot(dx, dy) or 1.0
                ux, uy = dx / n, dy / n

                def refl(q):
                    vx, vy = q[0] - b[0], q[1] - b[1]
                    t = vx * ux + vy * uy
                    return (b[0] + 2 * t * ux - vx, b[1] + 2 * t * uy - vy)
                stack = [r]
                while stack:
                    t_ = stack.pop()
                    J[t_] = {k_: refl(v) for k_, v in J[t_].items()}
                    self._pts[t_] = {k_: [refl(q) for q in v] for k_, v in self._pts[t_].items()}
                    stack += kids.get(t_, [])
        return J

    def _rot(self, pose):
        """rotation de chaque objet : os des rôles = angle visé − angle de repos ; les autres héritent du parent."""
        tgt = {}
        for role, deg in pose.items():
            s = self.roles.get(role)
            if s is None or s not in self.rest_ang or not self.rest_ang[s]:
                continue
            tgt[s] = -math.radians(deg) - self.rest_ang[s][0]          # angle écran (y vers le bas)
        rot = {}
        ex = getattr(self, "extra", None) or {}                      # rotations en plus par morceau (recopie fine)
        for s in self.tree:
            if s in tgt:
                rot[s] = tgt[s]
            elif s in self.par:
                rot[s] = rot[self.par[s][0]]
            else:
                rot[s] = 0.0
            if s in ex:
                rot[s] += math.radians(ex[s])
        return rot

    def draw(self, canvas, pose, x, y, rot=0.0, hair=None, alpha=1.0, ground=None, trail=0, ghost_col=None,
             shadow_y=None, lift=0.0, record=True, glow=None, tint=None, mask=None):
        R = self._rot(pose)
        J = self._joints(R, angles=self.rest_ang)
        k = self.scale
        pts = [p for s in J for p in J[s].values()]
        minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
        miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
        pad = 30
        ss = 2
        Wd, Hd = int((maxx - minx) * k + 2 * pad), int((maxy - miny) * k + 2 * pad)
        im = Image.new("RGBA", (Wd * ss, Hd * ss), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)

        def P(p):
            return (((p[0] - minx) * k + pad) * ss, ((p[1] - miny) * k + pad) * ss)
        for s in self.order:
            o = self.objs[s]
            if o.get("opacity", 1) <= 0:
                continue
            ft = self.fts[o["figure_type_id"]]
            pos = J[s]
            ov = o.get("color_override_rgb")
            mix = (o.get("color_override_mix") or 0) / 255

            def col(c, mix=mix, ov=ov):
                c = c or (0, 0, 0)
                if ov is not None and mix > 0:
                    c = [int(c[i] * (1 - mix) + ov[i] * mix) for i in range(3)]
                return tuple(c) + (255,)
            items = [("seg", q["z_order"], q) for q in ft["segments"]] + [("poly", q["z_order"], q) for q in ft["polyfills"]]
            for kind, _, it in sorted(items, key=lambda z: z[1]):
                if kind == "poly":
                    ps = [P(q) for q in poly_points(it, ft, pos, self._pts[s])]
                    if len(ps) >= 3:
                        d.polygon(ps, fill=col(it["color_rgb"]))
                    continue
                if not it.get("visible", True) and it["segment_kind"] == "line":
                    continue
                w = max(1.0, it["thickness"] * k * ss * o.get("scale", 1.0))
                draw_seg(d, it, [P(q) for q in self._pts[s][it["segment_id"]]], w, col(it["color_rgb"]))
        im = im.resize((Wd, Hd), Image.LANCZOS)
        hipP = ((J[self.root][0][0] - minx) * k + pad, (J[self.root][0][1] - miny) * k + pad)

        def LP(p):
            return ((p[0] - minx) * k + pad, (p[1] - miny) * k + pad)
        sl = self.roles
        marks = {"fist": LP(J[sl["farm_f"]][1]), "fist_b": LP(J[sl["farm_b"]][1]), "foot": LP(J[sl["shin_f"]][1]),
                 "head": LP(J[sl["head"]][1])}
        if self.flip:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            hipP = (Wd - hipP[0], hipP[1])
            marks = {kk: (Wd - v[0], v[1]) for kk, v in marks.items()}
        org = hipP
        if ground is not None:
            # bas du corps = points des objets durs (pas les cheveux) + demi-épaisseur des traits
            bb = 0.0
            for s_ in self.slots:
                if s_ in self.soft:
                    continue
                o = self.objs[s_]
                th = max((g_["thickness"] for g_ in self.fts[o["figure_type_id"]]["segments"]), default=0) * o.get("scale", 1.0)
                for pts_ in self._pts[s_].values():
                    for q in pts_:
                        bb = max(bb, (q[1] - miny) * k + pad + th * k / 2)
            y = ground - (bb - org[1]) - lift
        if rot:
            im = im.rotate(rot, resample=Image.BICUBIC, center=org, expand=False)
            ca, sa_ = math.cos(math.radians(-rot)), math.sin(math.radians(-rot))
            marks = {kk: (org[0] + (v[0] - org[0]) * ca - (v[1] - org[1]) * sa_,
                          org[1] + (v[0] - org[0]) * sa_ + (v[1] - org[1]) * ca) for kk, v in marks.items()}
        px, py = int(x - org[0]), int(y - org[1])
        if shadow_y is not None:
            dd = ImageDraw.Draw(canvas, "RGBA")
            h = max(0.15, 1 - (shadow_y - y) / 900)
            dd.ellipse((x - 80 * h, shadow_y - 11 * h, x + 80 * h, shadow_y + 11 * h), fill=(0, 0, 0, int(70 * h)))
        if tint is not None:
            c2 = Image.new("RGBA", im.size, tuple(tint) + (0,))
            c2.putalpha(im.getchannel("A"))
            im = c2
        if alpha < 1:
            im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
        if glow:
            from stickfx import rim_glow
            g = rim_glow(im, glow[0], glow[1], glow[2] if len(glow) > 2 else 1.0)
            canvas.paste(g, (px, py), g)
        canvas.paste(im, (px, py), im)
        if mask is not None:
            mask.paste(255, (px, py), im.getchannel("A"))
        info = {kk: (px + v[0], py + v[1]) for kk, v in marks.items()}
        info.update(x=x, y=y, box=(px, py, px + im.width, py + im.height))
        if record:
            self.last = info
        return info


import numpy as np  # noqa: E402

# Goku de base du pack « Goku Pivot By Killeroner » (image clé 0, perso dont la racine est l'objet 0)
ROLES_PIVOT_GOKU = {"hip": 0, "spine": 1, "chest": 2, "neck": 65, "head": 66,
                    "uarm_f": 54, "farm_f": 55, "uarm_b": 37, "farm_b": 38,
                    "thigh_f": 77, "shin_f": 78, "thigh_b": 3, "shin_b": 4}
