import sys, sim
from concurrent.futures import ProcessPoolExecutor
gap, pct, n = float(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
def run(s):
    r = sim.simulate(s, gap=gap, peg_pct=pct)
    sc, info = sim.score(r)
    return s, round(sc, 1), info
if __name__ == "__main__":
    with ProcessPoolExecutor() as ex:
        res = sorted(ex.map(run, range(n)), key=lambda x: -x[1])
    for x in res[:8]:
        print(x)
    print("T moyen", round(sum(x[2].get("T", 0) for x in res) / len(res), 1))
