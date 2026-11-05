import sim, json, sys, itertools
def fibN(start, target):
    V=[start,2*start]
    while V[-1] < target: V.append(V[-1]+V[-2])
    return len(V)-1  # index of first >= target
GRID=[(520,1.028,2700),(450,1.025,2200),(400,1.022,1800),(360,1.02,1400),(330,1.022,1300),(300,1.025,1500),(260,1.02,1000),(240,1.015,800),(200,1.02,700),(600,1.03,3000)]
def find(T, N=None, win=True):
    for v0,acc,vmax in GRID:
        for s in range(0,500):
            h,_=sim.simulate(s,T,r=62,v0=v0,acc=acc,vmax=vmax)
            if not h: continue
            gap=T-h[-1][0]
            if N is not None and len(h)!=N: continue
            if win and not (0.15<=gap<=0.45): continue
            if not win and not (0.3<=gap<=1.4): continue
            return dict(seed=s,sim=dict(v0=v0,acc=acc,vmax=vmax),n=len(h),gap=round(gap,2))
print("fib1M", fibN(1,1e6)); print("fib1B", fibN(1,1e9)); print("fibdebt", fibN(1,4.05e13))
