"""Animation Mixamo (Collada .dae, « Without Skin ») → positions 3D par image → bvh.project (poses du moteur)."""
import re
import xml.etree.ElementTree as ET

import numpy as np

import bvh

NS = {"c": "http://www.collada.org/2005/11/COLLADASchema"}


def load(path, t0=0.0, t1=None, fps=24, side=None):
    root = ET.parse(path).getroot()
    anim = {}
    for a in root.iter("{%s}animation" % NS["c"]):
        name = a.get("name")
        if not name:
            continue
        srcs = {s.get("id"): s for s in a.findall("c:source", NS)}
        tin = tout = None
        for sid, s in srcs.items():
            if s.find("c:float_array", NS) is None:
                continue
            arr = np.array(s.find("c:float_array", NS).text.split(), float)
            if sid.endswith("input"):
                tin = arr
            elif "output" in sid:
                tout = arr.reshape(-1, 4, 4)
        if tin is not None and tout is not None:
            anim[name] = (tin, tout)
    vs = root.find(".//c:library_visual_scenes", NS)
    nodes = []

    def walk(n, parent):
        nm = n.get("name") or n.get("id")
        m = n.find("c:matrix", NS)
        rest = np.array(m.text.split(), float).reshape(4, 4) if m is not None else np.eye(4)
        nodes.append((nm, parent, rest))
        me = len(nodes) - 1
        for c in n.findall("c:node", NS):
            walk(c, me)
    for n in vs.iter("{%s}node" % NS["c"]):
        if (n.get("name") or "").endswith("Hips"):
            walk(n, None)
            break
    # positions exactes à chaque image clé, puis rééchantillonnage linéaire (pas d'image en double = pas de saccade)
    tk = max((v[0] for v in anim.values()), key=len)
    keyf = []
    for k in range(len(tk)):
        G = []
        for nm, par, rest in nodes:
            L = rest
            if nm in anim:
                tin, tout = anim[nm]
                L = tout[min(k, len(tout) - 1)]
            G.append(L if par is None else G[par] @ L)
        keyf.append({re.sub(r"^mixamorig[_:]?", "", nm): G[i][:3, 3].copy() for i, (nm, _, _) in enumerate(nodes)})
    T = float(tk[-1])
    t1 = T if t1 is None else min(T, t1)
    frames = []
    for t in np.arange(t0, t1 + 1e-6, 1 / fps):
        j = int(np.clip(np.searchsorted(tk, t, side="right") - 1, 0, len(tk) - 1))
        j2 = min(j + 1, len(tk) - 1)
        u = 0.0 if j2 == j else float((t - tk[j]) / (tk[j2] - tk[j]))
        frames.append({n: keyf[j][n] * (1 - u) + keyf[j2][n] * u for n in keyf[j]})
    return bvh.project(frames, side, fwd0=np.array([0.0, 0.0, 1.0]), follow=False)
