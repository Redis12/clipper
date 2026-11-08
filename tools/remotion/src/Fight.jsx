import React from 'react';
import { AbsoluteFill, useCurrentFrame, staticFile } from 'remotion';
import { L, P, poseAt, joints, dir, add, rnd, pts, mix } from './rig';

const W = 1080, H = 1920, GROUND = 1420, S = 2.9;
const GX = 250, VX = 830;                     // bassin de Goku / de Vegeta (Vegeta dessiné en miroir)
const FPS = 30;

// ------------------------------------------------------------------ scénario
const HITS = [142, 148, 154, 160, 166, 172];
const KICK = 186, BEAM = 291, BEAM_END = 344;
const DX = 128;                                // Goku s'avance de DX unités pour frapper

const GOKU = [
  [0, 'stance'], [30, 'stance'], [40, 'charge', 'inout'], [52, 'scream'], [104, 'scream'],
  [120, 'stance', 'inout'], [128, 'stance'],
  [134, { ...P.dash, x: 60 }, 'snap'], [139, { ...P.stance, x: DX }, 'snap'],
  [142, { ...P.jab, x: DX + 18 }, 'snap'], [146, { ...P.stance, x: DX }],
  [148, { ...P.cross, x: DX + 34 }, 'snap'], [152, { ...P.stance, x: DX + 6 }],
  [154, { ...P.jab, x: DX + 22 }, 'snap'], [158, { ...P.stance, x: DX + 8 }],
  [160, { ...P.hook, x: DX + 30 }, 'snap'], [164, { ...P.stance, x: DX + 10 }],
  [166, { ...P.cross, x: DX + 40 }, 'snap'], [170, { ...P.stance, x: DX + 12 }],
  [172, { ...P.upper, x: DX + 34 }, 'snap'], [179, { ...P.kickW, x: DX + 26 }],
  [186, { ...P.kick, x: DX + 40 }, 'snap'], [198, { ...P.kick, x: DX + 40 }],
  [214, { ...P.stance, x: 20 }, 'inout'], [228, { ...P.stance, x: 0 }],
  [240, 'kameBk', 'inout'], [289, { ...P.kameBk, torso: -108 }], [BEAM, 'kameFr', 'snap'],
  [BEAM_END, 'kameFr'], [360, 'stance', 'inout'], [390, 'stance'],
];

function vegetaTrack() {
  const t = [[0, 'guard']];
  let push = 0;
  HITS.forEach((h, i) => {
    push -= 7;
    t.push([h - 1, { ...P.guard, x: push + 4 }]);
    t.push([h + 1, { ...(i % 2 ? P.hurt2 : P.hurt), x: push - 20 }, 'snap']);
    t.push([h + 5, { ...P.guard, x: push }]);
  });
  t.push([KICK - 1, { ...P.guard, x: push }]);
  t.push([KICK + 2, { ...P.hurt2, x: push - 40 }, 'snap']);
  t.push([KICK + 14, { ...P.fly, x: -70, y: -110 }, 'out']);
  t.push([KICK + 24, { ...P.down, x: -96, y: 0 }, 'inout']);
  t.push([238, { ...P.down, x: -96 }]);
  t.push([252, { ...P.hurt, x: -84 }, 'inout']);
  t.push([262, { ...P.guard, x: -80 }, 'out']);
  t.push([BEAM + 2, { ...P.guard, x: -80 }]);
  t.push([BEAM + 6, { ...P.hurt2, x: -140 }, 'snap']);
  t.push([BEAM_END, { ...P.hurt2, x: -170, y: -20 }]);
  t.push([BEAM_END + 18, { ...P.fly, x: -420, y: -520 }, 'out']);
  t.push([390, { ...P.fly, x: -460, y: -600 }]);
  return t;
}
const VEGETA = vegetaTrack();

