"""BVH (base CMU, libre même pour un usage commercial) → poses 2D du moteur stickman, vue de profil.
python3 bvh.py fichier.bvh [début_s fin_s] → liste de (pose, x, lift, facing) à 24 i/s."""
import math
import re

import numpy as np


def parse(path):
    txt = open(path).read()
    head, motion = txt.split("MOTION")
    toks = re.findall(r"[^\s{}]+|[{}]", head)
    joints, stack, i = [], [], 0
    while i < len(toks):
        t = toks[i]
        if t in ("ROOT", "JOINT"):
            joints.append({"name": toks[i + 1], "parent": stack[-1] if stack else None, "ch": [], "end": None})
            i += 2
        elif t == "End":
            joints.append({"name": joints[stack[-1]]["name"] + "_end", "parent": stack[-1], "ch": [], "end": True})
            i += 2
        elif t == "{":
            stack.append(len(joints) - 1)
            i += 1
        elif t == "}":
            stack.pop()
            i += 1
        elif t == "OFFSET":
            joints[stack[-1]]["off"] = np.array([float(x) for x in toks[i + 1:i + 4]])
            i += 4
        elif t == "CHANNELS":
            n = int(toks[i + 1])
            joints[stack[-1]]["ch"] = toks[i + 2:i + 2 + n]
            i += 2 + n
        else:
            i += 1
    lines = motion.strip().splitlines()
    ft = float(lines[1].split(":")[1])
    data = np.array([[float(x) for x in ln.split()] for ln in lines[2:] if ln.strip()])
    return joints, ft, data


def _rot(axis, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    if axis == "X":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "Y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def fk(joints, row):
    """positions 3D de chaque articulation pour une image."""
    pos, rot = {}, {}
    k = 0
    for j, J in enumerate(joints):
        R = np.eye(3)
        t = J.get("off", np.zeros(3)).copy()
        for c in J["ch"]:
            v = row[k]
            k += 1
            if c.endswith("position"):
                t["XYZ".index(c[0])] = v
            else:
                R = R @ _rot(c[0], v)
        p = J["parent"]
        if p is None:
            pos[j], rot[j] = t, R
        else:
            pos[j] = pos[p] + rot[p] @ J.get("off", np.zeros(3))
            rot[j] = rot[p] @ R
    return {joints[j]["name"]: pos[j] for j in pos}


ROLE_J = {"hip": ("Hips", "Spine1"), "spine": ("Hips", "Spine1"), "chest": ("Spine1", "Neck"), "neck": ("Neck", "Head"),
          "head": ("Neck", "Head"),
          "uarm_f": ("LeftArm", "LeftForeArm"), "farm_f": ("LeftForeArm", "LeftHand"),
          "uarm_b": ("RightArm", "RightForeArm"), "farm_b": ("RightForeArm", "RightHand"),
          "thigh_f": ("LeftUpLeg", "LeftLeg"), "shin_f": ("LeftLeg", "LeftFoot"),
          "thigh_b": ("RightUpLeg", "RightLeg"), "shin_b": ("RightLeg", "RightFoot")}


def load(path, t0=0.0, t1=None, fps=24, side=None):
    joints, ft, data = parse(path)
    data = data[1:]                                  # 1re image = pose en T ajoutée par la conversion
    n0 = int(t0 / ft)
    n1 = len(data) if t1 is None else min(len(data), int(t1 / ft))
    step = 1 / fps / ft
    frames = [fk(joints, data[int(i)]) for i in np.arange(n0, n1, step)]
    return project(frames, side)


def project(frames, side=None, fwd0=None, follow=True):
    """positions 3D (Y en haut ; noms Hips, Spine1, Neck, Head, Left/RightArm, …ForeArm, …Hand, …UpLeg, …Leg, …Foot,
    …ToeBase) → (pose, x, lift, facing). x et lift sont en LONGUEURS DE JAMBE (indépendant de l'unité du fichier)."""
    P0 = frames[0]
    leg = float(np.linalg.norm(P0["LeftUpLeg"] - P0["LeftLeg"]) + np.linalg.norm(P0["LeftLeg"] - P0["LeftFoot"]))
    # caméra de profil QUI SUIT LE CORPS : à chaque image, on regarde le perso de côté par rapport à SES hanches
    # (comme un jeu de combat 2D) ; une rotation sur lui-même (coup de pied retourné) devient un demi-tour de l'image.
    def fwd_of(P):
        r = P["RightUpLeg"] - P["LeftUpLeg"] + 0.6 * (P["RightArm"] - P["LeftArm"])
        f = np.cross(np.array([0.0, 1.0, 0.0]), r)
        f[1] = 0
        return f / (np.linalg.norm(f) + 1e-9)
    fws = [fwd_of(P) for P in frames]
    yaw = np.unwrap([math.atan2(f[2], f[0]) for f in fws])
    yaw = np.convolve(np.pad(yaw, 2, mode="edge"), np.ones(5) / 5, "valid")
    y0 = yaw[0]
    # fwd0 = direction de la cible (Mixamo : +Z). Le perso garde son décalage (garde de profil, hanches à 45°) et la
    # caméra ne suit que les rotations par rapport à la 1re image.
    base = math.atan2(fwd0[2], fwd0[0]) if fwd0 is not None else y0
    yaw = yaw - y0 + base
    y0 = base
    if not follow:                                 # caméra fixe, de côté par rapport à la cible : pas de demi-tour
        yaw = np.full_like(yaw, base)
    dirx = np.array([math.cos(y0), 0, math.sin(y0)])          # axe de déplacement à l'écran
    side = side or 1
    out = []
    def low(P):                                    # point le plus bas du corps (pieds, ou dos/mains quand il est au sol)
        return min(v[1] for k, v in P.items() if not k.endswith("_end") and "Top" not in k)
    ys = [low(P) for P in frames]
    ground = np.percentile(ys, 3)
    facing = 1
    for P, yw in zip(frames, yaw):
        f = np.array([math.cos(yw), 0, math.sin(yw)])
        turn = math.cos(yw - y0)
        if turn > 0.25:                                        # dos tourné à plus de ~105° = on retourne l'image
            facing = 1                                         # (hystérésis : pas de clignotement autour de 90°)
        elif turn < -0.25:
            facing = -1

        def p2(name):
            v = P[name] - P["Hips"]
            return (float(v @ f), float(v[1]))
        pose = {}
        for role, (a, b) in ROLE_J.items():
            A, B = p2(a), p2(b)
            pose[role] = math.degrees(math.atan2(B[1] - A[1], B[0] - A[0])) % 360
        # tête : la mocap penche beaucoup la tête (menton rentré du boxeur) ; avec la grosse tête du perso 2D ça cache
        # les bras → on garde 35 % de l'écart avec le buste, plafonné à ±18°
        for k in ("neck", "head"):
            dlt = (pose[k] - pose["chest"] + 180) % 360 - 180
            pose[k] = (pose["chest"] + max(-18, min(18, dlt * 0.35))) % 360
        # hauteur du point le plus bas ; couché, les articulations sont DANS le corps (dos, hanches à ~15 cm du sol) alors
        # que le dessin 2D, lui, a de l'épaisseur → marge plus grande quand ce n'est pas un pied qui est en bas
        lowk = min((k for k in P if not k.endswith("_end") and "Top" not in k), key=lambda k: P[k][1])
        foot = "Foot" in lowk or "Toe" in lowk
        m = 0.12 if foot else 0.45
        lift = (P[lowk][1] - ground) / leg
        lift = 0.0 if lift < m else lift - m
        out.append((pose, float(P["Hips"] @ dirx) * side / leg, lift, facing))
    return out
