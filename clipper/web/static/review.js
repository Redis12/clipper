// Page de revue : une carte par clip, un clip « actif » piloté au clavier.
const C = window.CLIPPER;
const state = { clips: C.clips, focus: 0 };
const root = document.getElementById('clips');

const tc = (s) => {
  s = Math.max(0, s);
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = Math.floor(s % 60);
  const d = Math.floor((s * 10) % 10);
  return (h ? `${h}:${String(m).padStart(2, '0')}` : `${m}`) + `:${String(r).padStart(2, '0')}.${d}`;
};
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function toast(msg, ms = 2200) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), ms);
}

async function api(id, action, body) {
  const r = await fetch(`/api/clip/${id}/${action}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
  });
  const data = await r.json();
  if (!r.ok) { toast(data.error || 'Erreur', 4000); throw new Error(data.error); }
  return data;
}

const STATUS = {
  pending: ['warn', 'en préparation'], review: ['', 'à revoir'], approved: ['ok', 'validé'],
  rejected: ['no', 'rejeté'], uploaded: ['', 'uploadé'], rejected_auto: ['no', 'écarté'],
};

function card(c, i) {
  const d = c.end - c.start;
  const bad = d < C.minD || d > C.maxD;
  const [cls, label] = STATUS[c.status] || ['', c.status];
  const v = c.updated_at;
  const titles = (c.titles || []).map((t, k) => `
    <label><input type="radio" name="t${c.id}" ${k === (c.title_idx || 0) ? 'checked' : ''} data-act="title_idx" data-k="${k}">
      <input type="text" value="${esc(t)}" maxlength="${C.maxChars}" data-act="title" data-k="${k}">
      <span class="count ${t.length > C.maxChars ? 'bad' : ''}">${t.length}/${C.maxChars}</span></label>`).join('');
  const frames = (c.frames || []).map((f, k) =>
    `<img src="/media/frame/${c.id}/${k}.jpg?v=${encodeURIComponent(v)}" class="${k === c.frame_idx ? 'sel' : ''}"
          data-act="frame" data-k="${k}" title="${tc(f.t)}${f.face ? ' · visage' : ''}" loading="lazy">`).join('');
  return `
  <section class="clip panel s-${c.status} ${i === state.focus ? 'focus' : ''}" id="clip-${c.id}" data-i="${i}">
    <div>
      <video preload="none" src="/media/proxy/${C.videoId}.mp4" poster="${(c.frames || []).length ? `/media/frame/${c.id}/${c.frame_idx ?? 0}.jpg?v=${encodeURIComponent(v)}` : ''}" controls></video>
      <div class="bounds">
        <span>Début</span><b class="mono">${tc(c.start)}</b>
        <span class="btns"><button class="small" data-act="adj" data-edge="start" data-d="-1">−1 s</button><button class="small" data-act="adj" data-edge="start" data-d="1">+1 s</button></span>
        <span>Fin</span><b class="mono">${tc(c.end)}</b>
        <span class="btns"><button class="small" data-act="adj" data-edge="end" data-d="-1">−1 s</button><button class="small" data-act="adj" data-edge="end" data-d="1">+1 s</button></span>
        <span>Durée</span><span class="dur mono ${bad ? 'bad' : ''}">${tc(d)}${bad ? ` (attendu ${tc(C.minD)}–${tc(C.maxD)})` : ''}</span>
        <span>${c.start !== c.sel_start || c.end !== c.sel_end ? '<button class="small" data-act="adj" data-edge="restore">bornes d’origine</button>' : ''}</span>
      </div>
      <div class="field thumb"><span>Miniature</span>
        <div class="thumbrow">
          ${c.has_thumb ? `<img class="main" src="/media/thumb/${c.id}.jpg?v=${encodeURIComponent(v)}" title="Miniature envoyée à YouTube (1280×720)">` : '<div class="muted">en préparation…</div>'}
          <div class="frames">${frames}</div>
        </div>
        <div class="actions"><input type="text" value="${esc(c.thumb_text)}" data-act="thumb_text" placeholder="Texte de miniature (3-4 mots)">
          <button class="small" data-act="newframes" title="Réextraire 10 images sur les bornes actuelles">↻ images</button></div>
      </div>
    </div>
    <div>
      <div class="head"><span class="score">${c.score}</span><span class="pill ${cls}">${label}</span>
        ${c.publish_local ? `<span class="pill ok">sortie ${esc(c.publish_local)}</span>` : ''}
        ${c.render_needed && c.status === 'approved' ? '<span class="pill">rendu à refaire</span>' : ''}
        ${c.youtube_id ? `<a href="https://studio.youtube.com/video/${c.youtube_id}/edit" target="_blank">Studio ↗</a>` : ''}</div>
      <div class="topic">${esc(c.topic)}</div>
      <div class="reason">${esc(c.reason)}</div>
      ${c.error ? `<div class="err">${esc(c.error)}</div>` : ''}
      <div class="field titles"><span>Titre (choisis-en un)</span>${titles || '<div class="muted">en préparation…</div>'}</div>
      <div class="field"><span>Description</span><textarea rows="6" data-act="description">${esc(c.description)}</textarea></div>
      <div class="field"><span>Tags (séparés par des virgules)</span><input type="text" value="${esc((c.tags || []).join(', '))}" data-act="tags"></div>
      <div class="actions">
        <button class="ok" data-act="approve">Valider <span class="kbd">v</span></button>
        <button class="no" data-act="reject">Rejeter <span class="kbd">r</span></button>
        ${['approved', 'rejected'].includes(c.status) ? '<button data-act="reset">Annuler <span class="kbd">u</span></button>' : ''}
        <a class="muted" href="/media/clip/${c.id}.mp4" target="_blank" style="margin-left:auto;font-size:13px">clip rendu ↗</a>
      </div>
    </div>
  </section>`;
}

function render(keepScroll = true) {
  const y = window.scrollY;
  root.innerHTML = state.clips.map(card).join('') || '<p class="muted">Aucun clip pour l’instant.</p>';
  root.querySelectorAll('video').forEach(bindPlayer);
  if (keepScroll) window.scrollTo(0, y);
  summary();
}

function summary() {
  const n = (s) => state.clips.filter((c) => c.status === s).length;
  document.getElementById('summary').textContent =
    `${state.clips.length} clips · ${n('review')} à revoir · ${n('approved')} validés · ${n('rejected')} rejetés`;
}

function replace(c) {
  const i = state.clips.findIndex((x) => x.id === c.id);
  state.clips[i] = c;
  const el = document.getElementById(`clip-${c.id}`);
  const wasPlaying = el && !el.querySelector('video').paused;
  const tmp = document.createElement('div');
  tmp.innerHTML = card(c, i);
  el.replaceWith(tmp.firstElementChild);
  bindPlayer(document.querySelector(`#clip-${c.id} video`));
  summary();
  return wasPlaying;
}

// Le lecteur lit l’aperçu de la vidéo complète, borné au clip : ajuster ne demande aucun re-rendu.
function bindPlayer(video) {
  const sec = video.closest('.clip');
  const clip = () => state.clips[+sec.dataset.i];
  video.addEventListener('play', () => {
    const c = clip();
    if (video.currentTime < c.start - 0.05 || video.currentTime >= c.end - 0.05) video.currentTime = c.start;
    document.querySelectorAll('video').forEach((o) => o !== video && o.pause());
  });
  video.addEventListener('timeupdate', () => { if (video.currentTime >= clip().end) video.pause(); });
}

function playAt(i, from) {
  const v = document.querySelector(`#clip-${state.clips[i].id} video`);
  const go = () => { v.currentTime = from; v.play(); };
  if (v.readyState >= 1) go(); else { v.preload = 'auto'; v.addEventListener('loadedmetadata', go, { once: true }); v.load(); }
}

function setFocus(i, scroll = true) {
  i = Math.max(0, Math.min(state.clips.length - 1, i));
  document.querySelectorAll('.clip.focus').forEach((e) => e.classList.remove('focus'));
  state.focus = i;
  const el = document.getElementById(`clip-${state.clips[i].id}`);
  el.classList.add('focus');
  if (scroll) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function act(i, name, el) {
  const c = state.clips[i];
  if (name === 'approve') {
    const r = await api(c.id, 'approve');
    replace(r); toast(`Validé · sortie ${r.publish_local}`);
    const next = state.clips.findIndex((x, k) => k > i && x.status === 'review');
    if (next >= 0) setFocus(next);
  } else if (name === 'reject') {
    replace(await api(c.id, 'reject')); toast('Rejeté');
    const next = state.clips.findIndex((x, k) => k > i && x.status === 'review');
    if (next >= 0) setFocus(next);
  } else if (name === 'reset') {
    replace(await api(c.id, 'reset')); toast('Décision annulée');
  } else if (name === 'adj') {
    const r = await api(c.id, 'adjust', { edge: el.dataset.edge, delta: +el.dataset.d || 0 });
    replace(r);
    // Rejoue autour de la borne modifiée pour juger à l’oreille.
    if (el.dataset.edge === 'start') playAt(i, r.start);
    else if (el.dataset.edge === 'end') playAt(i, Math.max(r.start, r.end - 5));
  } else if (name === 'frame') {
    toast('Miniature…', 800);
    replace(await api(c.id, 'meta', { frame_idx: +el.dataset.k }));
  } else if (name === 'title_idx') {
    replace(await api(c.id, 'meta', { title_idx: +el.dataset.k }));
  } else if (name === 'newframes') {
    toast('Extraction de 10 images…', 4000);
    replace(await api(c.id, 'frames'));
  }
}

async function saveField(i, el) {
  const c = state.clips[i];
  const a = el.dataset.act;
  let body;
  if (a === 'title') { const t = [...c.titles]; t[+el.dataset.k] = el.value; body = { titles: t }; }
  else if (a === 'description') body = { description: el.value };
  else if (a === 'tags') body = { tags: el.value.split(',') };
  else if (a === 'thumb_text') body = { thumb_text: el.value };
  else return;
  const r = await api(c.id, 'meta', body);
  state.clips[i] = r;
  if (a === 'thumb_text') replace(r);
  toast('Enregistré', 900);
}

root.addEventListener('click', (e) => {
  const el = e.target.closest('[data-act]');
  const sec = e.target.closest('.clip');
  if (!sec) return;
  const i = +sec.dataset.i;
  if (i !== state.focus) setFocus(i, false);
  if (!el || el.tagName === 'INPUT' && el.type === 'text' || el.tagName === 'TEXTAREA') return;
  act(i, el.dataset.act, el).catch(() => {});
});
root.addEventListener('change', (e) => {
  const sec = e.target.closest('.clip');
  if (sec && e.target.matches('input[type=text], textarea')) saveField(+sec.dataset.i, e.target).catch(() => {});
});
root.addEventListener('input', (e) => {
  if (e.target.dataset.act !== 'title') return;
  const n = e.target.value.length, cnt = e.target.parentElement.querySelector('.count');
  cnt.textContent = `${n}/${C.maxChars}`; cnt.classList.toggle('bad', n > C.maxChars);
});

const KEYS = { '1': 0, '&': 0, '2': 1, 'é': 1, '3': 2, '"': 2 };
document.addEventListener('keydown', (e) => {
  const t = e.target;
  if (t.matches?.('input[type=text], input[type=url], textarea')) {
    if (e.key === 'Escape') t.blur();
    return;
  }
  if (e.ctrlKey || e.metaKey || e.altKey || !state.clips.length) return;
  const i = state.focus, c = state.clips[i];
  const v = document.querySelector(`#clip-${c.id} video`);
  const fake = (edge, d) => ({ dataset: { edge, d } });
  const k = e.key;
  const run = (p) => { e.preventDefault(); p.catch(() => {}); };
  if (k === 'j' || k === 'ArrowDown') { e.preventDefault(); setFocus(i + 1); }
  else if (k === 'k' || k === 'ArrowUp') { e.preventDefault(); setFocus(i - 1); }
  else if (k === ' ') { e.preventDefault(); v.paused ? playAt(i, v.currentTime > c.start && v.currentTime < c.end ? v.currentTime : c.start) : v.pause(); }
  else if (k === 'd') { e.preventDefault(); playAt(i, c.start); }
  else if (k === 'f') { e.preventDefault(); playAt(i, Math.max(c.start, c.end - 8)); }
  else if (k === 'a') run(act(i, 'adj', fake('start', -1)));
  else if (k === 'z') run(act(i, 'adj', fake('start', 1)));
  else if (k === 'q') run(act(i, 'adj', fake('end', -1)));
  else if (k === 's') run(act(i, 'adj', fake('end', 1)));
  else if (k === 'v') run(act(i, 'approve'));
  else if (k === 'r') run(act(i, 'reject'));
  else if (k === 'u') run(act(i, 'reset'));
  else if (k in KEYS && c.titles && KEYS[k] < c.titles.length) run(act(i, 'title_idx', { dataset: { k: KEYS[k] } }));
  else if (k === 't' || k === 'T') {
    const n = (c.frames || []).length;
    if (n) run(act(i, 'frame', { dataset: { k: ((c.frame_idx ?? 0) + (k === 'T' ? -1 : 1) + n) % n } }));
  }
  else if (k === '?') toggleHelp();
});

function toggleHelp() { document.getElementById('help').classList.toggle('show'); }
async function rescue(id) {
  await fetch(`/api/clip/${id}/reset`, { method: 'POST' });
  toast('Repêché : titres et miniature en préparation…');
  setTimeout(() => location.reload(), 1500);
}

// Ouvre directement sur un clip si l’URL contient #clip-ID.
render(false);
const m = location.hash.match(/^#clip-(\d+)$/);
if (m) { const i = state.clips.findIndex((c) => c.id === +m[1]); if (i >= 0) setFocus(i); }
// Tant que des clips sont en préparation, on rafraîchit.
if (state.clips.some((c) => c.status === 'pending')) setTimeout(() => location.reload(), 8000);