const CALLS = [
  [44, 'HAAAAA!', '#ffd23f', 150], [104, 'SUPER SAIYAN!', '#ffd23f', 132],
  [148, 'ORA!', '#ffffff', 120], [166, 'ORA ORA!', '#ffffff', 120], [KICK, 'BAM!', '#ffd23f', 190],
  [244, 'KA...', '#6fd3ff', 140], [256, 'ME...', '#6fd3ff', 140], [268, 'HA...', '#6fd3ff', 140], [280, 'ME...', '#6fd3ff', 140],
  [BEAM, 'HAAAAAAA!', '#ffffff', 170], [356, 'K.O.!', '#ffd23f', 230],
];
const FLASHES = [104, KICK, BEAM, BEAM_END];
const SHAKES = [[52, 6, 52], [104, 26, 18], ...HITS.map((h) => [h, 9, 8]), [KICK, 30, 14], [BEAM, 34, 54], [BEAM_END, 26, 16]];

// ------------------------------------------------------------------ dessin d'un stickman
const GOKU_COL = { arm: '#f4caa0', armB: '#d9a97f', fist: '#f4caa0', fistB: '#d9a97f', band: '#1f4fd1', bandB: '#173a9c', leg: '#f26b1d', legB: '#c9500f', boot: '#1f4fd1', bootB: '#173a9c', torso: '#f26b1d', under: '#1f4fd1', belt: '#1f4fd1', skin: '#f4caa0' };
const VEG_COL = { arm: '#2546c4', armB: '#1a3392', fist: '#f5f5f5', fistB: '#d9d9de', band: '#f5f5f5', bandB: '#d9d9de', leg: '#2546c4', legB: '#1a3392', boot: '#f5f5f5', bootB: '#d9d9de', torso: '#f5f5f5', under: '#2546c4', belt: '#2546c4', skin: '#f2c49a', shoulder: '#e8c341' };

const GOKU_HAIR = [[-0.15, 1.25], [0.25, 1.75], [0.7, 1.55], [1.05, 2.05], [1.45, 1.7], [1.85, 2.15], [2.3, 1.75], [2.75, 1.95], [3.15, 1.5], [3.6, 1.2]];
function gokuHair(c, ang, ssj, t) {
  const up = (ang * Math.PI) / 180, R = L.head * S, out = [];
  GOKU_HAIR.forEach(([a, len], i) => {
    const base = up - Math.PI / 2 - 0.35 + a * 0.55 * (ssj ? 1.06 : 1);
    const L1 = R * (ssj ? len * 1.22 + 0.1 * Math.sin(t * 22 + i) : len);
    out.push([c[0] + Math.cos(base - 0.16) * R * 0.95, c[1] + Math.sin(base - 0.16) * R * 0.95]);
    out.push([c[0] + Math.cos(base) * L1, c[1] + Math.sin(base) * L1 - (ssj ? 8 : 0)]);
    out.push([c[0] + Math.cos(base + 0.16) * R * 0.95, c[1] + Math.sin(base + 0.16) * R * 0.95]);
  });
  out.push([c[0] + R * 0.65, c[1] - R * 0.35], [c[0] + R * 0.2, c[1] - R * 0.1], [c[0] - R * 0.2, c[1] - R * 0.5]);
  return pts(out) + 'Z';
}
function vegetaHair(c, ang) {                    // flamme haute, pointe en arrière
  const up = (ang * Math.PI) / 180, R = L.head * S, out = [];
  const spikes = [[-0.9, 1.1], [-0.55, 2.1], [-0.25, 1.6], [0.05, 2.6], [0.35, 1.9], [0.65, 2.3], [0.95, 1.4]];
  spikes.forEach(([a, len]) => {
    const base = up - 0.25 + a * 0.7;
    out.push([c[0] + Math.cos(base - 0.2) * R * 0.95, c[1] + Math.sin(base - 0.2) * R * 0.95]);
    out.push([c[0] + Math.cos(base) * R * len, c[1] + Math.sin(base) * R * len]);
  });
  out.push([c[0] + R * 0.9, c[1] - R * 0.2], [c[0] + R * 0.55, c[1] - R * 0.65], [c[0] + R * 0.35, c[1] - R * 0.15]);
  return pts(out) + 'Z';
}

