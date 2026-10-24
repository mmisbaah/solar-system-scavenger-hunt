import { chromium } from 'playwright';
const sizes = (process.argv[2] || '1350x662,1280x800,1024x768,768x1024,390x760,360x600').split(',').map(s => s.split('x').map(Number));
const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const CHECK = () => {
  const root = document.querySelector('dialog[open]') || document.querySelector('#celebrate:not([hidden])') || (!home.hidden ? home : document.querySelector('.app'));
  const clip = (el, r) => {
    for (let a = el.parentElement; a && a !== document.documentElement; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (/(hidden|auto|scroll|clip)/.test(cs.overflow + cs.overflowX + cs.overflowY)) {
        const c = a.getBoundingClientRect();
        r = { left: Math.max(r.left, c.left), right: Math.min(r.right, c.right), top: Math.max(r.top, c.top), bottom: Math.min(r.bottom, c.bottom) };
        if (r.right - r.left < 1 || r.bottom - r.top < 1) return null;
      }
    }
    return r;
  };
  const items = []; const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  for (let n; (n = w.nextNode());) {
    if (!n.textContent.trim()) continue;
    const el = n.parentElement; if (el.closest('svg, .sr, [hidden], .shoot')) continue;
    if (!el.checkVisibility({ opacityProperty: true, visibilityProperty: true })) continue;
    const rg = document.createRange(); rg.selectNodeContents(n);
    for (const r0 of rg.getClientRects()) {
      if (r0.width < 2 || r0.height < 2) continue;
      // trim line box to glyph-ish height
      const fs = parseFloat(getComputedStyle(el).fontSize), mid = (r0.top + r0.bottom) / 2, h = Math.min(r0.height, fs * 0.9);
      const r = clip(el, { left: r0.left, right: r0.right, top: mid - h / 2, bottom: mid + h / 2 }); if (r) items.push({ el, n, r, t: n.textContent.trim().slice(0, 30) });
    }
  }
  const out = []; const W = innerWidth;
  for (let i = 0; i < items.length; i++) {
    const a = items[i];
    if (a.r.right > W + 1 || a.r.left < -1) out.push(`OFFSCREEN "${a.t}"`);
    for (let j = i + 1; j < items.length; j++) {
      const c = items[j]; if (c.n === a.n) continue;
      const ox = Math.min(a.r.right, c.r.right) - Math.max(a.r.left, c.r.left), oy = Math.min(a.r.bottom, c.r.bottom) - Math.max(a.r.top, c.r.top);
      if (ox > 3 && oy > 3) out.push(`"${a.t}" <${a.el.className || a.el.tagName}> x "${c.t}" <${c.el.className || c.el.tagName}> (${Math.round(ox)}x${Math.round(oy)})`);
    }
  }
  return [...new Set(out)];
};
const report = {};
for (const [w, h] of sizes) {
  const p = await b.newPage({ viewport: { width: w, height: h } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + process.cwd() + '/index.html'); await p.waitForTimeout(700);
  await p.addStyleTag({ content: '*,*::before,*::after{animation-duration:0s!important;animation-delay:0s!important;transition:none!important}' });
  const chk = async (name, fn, arg) => {
    try { if (fn) await p.evaluate(fn, arg); } catch (e) { (report[name] ??= []).push(`${w}x${h} SETUP ERR ${e.message.split('\n')[0]}`); return; }
    await p.waitForTimeout(60);
    for (const o of await p.evaluate(CHECK)) (report[name] ??= []).push(`${w}x${h} ${o}`);
  };
  const go = (setup) => `(() => { document.querySelectorAll('dialog[open]').forEach(d => d.close()); ${setup} })()`;
  await chk('home-title', () => showHome('title'));
  await chk('home-missions', () => showHome('missions'));
  await p.evaluate(() => { P.xp = 123456; P.badges = BADGES.map(b => b.id); P.dailyStreak = 12; P.bestSpeed = 22; store.current = 'Maximilianna'; showHome('title'); });
  await chk('home-title-long', () => showHome('title'));
  await chk('home-missions-long', () => showHome('missions'));
  await p.evaluate(() => { hideHome(); Object.assign(S, fresh(), { phase: 'explore', names: true }); render(); });
  await chk('explore-empty');
  for (const id of await p.evaluate(() => ALL.map(o => o.id))) await chk('explore:' + id, id => { S.look = id; render(); }, id);
  await chk('school', () => { Object.assign(S, fresh(), { phase: 'school', lesson: '' }); render(); });
  for (const k of await p.evaluate(() => Object.keys(LESSONS))) await chk('lesson:' + k, k => { S.lesson = k; render(); }, k);
  await chk('sky', () => { Object.assign(S, fresh(), { phase: 'sky' }); render(); });
  await chk('custom', () => { Object.assign(S, fresh(), { phase: 'custom' }); render(); });
  for (const lv of [1, 2, 3, 4]) {
    await chk(`brief${lv}`, lv => { startMission(lv); hideHome(); }, lv);
    const n = await p.evaluate(() => S.queue.length);
    for (let i = 0; i < n; i++) {
      await chk(`L${lv}q${i}`, i => { S.idx = i; enterItem(); render(); }, i);
      const q = await p.evaluate(() => S.queue[S.idx].t);
      if (q !== 'lesson') {
        await chk(`L${lv}q${i}-wrong`, () => { S.misses = 2; S.feedback = 'Not quite! That one is a moon. Try looking farther from the Sun, past the asteroid belt.'; S.fbType = 'bad'; render(); });
        await chk(`L${lv}q${i}-found`, () => { const q = S.queue[S.idx]; S.answer = q.id || q.about || q.ids?.[0] || 'earth'; S.explain = 'Nice one!'; S.phase = 'found'; S.combo = 4; render(); });
      }
    }
    await chk(`L${lv}-done`, () => { S.phase = 'done'; S.stars = 2; render(); });
    await chk(`L${lv}-done-look`, () => { S.look = 'jupiter'; render(); });
  }
  await chk('speed', () => { startSpeed(); hideHome(); });
  await chk('speed-done', () => { clearInterval(window.__t); S.phase = 'done'; S.look = ''; render(); });
  await chk('passport', () => { renderPassport(); passDlg.showModal(); });
  await chk('player', () => { passDlg.close(); openPlayers(); });
  await chk('celebrate', () => { playerDlg.close(); celebrate('🏅', 'New badge: Galaxy Guide', 'You learned about every kind of star in the Milky Way.'); }, null);
  await p.waitForTimeout(700); await chk('celebrate2');
  if (errs.length) report['pageerrors ' + w] = errs;
  await p.close();
}
await b.close();
const keys = Object.keys(report);
console.log(keys.length ? keys.map(k => k + '\n  ' + report[k].slice(0, 6).join('\n  ') + (report[k].length > 6 ? `\n  …+${report[k].length - 6}` : '')).join('\n') : 'NO OVERLAPS');
