import { chromium } from 'playwright';
const file = process.argv[2] || 'index.html';
const sizes = [[1340,826],[1340,480],[1024,768],[768,1024],[390,760],[360,600]];
const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const CHECK = () => {
  const ts = [...document.querySelectorAll('#sky text')].filter(t => t.getAttribute('visibility') !== 'hidden' && t.checkVisibility({visibilityProperty: true}) && t.getBBox().width);
  const sb = document.querySelector('#sky').getBoundingClientRect();
  const R = ts.map(t => { const r = t.getBoundingClientRect(); const h = r.height * .7, m = (r.top + r.bottom) / 2; return { t: t.textContent, l: r.left, r: r.right, top: m - h / 2, bot: m + h / 2 }; })
    .filter(r => r.r > sb.left && r.l < sb.right && r.bot > sb.top && r.top < sb.bottom);
  const out = [];
  for (let i = 0; i < R.length; i++) for (let j = i + 1; j < R.length; j++) {
    const a = R[i], c = R[j], ox = Math.min(a.r, c.r) - Math.max(a.l, c.l), oy = Math.min(a.bot, c.bot) - Math.max(a.top, c.top);
    if (ox > 2 && oy > 2) out.push(`"${a.t}" x "${c.t}"`);
  }
  return out;
};
const rep = {}; let n = 0;
for (const [w, h] of sizes) {
  const p = await b.newPage({ viewport: { width: w, height: h } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + process.cwd() + '/' + file); await p.waitForTimeout(600);
  await p.evaluate(() => { hideHome(); Object.assign(S, fresh(), { phase: 'explore', names: true }); render(); });
  const views = [];
  for (const sc of ['galaxy', 'solar']) for (const zw of [1000, 880, 600, 400, 250, 160, 100, 85, 60, 40, 25, 15])
    for (const target of sc === 'galaxy' ? ['center', 'sunhome', 'sgra', 'crab', 'lmc'] : ['center', 'earth', 'jupiter', 'saturn', 'pluto'])
      for (const real of sc === 'solar' ? [0, 1] : [0]) views.push({ sc, zw, target, real });
  for (const v of views) {
    await p.evaluate(v => {
      setScene(v.sc); if (v.sc === 'solar') { realT = v.real; }
      const o = v.target === 'center' ? { x: 0, y: 0 } : byId[v.target];
      redraw(); view = { cx: o.x, cy: o.y, w: v.zw }; clampView(); redraw(); redraw();
    }, v);
    n++;
    for (const o of await p.evaluate(CHECK)) (rep[`${w}x${h} ${v.sc} w${v.zw} @${v.target}${v.real ? ' real' : ''}`] ??= []).push(o);
  }
  if (errs.length) rep[`${w}x${h} ERR`] = errs;
  await p.close();
}
await b.close();
const k = Object.keys(rep);
console.log(n, 'views;', k.length, 'with overlaps');
k.slice(0, 40).forEach(x => console.log(x, '::', rep[x].slice(0, 4).join(' | ')));
