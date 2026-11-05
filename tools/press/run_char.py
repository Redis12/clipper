import sys, json, subprocess
sys.path.insert(0, "/tmp/claude-0/-home-claude/21bbeec3-7caf-5d02-b598-3bc7fb9936c1/scratchpad/press")
import press, chars
name, seed = sys.argv[1], int(sys.argv[2])
press.TIERS = chars.tiers(name); press.TITLE2 = chars.FINAL[name]
D = "/tmp/claude-0/-home-claude/21bbeec3-7caf-5d02-b598-3bc7fb9936c1/scratchpad/press/"
v = D + f"v_{name}.mp4"; press.render(seed, v)
subprocess.run(["python3", D + "paudio.py", v + ".json", "39", D + f"a_{name}.wav", "1" if name in chars.DB else "0", str(len(press.TIERS) - 1)], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", v, "-i", D + f"a_{name}.wav", "-c:v", "copy", "-c:a", "aac", "-af", "loudnorm=I=-20:TP=-1.5", "-shortest", D + f"out/Hydraulic Press - {name}.mp4"], check=True)
print("done", name, json.load(open(v + ".json"))["n_end"], flush=True)
