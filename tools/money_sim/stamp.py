"""Filigrane Money Sim : badge qui change de place toutes les 6 s, hors des zones de texte."""
import sys, subprocess
from PIL import Image
SPOTS = [(0.50, 0.300), (0.80, 0.770), (0.50, 0.300), (0.22, 0.770)]
def stamp(src, dst, badge="badge_moneysim.png", every=6.0, alpha=0.6):
    b = Image.open(badge).convert("RGBA"); b.putalpha(b.getchannel("A").point(lambda v: int(v*alpha))); b.save("/tmp/_wm.png")
    n = len(SPOTS); cyc = every*n; xs = ys = ""
    for i, (fx, fy) in enumerate(SPOTS):
        last = i == n-1; cond = f"lt(mod(t,{cyc}),{every*(i+1)})"
        xi, yi = f"main_w*{fx}-overlay_w/2", f"main_h*{fy}-overlay_h"
        xs += xi if last else f"if({cond},{xi},"; ys += yi if last else f"if({cond},{yi},"
    xs += ")"*(n-1); ys += ")"*(n-1)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-i", "/tmp/_wm.png", "-filter_complex",
                    f"[0:v][1:v]overlay=x='{xs}':y='{ys}':format=auto", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                    "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", dst], check=True)
if __name__ == "__main__":
    stamp(sys.argv[1], sys.argv[2])
