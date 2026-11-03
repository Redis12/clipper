// Revue d'un slideshow : bande de slides éditables, choix d'image, publication.
let S = window.SS;
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const words = (t) => (t || '').trim().split(/\s+/).filter(Boolean).length;
const STATUS = { review: ['', 'à valider'], approved: ['ok', 'validé'], published: ['ok', 'publié'], rejected: ['no', 'rejeté'],
                 drafting: ['warn', 'en préparation'], queued: ['warn', 'en attente'], failed: ['no', 'échec'], idea: ['', 'idée'] };
const PLAT = { youtube: 'YouTube Short', instagram: 'Instagram', tiktok: 'TikTok' };

function toast(m, ms = 2200) {
  const t = document.getElementById('toast'); t.textContent = m; t.classList.add('show');
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove('show'), ms);
}

async function api(path, body) {
  const r = await fetch(`/api/slides/${S.id}/${path}`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
                                                         body: JSON.stringify(body || {}) });
  const d = await r.json();
  if (!r.ok) { toast(d.error || 'Erreur', 4000); throw new Error(d.error); }
  return d;
}

function slideCard(sl, i) {
  const n = i + 1, v = encodeURIComponent(S.v);
  const alts = Array.from({ length: Math.min(sl.n_alts, 8) }, (_, k) =>
    `<img src="/media/slide-alt/${S.id}/${i}/${k + 1}.jpg" data-k="${k + 1}" title="Utiliser cette image" loading="lazy">`).join('');
  const w = words(sl.text);
  const flags = [
    !sl.has_image && sl.kind === 'body' ? '<span class="warn">pas d’image</span>' : '',
    sl.kind === 'body' && sl.confidence < 70 ? `<span class="warn">fait incertain (${sl.confidence}) : vérifie</span>` : '',
    sl.has_image && sl.character && sl.character_match === false ? `<span class="warn">${esc(sl.character)} pas trouvé</span>` : '',
    sl.kind === 'body' && w > window.MAX_WORDS ? `<span class="warn">${w} mots</span>` : '',
  ].join(' ');
  return `<div class="sl" data-i="${i}">
    <div class="slwrap"><img class="r" src="/media/slide/${S.id}/vertical/${n}.jpg?v=${v}" alt="slide ${n}">
      ${sl.kind !== 'cover' ? '<button class="del" data-act="delete" title="Supprimer cette slide du post">✕</button>' : ''}</div>
    <div class="muted" style="font-size:12px;margin-top:4px">${n}. ${sl.kind === 'cover' ? 'couverture' : sl.kind === 'end' ? 'fin' : 'slide'} ${flags}</div>
    ${sl.kind === 'body' ? `<div class="row"><input type="text" value="${esc(sl.label)}" data-f="label" placeholder="étiquette (#1)"></div>` : ''}
    <textarea rows="3" data-f="text">${esc(sl.text)}</textarea>
    <div class="row"><input type="text" value="${esc(sl.character)}" data-f="character" placeholder="personnage">
      <button class="small" data-act="choose" title="Choisir toi-même parmi les images de ce perso">Choisir</button>
      <button class="small" data-act="repick" title="Laisser Claude rechercher une autre image">Chercher</button>
      <label class="small btnlike" title="Choisir une image sur ton PC">Ajouter<input type="file" accept="image/*" data-act="upload" hidden></label></div>
    <div class="alts">${alts}</div>
    <div class="picker" hidden></div>
  </div>`;
}

