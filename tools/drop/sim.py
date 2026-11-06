"""Power Drop : simulation déterministe (sans rendu).

4 persos lâchent leur tête à tour de rôle en haut d'une planche à clous. Chaque clou touché ajoute PEG_PCT de sa
puissance, le bac d'arrivée la multiplie. Le premier à 1 000 000 gagne.
"""
import math
import random

W, H = 1080, 1920
R = 27            # rayon d'une balle (tête)
PR = 9            # rayon d'un clou
ROWS = 10
SX = 84           # écart horizontal des clous
DY = 76           # écart vertical des rangées
Y0 = 690          # 1re rangée
SPAWN = (540, 612)
BIN_TOP = Y0 + (ROWS - 1) * DY + 26
BIN_BOT = BIN_TOP + 112
MULTS = [10, 5, 2, 1.5, 1, 0.5, 1, 1.5, 2, 5, 10]
GRAV = 2900.0
E = 0.30          # restitution sur un clou
START = 100.0
GOAL = 1_000_000.0


def pegs():
    out = []
    for r in range(ROWS):
        n = r + 3
        y = Y0 + r * DY
        for i in range(n):
            out.append((540 + (i - (n - 1) / 2) * SX, y))
    return out


PEGS = pegs()
BOTTOM_X = [540 + (i - (ROWS + 2 - 1) / 2) * SX for i in range(ROWS + 2)]   # clous de la dernière rangée = séparateurs


def bin_of(x):
    for i in range(len(BOTTOM_X) - 1):
        if x < BOTTOM_X[i + 1]:
            return max(0, i)
    return len(BOTTOM_X) - 2


def simulate(seed, n_chars=4, gap=0.62, peg_pct=0.06, max_t=90.0, dt=1 / 240):
    rng = random.Random(seed)
    power = [START] * n_chars
    balls = []      # dict: c, x, y, vx, vy, born, hits, last, alive, id
    events = []     # (t, kind, data)
    frames = []     # snapshots par image (30 i/s)
    t, next_spawn, turn, bid = 0.0, 0.25, 0, 0
    winner, win_t = None, None
    snap_every, next_snap = 1 / 30, 0.0
    while t < max_t:
        if winner is None and t >= next_spawn:
            c = turn % n_chars
            balls.append(dict(c=c, x=SPAWN[0] + rng.uniform(-26, 26), y=SPAWN[1], vx=rng.uniform(-50, 50), vy=60.0,
                              born=t, hits=0, last={}, alive=True, id=bid))
            events.append((t, "spawn", dict(c=c, id=bid)))
            bid += 1
            turn += 1
            next_spawn += gap
        for b in balls:
            if not b["alive"]:
                continue
            b["vy"] += GRAV * dt
            sp = math.hypot(b["vx"], b["vy"])
            if sp > 1500:
                b["vx"] *= 1500 / sp
                b["vy"] *= 1500 / sp
            b["x"] += b["vx"] * dt
            b["y"] += b["vy"] * dt
            if b["x"] < 60 + R:
                b["x"], b["vx"] = 60 + R, abs(b["vx"]) * 0.5
            if b["x"] > W - 60 - R:
                b["x"], b["vx"] = W - 60 - R, -abs(b["vx"]) * 0.5
            for k, (px, py) in enumerate(PEGS):
                dx, dy = b["x"] - px, b["y"] - py
                d2 = dx * dx + dy * dy
                if d2 < (R + PR) ** 2:
                    d = math.sqrt(d2) or 1e-6
                    nx, ny = dx / d, dy / d
                    b["x"], b["y"] = px + nx * (R + PR), py + ny * (R + PR)
                    vn = b["vx"] * nx + b["vy"] * ny
                    if vn < 0:
                        b["vx"] -= (1 + E) * vn * nx
                        b["vy"] -= (1 + E) * vn * ny
                        b["vx"] += rng.uniform(-35, 35)
                        if abs(b["vx"]) < 40:                        # jamais posé en équilibre sur un clou
                            b["vx"] = rng.choice((-1, 1)) * 70
                    if k not in b["last"]:                              # chaque clou ne compte qu'une fois par balle
                        b["last"][k] = t
                        b["hits"] += 1
                        if winner is None:
                            gain = max(1.0, power[b["c"]] * peg_pct)
                            power[b["c"]] += gain
                            events.append((t, "peg", dict(c=b["c"], id=b["id"], k=k, n=b["hits"], gain=gain)))
            if b["y"] > BIN_TOP - 8:                                 # séparateurs des bacs
                for sx in BOTTOM_X:
                    if abs(b["x"] - sx) < R + 4:
                        side = 1 if b["x"] >= sx else -1
                        b["x"] = sx + side * (R + 4)
                        b["vx"] = side * abs(b["vx"]) * 0.35
            if b["y"] > BIN_BOT - R:
                b["alive"] = False
                bi = bin_of(b["x"])
                if winner is None:
                    m = MULTS[bi]
                    power[b["c"]] *= m
                    events.append((t, "land", dict(c=b["c"], id=b["id"], bin=bi, m=m, p=power[b["c"]])))
        if winner is None:
            for c in range(n_chars):
                if power[c] >= GOAL:
                    winner, win_t = c, t
                    events.append((t, "win", dict(c=c)))
                    break
        if t >= next_snap:
            frames.append(dict(t=t, power=list(power),
                               balls=[(b["c"], b["x"], b["y"], b["id"]) for b in balls if b["alive"]]))
            next_snap += snap_every
        if winner is not None and t > win_t + 0.05:
            break
        t += dt
    return dict(seed=seed, winner=winner, win_t=win_t, events=events, frames=frames, power=power)


def score(res):
    """Plus c'est haut, plus la course est bonne : changements de leader, fin serrée, durée 32–45 s."""
    if res["winner"] is None:
        return -1e9, {}
    lead, changes, last = None, 0, None
    for f in res["frames"]:
        p = f["power"]
        cur = max(range(len(p)), key=lambda i: p[i])
        if p[cur] > START * 1.5 and cur != lead:
            if lead is not None:
                changes += 1
            lead = cur
        last = p
    s = sorted(math.log10(max(v, 1)) for v in last)
    gap2 = s[-1] - s[-2]                     # écart en décades avec le 2e
    T = res["win_t"]
    sc = changes * 2.0 - gap2 * 6.0 - (0 if 32 <= T <= 45 else abs(T - 38) * 0.8)
    return sc, dict(changes=changes, gap2=round(gap2, 2), T=round(T, 1), winner=res["winner"])


if __name__ == "__main__":
    import sys
    gap = float(sys.argv[1]) if len(sys.argv) > 1 else 0.62
    pct = float(sys.argv[2]) if len(sys.argv) > 2 else 0.06
    Ts = []
    for s in range(12):
        r = simulate(s, gap=gap, peg_pct=pct)
        sc, info = score(r)
        Ts.append(info.get("T"))
        print(s, round(sc, 1), info)