function Stick({ J, pose, col, hair, ssj = 0, t, flip }) {
  const seg = (a, b) => pts([a, b]);
  const seg3 = (a, b, c) => pts([a, b, c]);
  const w = (v) => v * S;
  const band = (wr, el) => {
    const a = (Math.atan2(el[1] - wr[1], el[0] - wr[0]) * 180) / Math.PI;
    return seg(wr, add(wr, dir(a, 10 * S)));
  };
  const line = (d, stroke, width) => <path d={d} fill="none" stroke={stroke} strokeWidth={w(width)} strokeLinecap="round" strokeLinejoin="round" />;
  const bl = add(J.hip, dir(pose.torso, 8 * S));
  const hairCol = hair === 'goku' ? mix('16121f', 'ffd23f', ssj) : '#141018';
  const ex = J.head[0] + 9 * S, ey = J.head[1] - 2 * S;
  return (
    <g transform={flip ? `matrix(-1 0 0 1 ${W} 0)` : undefined}>
      {line(seg3(J.shB, J.eB, J.wB), col.armB, 11)}
      {line(band(J.wB, J.eB), col.bandB, 13)}
      <circle cx={J.wB[0]} cy={J.wB[1]} r={w(8.5)} fill={col.fistB} />
      {line(seg3(J.hip, J.kB, J.aB), col.legB, 18)}
      {line(seg(add(J.aB, [0, -14 * S]), add(J.aB, [14 * S, 2 * S])), col.bootB, 15)}
      {line(seg(add(J.hip, dir(pose.torso, 4 * S)), add(J.neck, dir(pose.torso, -8 * S))), col.torso, 26)}
      {col.shoulder ? line(seg(add(J.neck, dir(pose.torso, -14 * S)), add(J.neck, dir(pose.torso, -4 * S))), col.shoulder, 30) : null}
      {line(seg(add(J.neck, dir(pose.torso, -10 * S)), add(J.neck, dir(pose.torso, -2 * S))), col.under, 12)}
      {line(seg(add(bl, dir(pose.torso + 90, 14 * S)), add(bl, dir(pose.torso - 90, 14 * S))), col.belt, 9)}
      {line(seg3(J.hip, J.kF, J.aF), col.leg, 18)}
      {line(seg(add(J.aF, [0, -14 * S]), add(J.aF, [15 * S, 2 * S])), col.boot, 15)}
      {line(seg(J.neck, add(J.neck, dir(pose.neck, (L.neck + 6) * S))), col.skin, 9)}
      <circle cx={J.head[0]} cy={J.head[1]} r={L.head * S} fill={col.skin} />
      <path d={`M${ex - 5 * S} ${ey - (3 + ssj * 2) * S} L${ex + 6 * S} ${ey - S} L${ex + 5 * S} ${ey + 2 * S} L${ex - 3 * S} ${ey + S} Z`} fill={ssj > 0.5 ? '#1a9e8f' : '#16121f'} />
      <path d={hair === 'goku' ? gokuHair(J.head, pose.neck, ssj > 0.35, t) : vegetaHair(J.head, pose.neck)} fill={hairCol} stroke="#0d0b1f" strokeWidth={3} strokeLinejoin="round" filter={ssj > 0.5 ? 'url(#glow)' : undefined} />
      {line(seg3(J.shF, J.eF, J.wF), col.arm, 11)}
      {line(band(J.wF, J.eF), col.band, 13)}
      <circle cx={J.wF[0]} cy={J.wF[1]} r={w(8.5)} fill={col.fist} />
    </g>
  );
}

// ------------------------------------------------------------------ effets
function flame(cx, cy, w, h, t, seed) {
  const out = [], n = 28;
  for (let i = 0; i <= n; i++) {
    const a = Math.PI + (i / n) * Math.PI;
    const lick = 1 + 0.28 * Math.sin(t * 13 + i * 1.7 + seed) + 0.18 * Math.sin(t * 21 + i * 3.1 + seed * 2);
    const tip = i % 2 === 0 ? 1.18 : 0.92;
    out.push([cx + Math.cos(a) * w, cy + Math.sin(a) * h * lick * tip]);
  }
  out.push([cx + w * 0.75, cy + h * 0.08], [cx + w * 0.3, cy + h * 0.13], [cx - w * 0.3, cy + h * 0.13], [cx - w * 0.75, cy + h * 0.08]);
  return pts(out) + 'Z';
}

