import sys, json, numpy as np
sys.path.insert(0,'/home/claude/clipper/tools/mocap')
import fit2
from PIL import Image
from pathlib import Path
doc=json.load(open('/tmp/pivout/doc.json'))
F=fit2.Fitter(doc, Image.open('/tmp/fit/f/0045.png'))
FR=sorted(Path('/tmp/fit/f').glob('*.png'))
R=json.load(open('/tmp/fit/fine4.json'))
keys=[k for k in sys.argv[1].split(',')]
out={}
for k in keys:
    p=dict(R[k]); kk=int(k)
    rgb=np.asarray(Image.open(FR[kk]).convert('RGB')).astype(np.int16)
    m=np.abs(rgb-F.bga).sum(2)>=45; ys,xs=np.nonzero(m)
    box=(max(0,xs.min()-30),max(0,ys.min()-30),min(640,xs.max()+30),min(360,ys.max()+25))
    tl=fit2.labels(rgb[box[1]:box[3],box[0]:box[2]],F.bga[box[1]:box[3],box[0]:box[2]]); bgc=F.bga[box[1]:box[3],box[0]:box[2]]
    lab=lambda q: fit2.mismatch(fit2.labels(F.render(q,box),bgc),tl)/100
    best=None
    for th,sh,f1,f2,dy in [(190,270,.6,.8,-5),(185,272,.5,.7,-10),(200,275,.55,.9,0),(195,268,.6,.75,-8)]:
        q=dict(p); q.update(thigh_b=th,shin_b=sh); q['y']=p['y']+dy; q['ls']=dict(p.get('ls',{}),thigh_b=f1,shin_b=f2); q['ex']={}
        c=lab(q)
        if best is None or c<best[0]: best=(c,q)
    c,q=best
    free=['x','y','hip','spine','chest','neck','head','uarm_f','farm_f','uarm_b','farm_b','thigh_f','shin_f','thigh_b','shin_b']
    for st,sp in ((8,3),(4,1.5),(2,0.75)):
        for _ in range(2):
            for key in free:
                lo_ok = True
                for sg in (1,-1):
                    r=dict(q); r[key]=q[key]+sg*(sp if key in('x','y') else st)
                    if key=='thigh_b' and not (165<=r[key]<=215): continue
                    if key=='shin_b' and not (250<=r[key]<=290): continue
                    cc=lab(r)
                    if cc<c: c,q=cc,r; break
    for r_ in ['thigh_b','shin_b','thigh_f','shin_f']:
        for d in (-0.1,0.1):
            r=dict(q); ls=dict(q['ls']); ls[r_]=round(ls.get(r_,1)+d,3); r['ls']=ls
            if not (0.45<=ls[r_]<=1.1): continue
            cc=lab(r)
            if cc<c: c,q=cc,r
    q,c=F.stage_b(q, lambda z: lab(z), c)
    out[k]=dict(q, cost=round(c,3))
    print(k, round(lab(p),1), '->', round(c,1), flush=True)
json.dump(out,open(sys.argv[2],'w'))
