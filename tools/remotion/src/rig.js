// Rig stickman (angles absolus en degrés, 0 = droite, 90 = bas ; perso tourné vers la droite) + poses + timeline.
export const L = { torso: 74, neck: 10, head: 21, uarm: 38, farm: 36, thigh: 50, shin: 50 };

export const P = {
  stance:  { torso: -82, neck: -84, uaF: 32, faF: -48, uaB: 112, faB: 20, thF: 62, shF: 98, thB: 122, shB: 84, x: 0, y: 0, rot: 0 },
  breathe: { torso: -85, neck: -87, uaF: 36, faF: -44, uaB: 114, faB: 26, thF: 64, shF: 99, thB: 120, shB: 85, x: 0, y: 0, rot: 0 },
  charge:  { torso: -96, neck: -104, uaF: 112, faF: 50, uaB: 72, faB: 128, thF: 46, shF: 100, thB: 134, shB: 80, x: 0, y: 0, rot: 0 },
  scream:  { torso: -100, neck: -118, uaF: 128, faF: 40, uaB: 58, faB: 140, thF: 42, shF: 102, thB: 138, shB: 78, x: 0, y: 0, rot: 0 },
  dash:    { torso: -40, neck: -50, uaF: 160, faF: 170, uaB: 170, faB: 180, thF: 120, shF: 150, thB: 150, shB: 170, x: 0, y: -30, rot: 0 },
  jab:     { torso: -72, neck: -78, uaF: -2, faF: -2, uaB: 108, faB: -30, thF: 54, shF: 100, thB: 128, shB: 82, x: 18, y: 0, rot: 0 },
  cross:   { torso: -66, neck: -74, uaF: 70, faF: -60, uaB: -4, faB: -3, thF: 50, shF: 104, thB: 134, shB: 76, x: 34, y: 0, rot: 0 },
  hook:    { torso: -76, neck: -80, uaF: -20, faF: 40, uaB: 100, faB: -40, thF: 56, shF: 100, thB: 126, shB: 82, x: 26, y: 0, rot: 0 },
  upper:   { torso: -98, neck: -102, uaF: -40, faF: -96, uaB: 96, faB: 20, thF: 70, shF: 96, thB: 120, shB: 86, x: 30, y: -18, rot: 0 },
  kickW:   { torso: -100, neck: -96, uaF: 40, faF: -30, uaB: 160, faB: 110, thF: 10, shF: 110, thB: 98, shB: 92, x: 22, y: 0, rot: 0 },
  kick:    { torso: -118, neck: -104, uaF: 60, faF: 10, uaB: 190, faB: 160, thF: -14, shF: -10, thB: 96, shB: 90, x: 36, y: 0, rot: 0 },
  kameBk:  { torso: -104, neck: -92, uaF: 150, faF: 196, uaB: 146, faB: 192, thF: 44, shF: 102, thB: 136, shB: 78, x: -16, y: 0, rot: 0 },
  kameFr:  { torso: -76, neck: -80, uaF: -2, faF: 0, uaB: 2, faB: 4, thF: 48, shF: 104, thB: 138, shB: 74, x: 10, y: 0, rot: 0 },
  // adversaire (dessiné en miroir : « droite » = vers Goku)
  guard:   { torso: -84, neck: -86, uaF: -20, faF: -80, uaB: 10, faB: -70, thF: 64, shF: 96, thB: 118, shB: 86, x: 0, y: 0, rot: 0 },
  hurt:    { torso: -118, neck: -140, uaF: 60, faF: 100, uaB: 120, faB: 150, thF: 70, shF: 92, thB: 112, shB: 70, x: -26, y: 0, rot: 0 },
  hurt2:   { torso: -126, neck: -152, uaF: 80, faF: 130, uaB: 140, faB: 170, thF: 60, shF: 100, thB: 118, shB: 66, x: -40, y: 0, rot: 0 },
  fly:     { torso: -160, neck: -175, uaF: 120, faF: 160, uaB: 200, faB: 220, thF: 30, shF: 60, thB: 10, shB: 40, x: -320, y: -140, rot: 0 },
  down:    { torso: 182, neck: 186, uaF: 140, faF: 170, uaB: 210, faB: 190, thF: 2, shF: 8, thB: -6, shB: 4, x: -420, y: 0, rot: 0 },
};
export const KEYS = Object.keys(P.stance);

export const ease = {
  lin: (t) => t,
  out: (t) => 1 - Math.pow(1 - t, 3),
  inout: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  snap: (t) => 1 - Math.pow(1 - t, 6),
  back: (t) => { const c = 1.9; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); },
};

// timeline : [[frame, pose (objet ou nom), easing], …] → pose à la frame f
export function poseAt(track, f) {
  const get = (p) => (typeof p === 'string' ? P[p] : p);
  if (f <= track[0][0]) return { ...P.stance, ...get(track[0][1]) };
  for (let i = 1; i < track.length; i++) {
    const [f1, p1, e] = track[i];
    const [f0, p0] = track[i - 1];
    if (f <= f1) {
      const a = { ...P.stance, ...get(p0) }, b = { ...P.stance, ...get(p1) };
      const k = (ease[e || 'out'])(Math.min(1, Math.max(0, (f - f0) / Math.max(1, f1 - f0))));
      const o = {};
      for (const key of KEYS) o[key] = a[key] + (b[key] - a[key]) * k;
      return o;
    }
  }
  return { ...P.stance, ...get(track[track.length - 1][1]) };
}

const rad = (d) => (d * Math.PI) / 180;
export const dir = (a, l) => [Math.cos(rad(a)) * l, Math.sin(rad(a)) * l];
export const add = (p, v) => [p[0] + v[0], p[1] + v[1]];

// joints : pieds posés sur le sol (sauf y < 0 = en l'air)
export function joints(p, baseX, ground, s = 1) {
  const hip0 = [baseX + p.x * s, 0];
  const d = (a, l) => dir(a, l * s);
  const kF = add(hip0, d(p.thF, L.thigh)), aF = add(kF, d(p.shF, L.shin));
  const kB = add(hip0, d(p.thB, L.thigh)), aB = add(kB, d(p.shB, L.shin));
  const low = Math.max(aF[1], aB[1]);
  const dy = ground - 8 * s - low + p.y * s;
  const sh = (v) => [v[0], v[1] + dy];
  const hip = sh(hip0);
  const neck = add(hip, d(p.torso, L.torso));
  const head = add(neck, d(p.neck, L.neck + L.head));
  const shF = add(neck, d(p.torso + 180, 6)), shB = add(neck, d(p.torso + 180, 9));
  const eF = add(shF, d(p.uaF, L.uarm)), wF = add(eF, d(p.faF, L.farm));
  const eB = add(shB, d(p.uaB, L.uarm)), wB = add(eB, d(p.faB, L.farm));
  return { hip, neck, head, shF, shB, eF, wF, eB, wB, kF: sh(kF), aF: sh(aF), kB: sh(kB), aB: sh(aB) };
}

// bruit déterministe
export function rnd(i) {
  const x = Math.sin(i * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
}
export const pts = (a) => a.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join(' ');
export function mix(a, b, t) {
  const pa = a.match(/\w\w/g).map((h) => parseInt(h, 16)), pb = b.match(/\w\w/g).map((h) => parseInt(h, 16));
  return '#' + pa.map((v, i) => Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, '0')).join('');
}