function Aura({ J, a, gold, t, f }) {
  if (a <= 0.01) return null;
  const cx = (J.hip[0] + J.neck[0]) / 2, cy = J.hip[1] + 14;
  const outer = mix('6fd3ff', 'ffb81f', gold), mid = mix('bfeaff', 'ffd23f', gold), inner = mix('ffffff', 'fff4c2', gold);
  const cols = [outer, mid, inner], ws = [70, 52, 34], hs = [205, 165, 120], op = [0.38, 0.45, 0.55];
  const rise = [];
  for (let k = 0; k < 24; k++) {                 // étincelles qui montent (déterministes)
    const sf = f - (k % 24), id = sf * 7 + k;
    const age = (f - sf) / 24;
    const x = cx + (rnd(id) - 0.5) * 260, y = cy + 10 - age * (260 + rnd(id + 3) * 200) * a;
    const r = (3 + rnd(id + 5) * 5) * (1 - age);
    rise.push(<path key={k} d={`M${x} ${y - r * 3} L${x + r * 0.8} ${y} L${x} ${y + r} L${x - r * 0.8} ${y} Z`} fill={k % 2 ? mid : inner} opacity={(1 - age) * 0.9 * a} />);
  }
  return (
    <g>
      <ellipse cx={cx} cy={cy - 140} rx={140} ry={220} fill={outer} opacity={a * 0.5} filter="url(#soft)" />
      {cols.map((c, i) => <path key={i} d={flame(cx, cy, ws[i] * S * (0.8 + a * 0.35), hs[i] * S * (0.75 + a * 0.4), t, i * 2.3)} fill={c} opacity={a * op[i]} />)}
      {rise}
    </g>
  );
}

function Impact({ x, y, age, size, col, seed }) {
  const k = age / 8;
  if (age < 0 || k >= 1) return null;
  const R = size * (0.6 + k * 0.8), r2 = R * 0.28, s = [];
  for (let j = 0; j < 16; j++) { const a = (j * Math.PI) / 8 + 0.2; const rr = j % 2 ? r2 : R * (j % 4 === 0 ? 1 : 0.65); s.push([x + Math.cos(a) * rr, y + Math.sin(a) * rr]); }
  const ring = size * 0.6 * (0.4 + k * 2.4);
  const sparks = [];
  for (let i = 0; i < 12; i++) {
    const a = rnd(seed + i) * Math.PI * 2, sp = (18 + rnd(seed + i + 50) * 30) * (age + 1);
    const x1 = x + Math.cos(a) * sp, y1 = y + Math.sin(a) * sp;
    sparks.push(<line key={i} x1={x1} y1={y1} x2={x1 - Math.cos(a) * 30} y2={y1 - Math.sin(a) * 30} stroke="#ffffff" strokeWidth={6 * (1 - k)} strokeLinecap="round" />);
  }
  return (
    <g opacity={1 - k}>
      <path d={pts(s) + 'Z'} fill={col} stroke="#ffffff" strokeWidth={4} />
      <circle cx={x} cy={y} r={ring} fill="none" stroke="#ffffff" strokeWidth={8 * (1 - k)} />
      {sparks}
    </g>
  );
}

function SpeedLines({ f, y, op }) {
  if (op <= 0) return null;
  const ls = [];
  for (let i = 0; i < 34; i++) {
    const yy = y - 420 + ((i * 53 + f * 31) % 840);
    const x = ((i * 233 + f * 95) % 1400) - 160;
    const len = 160 + ((i * 37) % 260);
    ls.push(<line key={i} x1={x} x2={x - len} y1={yy} y2={yy} stroke="#f6efe2" strokeWidth={2 + (i % 3) * 2} strokeLinecap="round" opacity={0.25 + (i % 4) * 0.15} />);
  }
  return <g opacity={op}>{ls}</g>;
}

// ------------------------------------------------------------------ scène
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const lerp = (a, b, t) => a + (b - a) * t;

