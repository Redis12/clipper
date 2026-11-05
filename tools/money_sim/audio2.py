import numpy as np, subprocess, wave, sys, json
from sim import simulate
CFG = json.load(open(sys.argv[1]))
T = float(CFG.get('seconds', 60))
SR = 44100; END = 1.8
hits, _ = simulate(CFG['seed'], T, r=62, **CFG.get('sim', {}))
N = len(hits); m = CFG.get('mult') or (CFG['target']/CFG['start'])**(1/N)
if CFG.get('mode') == 'fib':
    V = [CFG['start'], 2*CFG['start']]
    while len(V) <= N: V.append(V[-1] + V[-2])
else:
    V = [CFG['start']*m**k for k in range(N + 1)]
WIN = V[N] >= CFG['target']*0.999
TE = hits[-1][0] if WIN else T
n = int((T + END) * SR); out = np.zeros(n)
def load(p):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)
def ching(f0, dur=0.22):
    t = np.arange(int(dur*SR))/SR
    s = sum(a*np.sin(2*np.pi*f0*k*t) * np.exp(-t*(18+8*k)) for k, a in ((1, 1), (2.76, .5), (5.4, .25), (8.9, .12)))
    s[:60] *= np.linspace(0, 1, 60)
    return s
def put(s, t, g):
    i = int(t*SR); j = min(n, i+len(s)); out[i:j] += g*s[:j-i]
for k, (th, _) in enumerate(hits):
    semi = min(14, k*14/len(hits))
    put(ching(1320*2**(semi/12)), th, 0.32)
A = "/home/claude/clipper/clipper/assets/sfx/"
tick = load(A + "impact_metal_light_000.ogg")
for s in range(10):
    put(tick, T - 10 + s, 0.35 + 0.04*s)
# fin : ka-ching + cloche + montée
if WIN:
    put(ching(880, 0.9)*0.9 + np.pad(ching(1760, 0.6), (0, int(0.3*SR))), TE, 0.8)
    put(load(A + "impact_bell_heavy_000.ogg"), TE, 0.6)
    put(load(A + "powerUp7.ogg"), TE + 0.15, 0.5)
else:
    put(load(A + "impact_bell_heavy_002.ogg"), T, 0.7)
    put(load(A + "low_frequency_explosion_001.ogg"), T, 0.6)
    t2 = np.arange(int(0.9*SR))/SR; buzz = 0.4*np.sign(np.sin(2*np.pi*110*t2))*np.exp(-t2*2.5)
    put(buzz, T + 0.05, 0.5)
# nappe grave qui monte doucement (tension)
t = np.arange(int(T*SR))/SR
f = 55*2**(t/T*1.0)
pad = (np.sin(2*np.pi*np.cumsum(f)/SR) + 0.5*np.sin(2*np.pi*np.cumsum(f*1.5)/SR)) * (0.05 + 0.07*t/T)
out[:len(pad)] += pad
out = np.tanh(out*1.2)/1.2
w = wave.open(sys.argv[2], "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
w.writeframes((out*32767*0.9).astype(np.int16).tobytes()); w.close()
