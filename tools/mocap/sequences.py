"""Bibliothèque de mouvements recopiés : découpe une recopie image par image (fit.py) en séquences nommées
(« coup de poing », « fente »…), chacune enregistrée à part pour être rejouée par le moteur.
Une séquence = liste d'images {angles des os, sens, dx, dy} ; dx/dy en px de la référence (640×360, Goku Pivot à
640/768), relatifs à la 1re image de la séquence. Planche d'aperçu par séquence + index Markdown.
python3 sequences.py doc.json fit.json[,fit2.json] decoupage.json dossier_sortie
decoupage.json = {"source": "...", "fps": 30, "t0": 19.0, "seq": [["nom", début, fin, "description"], …]}
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "punch"))
import pivot_render as pr  # noqa: E402

ROLES = ["hip", "spine", "chest", "neck", "head", "uarm_f", "farm_f", "uarm_b", "farm_b",
         "thigh_f", "shin_f", "thigh_b", "shin_b"]


def load(path):
    return json.load(open(path))


def play(seq, i):
    """image i d'une séquence → (pose, flip, dx, dy, vue, morceaux, raccourcis, bottes en miroir)"""
    f = seq["frames"][min(i, len(seq["frames"]) - 1)]
    return ({k: f[k] for k in ROLES}, f["flip"], f["dx"], f["dy"], f.get("view", 0), f.get("ex", {}), f.get("ls", {}),
            f.get("fm", []))


if __name__ == "__main__":
    doc = json.load(open(sys.argv[1]))
    R = {}
    for f in sys.argv[2].split(","):
        R.update({int(k): v for k, v in json.load(open(f)).items()})
    # format fit2 : une entrée par pose distincte, avec la liste des images où elle est tenue → une entrée par image
    if any("frames" in v for v in R.values()):
        R = {i: v for v in list(R.values()) for i in v["frames"]}
    cut = json.load(open(sys.argv[3]))
    out = Path(sys.argv[4])
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(HERE))
    import views  # noqa: E402
    ACT = views.make_actors(doc, 0.42)
    index = [f"# Mouvements recopiés\n\nSource : {cut['source']} ({cut['fps']} i/s). Une séquence = un geste.\n",
             "| Séquence | Images | Durée | Description |", "|---|---|---|---|"]
    for name, a, b, desc in cut["seq"]:
        ids = [i for i in range(a, b + 1) if i in R]
        if not ids:
            continue
        x0, y0 = R[ids[0]]["x"], R[ids[0]]["y"]
        frames = [dict({k: round(R[i][k], 2) for k in ROLES}, flip=R[i]["flip"], view=R[i].get("view", 0),
                       ex=R[i].get("ex", {}), ls=R[i].get("ls", {}), fm=R[i].get("fm", []),
                       dx=round(R[i]["x"] - x0, 2), dy=round(R[i]["y"] - y0, 2), ref=i) for i in ids]
        seq = {"name": name, "desc": desc, "fps": cut["fps"], "source": cut["source"],
               "t": [round(cut["t0"] + a / cut["fps"], 2), round(cut["t0"] + b / cut["fps"], 2)], "frames": frames}
        (out / f"{name}.json").write_text(json.dumps(seq))
        # planche : ~8 images de la séquence
        step = max(1, len(frames) // 8)
        mdx = sum(f["dx"] for f in frames) / len(frames)          # planche centrée sur le geste (fente : 150 px)
        cells = []
        for f in frames[::step][:8]:
            c = Image.new("RGBA", (150, 190), (225, 236, 245, 255))
            gg = ACT[f.get("view", 0)]
            gg.flip = f["flip"]
            gg.extra = {int(s): v for s, v in f.get("ex", {}).items()}
            gg.lscale = {gg.roles[k]: v for k, v in f.get("ls", {}).items()}
            gg.fmirror = [int(q) for q in f.get("fm", [])]
            gg.draw(c, {k: f[k] for k in ROLES}, 75 + max(-40.0, min(40.0, (f["dx"] - mdx) * 0.42)), 0, ground=180, record=False)
            gg.extra, gg.lscale, gg.fmirror = {}, {}, []
            ImageDraw.Draw(c).text((3, 3), str(f["ref"]), fill=(200, 0, 0))
            cells.append(c)
        sh = Image.new("RGB", (150 * len(cells), 210), (255, 255, 255))
        for k, c in enumerate(cells):
            sh.paste(c, (k * 150, 20))
        ImageDraw.Draw(sh).text((4, 4), f"{name} — {desc}", fill=(0, 0, 0))
        sh.save(out / f"{name}.png")
        index.append(f"| `{name}` | {a}–{b} | {len(frames) / cut['fps']:.2f} s | {desc} |")
    # l'index garde les autres sources : une section par source, celle-ci remplacée si elle existe déjà
    idx = out / "INDEX.md"
    secs = [x for x in (idx.read_text().split("\n## ") if idx.exists() else []) if x.strip()]
    secs = [x for x in secs if cut["source"] not in x]
    body = "\n".join(index[1:]) if False else "\n".join(index)
    body = body.replace("# Mouvements recopiés\n\n", "")
    parts = [x.replace("# Mouvements recopiés\n\n", "", 1) for x in secs] + [body]
    txt = "# Mouvements recopiés\n\n" + "\n\n## ".join(p_.strip("\n") for p_ in parts) + "\n"
    idx.write_text(txt)
    print("\n".join(index))