export const Fight = () => {
  const f = useCurrentFrame();
  const t = f / FPS;
  // Goku
  let gp = poseAt(GOKU, f);
  const idle = (f < 30 || (f > 120 && f < 130) || f > 360);
  if (idle) {
    const b = (Math.sin(t * 2.4) + 1) / 2;
    const br = { ...P.stance };
    for (const k of Object.keys(br)) br[k] = lerp(P.stance[k], P.breathe[k], b) + (gp[k] - P.stance[k]);
    gp = br;
  }
  const tremble = f > 44 && f < 104 ? (rnd(f) - 0.5) * 8 : 0;
  const J = joints(gp, GX + tremble, GROUND, S);
  const vp = poseAt(VEGETA, f);
  const JV = joints(vp, W - VX, GROUND, S);
  const mirror = (p) => [W - p[0], p[1]];
  const ssj = clamp((f - 100) / 6, 0, 1);
  // aura
  let aura = 0;
  if (f >= 40 && f < 104) aura = lerp(0.2, 0.85, clamp((f - 40) / 50, 0, 1));
  else if (f >= 104 && f < 120) aura = 1;
  else if (f >= 120) aura = 0.25;
  if (f >= 240 && f < BEAM_END) aura = Math.max(aura, 0.5);
  const gold = ssj;
  // Kamehameha
  const hands = [(J.wF[0] + J.wB[0]) / 2, (J.wF[1] + J.wB[1]) / 2];
  const ballK = f < 244 ? 0 : f < BEAM ? clamp((f - 244) / 44, 0, 1) * 1.1 : f < BEAM_END ? 1 : clamp(1 - (f - BEAM_END) / 10, 0, 1);
  const beamOn = f >= BEAM && f < BEAM_END + 10;
  const beamLen = f < BEAM ? 0 : f < BEAM_END ? clamp((f - BEAM) / 4, 0, 1) * 1300 : 1300;
  const beamW = (f < BEAM_END ? 1 : clamp(1 - (f - BEAM_END) / 10, 0, 1)) * 190 * (1 + 0.1 * Math.sin(f * 1.9));
  // tremblement / flash
  let shake = 0;
  for (const [sf, amp, dur] of SHAKES) if (f >= sf && f < sf + dur) shake = Math.max(shake, amp * (1 - (f - sf) / dur));
  const sx = (rnd(f * 3) - 0.5) * 2 * shake, sy = (rnd(f * 3 + 1) - 0.5) * 2 * shake;
  let flash = 0;
  for (const ff of FLASHES) if (f >= ff && f < ff + 8) flash = Math.max(flash, 0.9 * (1 - (f - ff) / 8));
  // impacts
  const impacts = [];
  HITS.forEach((h, i) => {
    const pj = joints(poseAt(GOKU, h), GX, GROUND, S);
    const fist = i % 2 === 1 ? pj.wB : pj.wF;
    impacts.push(<Impact key={h} x={fist[0] + 26} y={fist[1]} age={f - h} size={70} col={i === 5 ? '#ff8a3d' : '#ffd23f'} seed={h} />);
  });
  {
    const pj = joints(poseAt(GOKU, KICK), GX, GROUND, S);
    impacts.push(<Impact key="k" x={pj.aF[0] + 40} y={pj.aF[1]} age={f - KICK} size={130} col="#ffd23f" seed={KICK} />);
  }
  const speedOp = (f >= 132 && f < 200) ? 0.7 : (f >= BEAM && f < BEAM_END) ? 0.85 : 0;
  // texte
  let call = null;
  for (const [cf, txt, col, size] of CALLS) {
    const age = f - cf;
    if (age >= 0 && age < 28) {
      const sc = age < 4 ? 1.5 - age * 0.125 : 1;
      call = (
        <text x={W / 2} y={470} textAnchor="middle" fontFamily="Bangers" fontSize={size} fill={col} stroke="#0d0b1f" strokeWidth={14} paintOrder="stroke" letterSpacing={4}
          opacity={age < 22 ? 1 : 1 - (age - 22) / 6} transform={`translate(${W / 2} 470) scale(${sc}) translate(${-W / 2} -470)`}>{txt}</text>
      );
    }
  }
  const crackle = [];
  if (ballK > 0.1 && f < BEAM) {
    for (let j = 0; j < 3; j++) {
      const s = [];
      for (let i = 0; i < 6; i++) { const a = rnd(f * 13 + j * 7 + i) * Math.PI * 2, l = ballK * 70 * (0.6 + rnd(f + j + i * 3)); s.push([hands[0] + 14 + Math.cos(a) * l, hands[1] + Math.sin(a) * l]); }
      crackle.push(<path key={j} d={pts(s)} fill="none" stroke="#e9fbff" strokeWidth={4} strokeLinecap="round" opacity={0.85} />);
    }
  }
  const bx = hands[0] + 10;

  return (
    <AbsoluteFill style={{ backgroundColor: '#0d0b1f' }}>
      <style>{`@font-face{font-family:Bangers;src:url(${staticFile('bangers.woff2')}) format('woff2');}`}</style>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H}>
        <defs>
          <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0d0b1f" /><stop offset=".45" stopColor="#2a1640" /><stop offset=".63" stopColor="#7a2f45" /><stop offset=".7" stopColor="#e2683a" />
          </linearGradient>
          <radialGradient id="ball" cx=".5" cy=".5" r=".5">
            <stop offset="0" stopColor="#ffffff" /><stop offset=".35" stopColor="#d8f6ff" /><stop offset=".7" stopColor="#6fd3ff" /><stop offset="1" stopColor="#2a7dff" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#2a7dff" stopOpacity="0" /><stop offset=".22" stopColor="#6fd3ff" /><stop offset=".42" stopColor="#e9fbff" /><stop offset=".5" stopColor="#ffffff" />
            <stop offset=".58" stopColor="#e9fbff" /><stop offset=".78" stopColor="#6fd3ff" /><stop offset="1" stopColor="#2a7dff" stopOpacity="0" />
          </linearGradient>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="9" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
          <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="30" /></filter>
        </defs>
        <g transform={`translate(${sx} ${sy})`}>
          <rect x={-60} y={-60} width={W + 120} height={H + 120} fill="url(#sky)" />
          {Array.from({ length: 90 }, (_, i) => <circle key={i} cx={(i * 137.5) % W} cy={(i * 61.7) % 1000} r={i % 7 === 0 ? 3 : 1.6} fill="#f6efe2" opacity={0.2 + (i % 5) * 0.12} />)}
          <path d={`M-60 1340 L120 1220 L300 1290 L470 1180 L640 1270 L820 1190 L1000 1260 L1140 1210 L1140 2000 L-60 2000 Z`} fill="#1d1430" />
          <rect x={-60} y={GROUND} width={W + 120} height={H} fill="#1a1328" />
          <line x1={-60} y1={GROUND} x2={W + 60} y2={GROUND} stroke="#3a2d5e" strokeWidth={4} />
          {[[120, 1480, 'l90 20 l60 -8'], [640, 1550, 'l110 -14 l60 26'], [380, 1660, 'l80 18']].map(([x, y, d], i) => <path key={i} d={`M${x} ${y} ${d}`} stroke="#2b2045" strokeWidth={4} fill="none" />)}
          <SpeedLines f={f} y={J.neck[1] + 60} op={speedOp} />
          <Aura J={J} a={aura} gold={gold} t={t} f={f} />
          <Stick J={JV} pose={vp} col={VEG_COL} hair="vegeta" t={t} flip />
          <Stick J={J} pose={gp} col={GOKU_COL} hair="goku" ssj={ssj} t={t} />
          {impacts}
          {/* Kamehameha */}
          {ballK > 0.01 && <circle cx={hands[0] + 14} cy={hands[1]} r={ballK * 120} fill="url(#ball)" filter="url(#glow)" opacity={0.9} />}
          {ballK > 0.01 && <circle cx={hands[0] + 14} cy={hands[1]} r={ballK * 62 * (1 + 0.08 * Math.sin(f * 1.3))} fill="url(#ball)" />}
          {crackle}
          {beamOn && beamLen > 4 && (
            <g>
              <rect x={bx} y={hands[1] - beamW / 2} width={beamLen} height={beamW} fill="url(#beam)" filter="url(#glow)" />
              <rect x={bx} y={hands[1] - beamW * 0.16} width={beamLen} height={beamW * 0.32} fill="#ffffff" opacity={0.95} />
              {beamLen < 1250 && <circle cx={bx + beamLen} cy={hands[1]} r={beamW * 0.9} fill="url(#ball)" filter="url(#glow)" />}
            </g>
          )}
          {call}
        </g>
        <rect x={0} y={0} width={W} height={H} fill="#ffffff" opacity={flash} />
        <text x={W / 2} y={1760} textAnchor="middle" fontFamily="Bangers" fontSize={64} fill="#f6efe2" opacity={0.5} letterSpacing={6}>@ANIMELOREHQ</text>
      </svg>
    </AbsoluteFill>
  );
};
