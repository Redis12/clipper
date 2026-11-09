import soundfile as sf
from kokoro_onnx import Kokoro
k = Kokoro("kokoro-v1.0.onnx", "voices-v1.0.bin")
txt = "Saitama fans think one single punch would be enough to beat Goku. But there's a problem they refuse to admit. He would still have to touch him."
import numpy as np
outs=[]
for v in ["am_michael", "am_adam", "am_onyx", "bm_george"]:
    s, sr = k.create(txt, voice=v, speed=1.1, lang="en-us" if v.startswith("a") else "en-gb")
    outs.append(s); outs.append(np.zeros(int(sr*0.6), np.float32))
    print(v, len(s)/sr)
sf.write("demo.wav", np.concatenate(outs), sr)
