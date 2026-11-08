import sys; sys.path.insert(0, '.')
import extract_flat as X
from concurrent.futures import ProcessPoolExecutor
V = '/tmp/sai_v/src.mp4'
JOBS = [
    ('saitama_debout', 11.5, 13.55, (250, 150, 1200, 1080)),
    ('saitama_super_saut', 13.55, 14.17, (250, 150, 1300, 1080)),
    ('saitama_marche', 24.0, 26.6, (100, 150, 1400, 1080)),
    ('saitama_poing_armer', 70.5, 70.95, (250, 240, 840, 1080)),
    ('saitama_poing_tendu', 74.95, 76.0, (250, 240, 880, 1080)),
    ('saitama_poing_retour', 76.0, 76.8, (250, 240, 900, 1080)),
    ('saitama_accroupi_elan', 80.3, 80.66, (300, 150, 780, 1080)),
    ('saitama_saut_air', 81.55, 82.0, (0, 150, 1500, 1080)),
    ('saitama_reception', 82.0, 82.6, (0, 150, 1500, 1080)),
    ('saitama_course', 118.0, 118.45, (0, 300, 1100, 1080)),
]
def go(j):
    n, a, b, box = j
    try:
        return X.run(V, a, b, n, box, 575.0)
    except Exception as e:
        return (n, 'ERR', str(e))
with ProcessPoolExecutor(2) as ex:
    for r in ex.map(go, JOBS): print(r, flush=True)
