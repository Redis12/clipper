import os, difflib, re
LIB = "/home/claude/clipper/library/_fusion/"
FINAL = {"Goku": "ULTRA INSTINCT GOKU", "Vegeta": "ULTRA EGO VEGETA", "Gohan": "BEAST GOHAN", "Frieza": "BLACK FRIEZA",
         "Cell": "CELL MAX", "Buu": "KID BUU", "Ichigo": "TRUE BANKAI ICHIGO", "Luffy": "GEAR 5 LUFFY",
         "Naruto": "BARYON MODE NARUTO", "Sasuke": "BORUTO SASUKE", "Madara": "SIX PATHS MADARA"}
DB = {"Goku", "Vegeta", "Gohan", "Frieza", "Cell", "Buu"}
PALETTE = [(255, 140, 40), (70, 120, 255), (255, 215, 60), (255, 90, 120), (60, 210, 255), (180, 110, 255), (120, 230, 140), (230, 230, 255)]
def tiers(name):
    d = LIB + name + "/"; files = [f for f in os.listdir(d) if not f.endswith(".txt")]
    rows = []
    for line in open(d + "ordre.txt"):
        line = line.strip()
        if not line or line.startswith("#") or "easter" in line: continue
        f, n = [x.strip() for x in line.split("=", 1)]
        if f not in files: f = difflib.get_close_matches(f, files, 1, 0.3)[0] if not any(x.endswith(f) for x in files) else [x for x in files if x.endswith(f)][0]
        rows.append((f, n))
    KEEP = {"Goku": ["Kid Goku", "Base", "SSJ1", "SSJ3", "SSJ Blue", "Ultra Instinct"],
            "Frieza": ["First Form", "Third Form", "Final Form", "Mecha Frieza", "Golden Frieza", "Black Frieza"],
            "Naruto": ["Kid Naruto", "Base", "Sage Mode", "Nine-Tails Chakra Mode", "Kurama Mode", "Baryon Mode"],
            "Madara": ["Kid Madara", "Young Madara", "Mangekyō Sharingan", "Perfect Susanoo", "Rinnegan", "Six Paths Madara"],
            "Sasuke": ["Kid Sasuke", "Curse Mark", "Mangekyo Sharingan", "Perfect Susanoo", "Rinnegan", "Boruto Sasuke"]}
    if name in KEEP:
        rows = [r for r in rows if r[1] in KEEP[name]]
    elif len(rows) > 6:
        idx = sorted({round(i*(len(rows)-1)/5) for i in range(6)}); rows = [rows[i] for i in idx]
    return [(d + f, n.upper(), PALETTE[i % len(PALETTE)]) for i, (f, n) in enumerate(rows)]
if __name__ == "__main__":
    for c in FINAL: print(c, [t[1] for t in tiers(c)])
