// One menu for every page. Each page loads this as the first thing in <body>, and
// it writes the same bar — the same links, in the same order, in the same place —
// so nothing shifts from one page to the next. The pages used to carry their own
// menus: six different sets of links, some on the left and some on the right.
//
// The public links sit on a row of their own that never changes. What depends on
// who is signed in (the research and admin menus) sits at the right of the row
// above, where it appearing a moment later cannot push the links along.
//
// Plain divs rather than <header> and <nav>: many pages style those tags directly,
// and those rules would reach into the bar.
(function () {
  const LINKS = [
    ['/', '🗺', 'Map'],
    ['/people', '👤', 'People'],
    ['/significant', '★', 'Notable'],
    ['/architects', '🏛', 'Architects'],
    ['/census', '📜', 'Census'],
    ['/family-tree', '🌳', 'Family trees'],
    ['/stats', '📈', 'Insights'],
    ['/origins', '🌍', 'Origins'],
    ['/archive', '🗄', 'Archive'],
    ['/research', '❓', 'Open questions'],
    ['/dashboard', '📊', 'Dashboard'],
  ];
  const WORK = [
    ['/tasks', '✔', 'The working list'],
    ['/unfiled', '📥', 'Unfiled records'],
    ['/census/unresolved', '🔍', 'Unresolved census'],
    ['/reassign', '↔', "Split a house's census"],
    ['/duplicates', '👥', 'Duplicate people'],
    ['/crowding', '⚠', 'Crowded houses'],
    ['/osm', '📍', 'Positions vs OpenStreetMap'],
    ['/gazette-review', '📰', 'Gazette review'],
    ['/wikidata-review', '🔗', 'Wikidata review'],
    ['/name-sex', '⚥', 'Forename sex'],
  ];
  const MINE = [
    ['/watchlist', '⭐', 'My watchlist'],
    ['/my-contributions', '✏', 'My contributions'],
  ];
  const ADMIN = [
    ['/admin', '🛠', 'Admin tools'],
    ['/admin/users', '👤', 'Users'],
    ['/admin/birthplaces', '🌍', 'Birthplaces'],
  ];

  // The page you are on: an exact match, else the longest link it sits under
  // (/architects/person/12 is still Architects).
  const path = location.pathname.replace(/\/+$/, '') || '/';
  const all = [...LINKS, ...WORK, ...MINE, ...ADMIN].map(l => l[0]);
  const here = all.includes(path) ? path
    : all.filter(h => h !== '/' && path.startsWith(h + '/')).sort((a, b) => b.length - a.length)[0] || null;

  const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  const link = (l, cls) => `<a class="${cls}${l[0] === here ? ' is-here' : ''}" href="${l[0]}"`
    + `${l[0] === here ? ' aria-current="page"' : ''}><span class="pnav-i" aria-hidden="true">${l[1]}</span>${esc(l[2])}</a>`;
  const menu = (label, groups) => {
    const items = groups.flat();
    return `<details class="pnav-menu"><summary${items.some(i => i[0] === here) ? ' class="is-here"' : ''}>${label}</summary>`
      + `<div class="pnav-drop">${groups.filter(g => g.length).map(g => g.map(i => link(i, 'pnav-item')).join('')).join('<hr>')}</div></details>`;
  };

  const css = `
.pnav{background:#25401f;color:#f2ecd8;font-family:Georgia,'Times New Roman',serif;line-height:1.3;
  flex-shrink:0;position:relative;z-index:2000;text-align:left;font-size:16px}
.pnav *{box-sizing:border-box;margin:0;padding:0;font-family:inherit;letter-spacing:normal}
.pnav-top{display:flex;align-items:center;gap:12px;padding:8px 20px;min-height:50px}
.pnav a.pnav-brand{color:#f2ecd8;text-decoration:none;display:block;background:none;border:0}
.pnav-brand b{display:block;font-size:1.12rem;font-weight:700}
.pnav-brand small{display:block;font-size:.64rem;letter-spacing:.13em;text-transform:uppercase;color:#b9c9a8;margin-top:1px}
.pnav-side{margin-left:auto;display:flex;align-items:center;gap:8px}
.pnav-extra,.pnav-account{display:flex;align-items:center;gap:6px}
.pnav-row{background:#2f4d27;padding:6px 20px;display:flex;gap:4px;flex-wrap:wrap;scrollbar-width:none}
.pnav-row::-webkit-scrollbar{display:none}
.pnav a.pnav-link{color:#e8e2cf;text-decoration:none;font-size:.8rem;padding:4px 11px;border-radius:4px;
  white-space:nowrap;display:inline-flex;gap:4px;align-items:center;background:none;border:0;font-weight:400}
.pnav a.pnav-link:hover{background:rgba(255,255,255,.12)}
.pnav a.pnav-link.is-here{background:#f2ecd8;color:#25401f;font-weight:600}
.pnav-menu{position:relative}
.pnav-menu>summary{list-style:none;cursor:pointer;color:#e8e2cf;font-size:.8rem;padding:4px 11px;
  border:1px solid rgba(255,255,255,.28);border-radius:4px;white-space:nowrap;user-select:none}
.pnav-menu>summary::-webkit-details-marker{display:none}
.pnav-menu>summary::after{content:" \\25BE";font-size:.72rem}
.pnav-menu>summary:hover,.pnav-menu[open]>summary{background:rgba(255,255,255,.12)}
.pnav-menu>summary.is-here{background:#f2ecd8;color:#25401f;font-weight:600}
.pnav-drop{position:absolute;right:0;top:calc(100% + 6px);background:#fffdf7;border:1px solid #d8ceb4;
  border-radius:6px;box-shadow:0 8px 24px rgba(0,0,0,.28);padding:5px;min-width:240px;z-index:2001}
.pnav a.pnav-item{display:flex;gap:8px;align-items:center;color:#2a2418;text-decoration:none;font-size:.84rem;
  padding:6px 10px;border-radius:4px;white-space:nowrap;background:none;border:0}
.pnav a.pnav-item:hover{background:#f0ead8}
.pnav a.pnav-item.is-here{background:#e4ecdc;font-weight:600}
.pnav-drop hr{border:0;border-top:1px solid #e8dfc8;margin:4px 2px}
.pnav-i{display:inline-block;min-width:1.1em;text-align:center}
.pnav-extra button{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.25);color:#e8dfc8;
  padding:5px 13px;border-radius:4px;cursor:pointer;font-size:.8rem}
.pnav-extra button:hover{background:rgba(255,255,255,.2)}
.pnav-extra button.primary{background:#4a7c5a;border-color:#3a6a4a}
.pnav a:focus-visible,.pnav summary:focus-visible,.pnav button:focus-visible{outline:2px solid #f2d68a;outline-offset:2px}
@media (max-width:700px){
  .pnav-top{padding:6px 12px;min-height:44px}
  .pnav-brand small{display:none}
  .pnav-brand b{font-size:.95rem}
  .pnav-row{padding:5px 12px;flex-wrap:nowrap;overflow-x:auto}
  .pnav-extra button{padding:4px 8px;font-size:.72rem}
}`;
  const style = document.createElement('style');
  style.id = 'pnav-style';
  style.textContent = css;
  document.head.appendChild(style);

  const bar = `<div class="pnav" role="banner">
    <div class="pnav-top">
      <a class="pnav-brand" href="/"><b>Nottingham Park Houses</b><small>The Park Conservation Trust — Historical Record</small></a>
      <div class="pnav-side"><div class="pnav-extra" id="pnavExtra"></div><div class="pnav-account" id="pnavAccount"></div></div>
    </div>
    <div class="pnav-row" role="navigation" aria-label="Site">${LINKS.map(l => link(l, 'pnav-link')).join('')}</div>
  </div>`;
  const me = document.currentScript;
  if (me) me.insertAdjacentHTML('beforebegin', bar);
  else document.body.insertAdjacentHTML('afterbegin', bar);
  const el = document.querySelector('.pnav');

  // Pages that need their height below the bar (the map) read this.
  const setHeight = () => document.documentElement.style.setProperty('--site-nav-h', el.offsetHeight + 'px');
  setHeight();
  window.addEventListener('resize', setHeight);

  // A page's own controls for the bar — the map's search, sign-in and so on — are
  // written inside <div id="navExtra" hidden> and moved in once the page has parsed.
  document.addEventListener('DOMContentLoaded', () => {
    const extra = document.getElementById('navExtra');
    if (extra) {
      const slot = document.getElementById('pnavExtra');
      while (extra.firstChild) slot.appendChild(extra.firstChild);
      extra.remove();
    }
    setHeight();
  });

  fetch('/api/me', { credentials: 'same-origin' }).then(r => r.json()).then(d => {
    const acct = document.getElementById('pnavAccount');
    if (!acct) return;
    const contributor = d.isAdmin || (d.user && (d.user.role === 'contributor' || d.user.role === 'admin') && d.user.approved);
    const signedIn = d.isAdmin || d.user;
    let html = '';
    if (signedIn) html += menu('Research', [contributor ? WORK : [], d.user ? MINE : []].filter(g => g.length));
    if (d.isAdmin) html += menu('Admin', [ADMIN]);
    if (!signedIn && path !== '/join') html += link(['/join', '✍', 'Join the record'], 'pnav-link');
    acct.innerHTML = html;
    setHeight();
  }).catch(() => {});

  // One menu open at a time; a click elsewhere or Escape closes it.
  document.addEventListener('toggle', e => {
    if (!e.target.matches || !e.target.matches('.pnav-menu') || !e.target.open) return;
    document.querySelectorAll('.pnav-menu[open]').forEach(m => { if (m !== e.target) m.open = false; });
  }, true);
  document.addEventListener('click', e => {
    document.querySelectorAll('.pnav-menu[open]').forEach(m => { if (!m.contains(e.target)) m.open = false; });
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.pnav-menu[open]').forEach(m => { m.open = false; });
  });
})();
