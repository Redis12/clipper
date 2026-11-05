import json, subprocess, wave, sys, numpy as np
SR = 44100
ev = json.load(open(sys.argv[1]))["events"]; dur = float(sys.argv[2]); out = sys.argv[3]; DBZ = sys.argv[4] == "1"; LAST = int(sys.argv[5])
n = int(dur*SR); a = np.zeros(n)
def load(p, maxs=1.2):
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", p, "-t", str(maxs), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True)
    x = np.frombuffer(r.stdout, np.float32).astype(float); m = np.abs(x).max() or 1
    return x/m
def put(s, t, g):
    i = int(t*SR); j = min(n, i+len(s)); a[i:j] += g*s[:j-i]
K = "/home/claude/clipper/clipper/assets/sfx/"; DB = "/home/claude/clipper/library/_sfx/Dragon Ball SFX/Dragon Ball Z Sounds/"
HY = "/home/claude/clipper/library/_sfx/Helton Yan's Old-School Shonen SFX/"
thud = load(K + "impact_plate_heavy_000.ogg")
if DBZ:
    punch = load(DB + "DBZ Sound effect Strong Punch.mp3", 0.6)
    burst = load(DB + "Voicy_Small Aura Burst (DBZ Sound Effect).mp3", 0.9); aura = load(DB + "Voicy_super sayian aura sound effect.mp3", 1.2)
else:
    punch = load(HY + "FGHTImpt_Anime Melee 1.ogg", 0.6)
    burst = load(HY + "MAGSpel_Anime Ability Release 1.ogg", 0.9); aura = load(HY + "MAGSpel_Anime Ability Ready 1.ogg", 1.2)
# grondement de la presse qui se ferme (avant chaque écrasement)
t2 = np.arange(int(0.6*SR))/SR; rumble = np.sin(2*np.pi*(45 + 30*t2)*t2) * np.linspace(0, 1, len(t2))**2
for k, (t, nc, tier) in enumerate(ev):
    put(rumble, t - 0.6, 0.25)
    put(thud, t, 0.7); put(punch, t, 0.45)
    put(burst if tier < LAST else aura, t + 0.03, 0.35 + min(0.3, nc*0.01))
a = np.tanh(a*1.1)
w = wave.open(out, "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((a*0.85*32767).astype(np.int16).tobytes()); w.close()
