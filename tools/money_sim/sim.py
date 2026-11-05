import math, random
def simulate(seed, T=60.0, L=900, r=46, v0=520, acc=1.028, vmax=2700, dt=1/600):
    rnd = random.Random(seed)
    a = rnd.uniform(0.2, 1.35) + rnd.choice([0, math.pi/2, math.pi, 3*math.pi/2])
    x, y = rnd.uniform(r+60, L-r-60), rnd.uniform(r+60, L-r-60)
    v = v0; vx, vy = v*math.cos(a), v*math.sin(a)
    t = 0; hits = []; path = []
    k = 0
    while t < T:
        x += vx*dt; y += vy*dt; hit = None
        if x < r: x = 2*r-x; vx = -vx; hit = (r*0, y)
        elif x > L-r: x = 2*(L-r)-x; vx = -vx; hit = (L, y)
        if y < r: y = 2*r-y; vy = -vy; hit = (x, 0)
        elif y > L-r: y = 2*(L-r)-y; vy = -vy; hit = (x, L)
        if hit:
            hits.append((t, hit))
            s = min(vmax, math.hypot(vx, vy)*acc); n = math.hypot(vx, vy); vx, vy = vx/n*s, vy/n*s
        k += 1
        if k % 10 == 0: path.append((t, x, y))
        t += dt
    return hits, path
def pick(T=60.0, tries=400):
    best = None
    for s in range(tries):
        h, _ = simulate(s, T)
        if not h: continue
        last = h[-1][0]
        gap = T - last
        if 0.05 <= gap <= 0.45:
            sc = abs(gap - 0.25)
            if best is None or sc < best[0]: best = (sc, s, len(h), last)
    return best
if __name__ == "__main__":
    print(pick())