function render() {
  document.getElementById('strip').innerHTML = S.slides.map(slideCard).join('');
  const [cls, label] = STATUS[S.status] || ['', S.status];
  document.getElementById('status').innerHTML = `<span class="pill ${cls}">${label}</span>`;
  document.getElementById('when').textContent = S.publish_at ? `sortie ${S.publish_audience} (heure du public) · ${S.publish_local} à Bruxelles` : 'pas encore programmé';
  document.getElementById('warn').textContent = S.error || '';
  document.getElementById('caption').value = S.caption || '';
  document.getElementById('hashtags').value = (S.hashtags || []).map((h) => '#' + h).join(' ');
  document.getElementById('yt_title').value = S.yt_title || '';
  if (S.has_grid) {
    document.getElementById('gridbox').style.display = '';
    document.getElementById('grid').src = `/media/grid/${S.id}/vertical.jpg?v=${encodeURIComponent(S.v)}`;
  }
  document.getElementById('short').style.display = S.has_video ? '' : 'none';
  document.getElementById('novideo').style.display = S.has_video ? 'none' : '';
  document.getElementById('videobtn').textContent = S.has_video ? 'Refaire la vidéo' : 'Générer la vidéo';
  document.getElementById('packshort').style.display = S.has_video ? '' : 'none';
  const vid = document.getElementById('short');
  vid.poster = `/media/slide/${S.id}/vertical/1.jpg?v=${encodeURIComponent(S.v)}`;
  if (S.has_video && !vid.src.includes(encodeURIComponent(S.v))) vid.src = `/media/short/${S.id}.mp4?v=${encodeURIComponent(S.v)}`;
  const a = document.getElementById('actions');
  a.innerHTML = S.status === 'review' ? '<button class="ok" onclick="decide(\'approve\')">Valider <span class="kbd">v</span></button> <button class="no" onclick="decide(\'reject\')">Rejeter</button>'
    : S.status === 'approved' ? '<button onclick="decide(\'unapprove\')">Annuler la validation</button>' : '';
  document.getElementById('posts').innerHTML = (S.posts || []).map((p) => `<div style="font-size:14px;margin:3px 0">
      <b>${PLAT[p.platform]}</b> : ${p.status === 'done' ? `<span class="pill ok">publié</span> ${p.url ? `<a href="${esc(p.url)}" target="_blank">voir ↗</a>` : ''}`
        : p.mode === 'manual' ? `<span class="pill">à poster à la main</span> <a href="/slides/${S.id}/pack/${p.platform}.zip">pack</a>
           <button class="small" onclick="manualDone(${p.id})">C'est posté</button>`
        : `<span class="pill warn">${p.status === 'failed' ? 'échec, nouvel essai' : 'automatique'}</span>`}
      ${p.error ? `<div class="err">${esc(p.error)}</div>` : ''}</div>`).join('') || '<span class="muted">Valide pour programmer.</span>';
}

async function decide(a) {
  S = await api(a);
  toast(a === 'approve' ? `Programmé : ${S.publish_audience} (heure du public)` : 'Fait');
  render();
}

async function rerender() {
  await api('rerender'); toast('Vidéo en cours… elle apparaîtra ici dans une minute', 4000);
  setTimeout(() => location.reload(), 45000);
}

async function manualDone(pid) {
  const url = prompt('Lien du post (facultatif) :') || '';
  await fetch(`/api/posts/${pid}/done`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) });
  location.reload();
}

const strip = document.getElementById('strip');
strip.addEventListener('change', async (e) => {
  if (e.target.dataset.act === 'upload' && e.target.files.length) {
    const card = e.target.closest('.sl');
    const fd = new FormData(); fd.append('file', e.target.files[0]);
    toast('Envoi de l’image…', 1500);
    const r = await fetch(`/api/slides/${S.id}/slide/${card.dataset.i}/upload`, { method: 'POST', body: fd });
    const d = await r.json();
    if (!r.ok) { toast(d.error || 'Erreur', 4000); return; }
    S = d; render(); toast('Image ajoutée', 1200);
    return;
  }
  const card = e.target.closest('.sl'); const f = e.target.dataset.f;
  if (!card || !f) return;
  toast('Redessin…', 800);
  S = await api(`slide/${card.dataset.i}`, { [f]: e.target.value });
  render();
});
strip.addEventListener('click', async (e) => {
  const card = e.target.closest('.sl'); if (!card) return;
  const i = card.dataset.i;
  if (e.target.matches('.alts img')) { toast('Image changée', 800); S = await api(`slide/${i}/image/${e.target.dataset.k}`); render(); }
  else if (e.target.dataset.act === 'choose') {
    const box = card.querySelector('.picker');
    if (!box.hidden) { box.hidden = true; return; }
    const list = await (await fetch(`/api/slides/${S.id}/slide/${i}/choices`)).json();
    box.innerHTML = list.length ? list.map((c) => `<figure class="${c.current ? 'cur' : ''}">
        <img src="/media/lib/${c.id}.jpg" data-lib="${c.id}" loading="lazy" title="${esc(c.character)}">
        <figcaption>${c.uses ? `utilisée ${c.uses}×` : 'jamais utilisée'}</figcaption></figure>`).join('')
      : '<span class="muted">Aucune image pour ce perso : utilise « Ajouter ».</span>';
    box.hidden = false;
  }
  else if (e.target.dataset.lib) { toast('Image changée', 800); S = await api(`slide/${i}/lib/${e.target.dataset.lib}`); render(); }
  else if (e.target.dataset.act === 'delete') {
    if (!confirm('Supprimer cette slide du post ?')) return;
    S = await api(`slide/${i}/delete`); render(); toast('Slide supprimée', 1200);
  }
  else if (e.target.dataset.act === 'repick') { toast('Recherche d’image…', 3000); S = await api(`slide/${i}/repick`); render(); }
});
for (const id of ['caption', 'hashtags', 'yt_title']) {
  document.getElementById(id).addEventListener('change', async (e) => { S = await api('meta', { [id]: e.target.value }); toast('Enregistré', 900); });
}
document.addEventListener('keydown', (e) => {
  if (e.target.matches('input, textarea')) { if (e.key === 'Escape') e.target.blur(); return; }
  if (e.key === 'v' && S.status === 'review') decide('approve');
});
render();
if (['drafting', 'queued'].includes(S.status)) setTimeout(() => location.reload(), 5000);
