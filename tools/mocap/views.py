"""Les différentes VUES du Goku Pivot (profil, trois-quarts, face, dos) : le fichier .piv contient un tour complet
du perso (images clés 8 à 15, en Ultra Instinct). Même squelette que le Goku de base (mêmes types d'os), donc
les rôles (hanche, bras, jambes…) se retrouvent automatiquement ; les cheveux argentés sont repeints en noir
pour redonner le Goku de base. Vue 0 = le Goku de base de profil (image clé 0).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "punch"))
import pivot_render as pr  # noqa: E402

VIEW_KF = [0, 8, 9, 10, 11, 12, 13, 14, 15]
VIEW_NAMES = ["profil (base)", "profil", "3/4 face", "face", "3/4 face (autre)", "profil (autre)", "3/4 dos", "dos",
              "3/4 dos (autre)"]


def auto_roles(kf):
    objs = {o["object_slot"]: o for o in kf["objects"]}
    par = {o["object_slot"]: o["join"]["target_object_slot"] for o in kf["objects"] if o.get("join")}
    order = {s: i for i, s in enumerate(kf.get("object_draw_order") or list(objs))}
    by = {}
    for s, o in objs.items():
        by.setdefault(o["figure_type_id"], []).append(s)

    def depth(s):
        d = 0
        while s in par:
            s = par[s]
            d += 1
        return d

    def chain(ft):
        return sorted(by.get(ft, []), key=depth)
    trunk = chain(155)
    nh = chain(397)
    r = {"hip": trunk[0], "spine": trunk[1], "chest": trunk[2], "neck": nh[0], "head": nh[1]}

    def limb(ft_a, ft_b):
        pairs = []
        def anc(s):
            out = set()
            while s in par:
                s = par[s]
                out.add(s)
            return out
        for a in by.get(ft_a, []):
            kids = [s for s in by.get(ft_b, []) if a in anc(s)]
            if kids:
                pairs.append((a, kids[0]))
        pairs.sort(key=lambda p: order.get(p[1], 0))           # dessiné en dernier = devant
        return pairs
    legs = limb(156, 157)
    arms = limb(351, 353)
    r["thigh_b"], r["shin_b"] = legs[0]
    r["thigh_f"], r["shin_f"] = legs[-1]
    r["uarm_b"], r["farm_b"] = arms[0]
    r["uarm_f"], r["farm_f"] = arms[-1]
    return r


def _grey(c):
    return bool(c) and max(c) - min(c) < 60 and min(c) > 110


def make_actors(doc, scale):
    acts = []
    for ki in VIEW_KF:
        kf = doc["keyframes"][ki]
        if ki == 0:
            a = pr.PivotActor(doc, 0, 0, pr.ROLES_PIVOT_GOKU, scale=scale)
        else:
            roles = auto_roles(kf)
            root = roles["hip"]
            a = pr.PivotActor(doc, ki, root, roles, scale=scale)
            fts = a.fts
            # cheveux Ultra Instinct (gris clair) → noirs, comme le Goku de base
            for s in a.slots:
                o = a.objs[s]
                ov = o.get("color_override_rgb")
                if (o.get("color_override_mix") or 0) > 0 and _grey(ov):
                    o["color_override_rgb"] = [26, 26, 26]
        acts.append(a)
    return acts
