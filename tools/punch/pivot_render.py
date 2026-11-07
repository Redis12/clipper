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


def joints(obj, ft):
    """positions des articulations (0 = racine) en coordonnées Pivot."""
    pos = {0: (obj["root_x"], obj["root_y"])}
    segs = sorted(ft["segments"], key=lambda s: s["segment_id"])
    ang, lens = obj.get("angles") or [], obj.get("lengths") or []
    for i, s in enumerate(segs):
        a = ang[i] if i < len(ang) else s["angle_rad"]
        L = (lens[i] if i < len(lens) else s["length"]) * obj.get("scale", 1.0)
        p = pos.get(s["parent_id"], pos[0])
        pos[s["segment_id"]] = (p[0] + math.cos(a) * L, p[1] + math.sin(a) * L)
    return pos


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
        pos = joints(o, ft)
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
                pts = [P(pos[j]) for j in it["segment_ids"] if j in pos]
                if len(pts) >= 3:
                    d.polygon(pts, fill=col(it["color_rgb"]))
                continue
            s = it
            if not s.get("visible", True) and s["segment_kind"] == "line":
                continue
            A, B = P(pos[s["parent_id"]]), P(pos[s["segment_id"]])
            w = max(1.0, s["thickness"] * k * o.get("scale", 1.0))
            c = col(s["color_rgb"])
            if s["segment_kind"] in ("line", "squareLine"):
                d.line((A, B), fill=c, width=int(round(w)))
                if s["segment_kind"] == "line":
                    for q in (A, B):
                        d.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=c)
            elif s["segment_kind"].startswith("circle"):
                cx, cy = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
                r = math.hypot(B[0] - A[0], B[1] - A[1]) / 2
                if s["segment_kind"] == "circleClear":
                    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=c, width=int(max(1, w)))
                else:
                    d.ellipse((cx - r - w / 2, cy - r - w / 2, cx + r + w / 2, cy + r + w / 2), fill=c)
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
        self.roles, self.scale, self.flip = roles, scale, flip
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
        self.last = None

    def _m_ang(self, a):
        return math.pi - a if self.mirror else a

    def _joints(self, rot, angles=None):
        """positions des articulations de chaque objet ; rot = {slot: rotation (rad)} ; angles = angles de repos."""
        J = {}
        for s in self.tree:
            o = self.objs[s]
            ft = self.fts[o["figure_type_id"]]
            if s in self.par:
                p, h = self.par[s]
                base = J[p].get(h, J[p][0])
            else:
                base = (o["root_x"], o["root_y"]) if angles is None else (0.0, 0.0)
            pos = {0: base}
            segs = sorted(ft["segments"], key=lambda q: q["segment_id"])
            ang = (angles or {}).get(s) if angles is not None else (o.get("angles") or [])
            lens = o.get("lengths") or []
            r = rot.get(s, 0.0)
            for i, sg in enumerate(segs):
                a = (ang[i] if ang and i < len(ang) else sg["angle_rad"]) + r
                L = lens[i] if i < len(lens) else sg["length"]
                q = pos.get(sg["parent_id"], base)
                pos[sg["segment_id"]] = (q[0] + math.cos(a) * L, q[1] + math.sin(a) * L)
            J[s] = pos
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
        for s in self.tree:
            if s in tgt:
                rot[s] = tgt[s]
            elif s in self.par:
                rot[s] = rot[self.par[s][0]]
            else:
                rot[s] = 0.0
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
                    ps = [P(pos[j]) for j in it["segment_ids"] if j in pos]
                    if len(ps) >= 3:
                        d.polygon(ps, fill=col(it["color_rgb"]))
                    continue
                if not it.get("visible", True) and it["segment_kind"] == "line":
                    continue
                A, B = P(pos[it["parent_id"]]), P(pos[it["segment_id"]])
                w = max(1.0, it["thickness"] * k * ss)
                c = col(it["color_rgb"])
                if it["segment_kind"] in ("line", "squareLine"):
                    d.line((A, B), fill=c, width=int(round(w)))
                    if it["segment_kind"] == "line":
                        for q in (A, B):
                            d.ellipse((q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2), fill=c)
                elif it["segment_kind"].startswith("circle"):
                    cx, cy = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
                    r = math.hypot(B[0] - A[0], B[1] - A[1]) / 2
                    d.ellipse((cx - r - w / 2, cy - r - w / 2, cx + r + w / 2, cy + r + w / 2), fill=c)
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
            a = np.asarray(im)[..., 3]
            bottom = np.nonzero(a.max(1) > 0)[0].max()
            y = ground - (bottom - org[1]) - lift
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
