import { chromium } from 'playwright';
import fs from 'fs';
const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
const errs = [];
async function page(vp) {
  const p = await b.newPage({ viewport: vp, hasTouch: vp.width < 600 });
  if (fs.existsSync('ae/package/astronomy.browser.min.js')) await p.route('**/astronomy.browser.min.js', r => r.fulfill({ body: fs.readFileSync('ae/package/astronomy.browser.min.js','utf8'), contentType: 'text/javascript' }));
  p.on('pageerror', e => errs.push(e.message)); p.on('console', m => m.type()==='error' && errs.push(m.text()));
  await p.goto('file://' + process.cwd() + '/index.html'); await p.waitForTimeout(700); return p;
}
const p = await page({width:1280,height:800});
await p.screenshot({path:'h_title.png'});
await p.evaluate(() => document.querySelector('[data-hplay]').click()); await p.waitForTimeout(300); await p.screenshot({path:'h_missions.png'});
// locked mission should not start
await p.click('[data-hlevel="3"]', {force:true}); console.log('locked stays home:', await p.evaluate(() => !home.hidden));
await p.click('[data-hlevel="1"]'); await p.waitForTimeout(300); await p.click('[data-begin]');
// answer all right first try
for (let i = 0; i < 30; i++) {
  const st = await p.evaluate(() => ({ ph: S.phase, q: S.queue[S.idx] }));
  if (st.ph === 'done') break;
  if (await p.evaluate(() => !document.querySelector('#celebrate').hidden)) { await p.click('#celOk'); continue; }
  if (st.ph === 'lesson') { await p.waitForTimeout(500); if (await p.evaluate(() => !document.querySelector('#celebrate').hidden)) { await p.click('#celOk'); continue; } await p.click('[data-next]'); continue; }
  if (st.ph === 'clue') { const q = st.q; if (q.t === 'choice') await p.evaluate(a => choose(a), q.ans); else await p.evaluate(r => onTap(r), q.t === 'find' ? q.id : q.t === 'group' ? q.ids[0] : q.ans);
    await p.waitForTimeout(120);
    if (i === 3) { await p.waitForTimeout(300); await p.screenshot({path:'h_found.png'}); }
    if (await p.evaluate(() => S.phase === 'found')) await p.evaluate(() => { S.idx++; enterItem(); render(); }); continue; }
}
await p.waitForTimeout(1800); await p.screenshot({path:'h_pop.png'});
for (let i = 0; i < 6; i++) if (await p.evaluate(() => !document.querySelector('#celebrate').hidden)) { await p.click('#celOk'); await p.waitForTimeout(300); }
await p.screenshot({path:'h_results.png'});
console.log('after L1', await p.evaluate(() => ({ xp: P.xp, done: P.done, badges: P.badges, unlocked2: unlocked(2) })));
// speed run
await p.evaluate(() => startSpeed()); await p.waitForTimeout(300);
for (let i = 0; i < 4; i++) await p.evaluate(() => onTap(S.queue[S.idx].id));
await p.evaluate(() => onTap('mars' === S.queue[S.idx].id ? 'venus' : 'mars'));
await p.screenshot({path:'h_speed.png'});
await p.evaluate(() => { S.deadline = Date.now() - 10; }); await p.waitForTimeout(600);
for (let i = 0; i < 4; i++) if (await p.evaluate(() => !document.querySelector('#celebrate').hidden)) { await p.click('#celOk'); await p.waitForTimeout(300); }
await p.screenshot({path:'h_speedend.png'});
console.log('speed', await p.evaluate(() => ({ phase: S.phase, score: S.score, best: P.bestSpeed })));
// daily twice gives same questions
const d1 = await p.evaluate(() => { startDaily(); return JSON.stringify(S.queue.map(q => q.id || q.ans || q.q)); });
const d2 = await p.evaluate(() => { startDaily(); return JSON.stringify(S.queue.map(q => q.id || q.ans || q.q)); });
console.log('daily same:', d1 === d2, d1);
await p.evaluate(() => showHome('title')); await p.waitForTimeout(300); await p.screenshot({path:'h_title2.png'});
await p.evaluate(() => { renderPassport(); passDlg.showModal(); }); await p.waitForTimeout(200); await p.screenshot({path:'h_pass.png'});
const ph = await page({width:390,height:760});
await ph.screenshot({path:'h_ptitle.png'}); await ph.evaluate(() => document.querySelector('[data-hplay]').click()); await ph.waitForTimeout(300); await ph.screenshot({path:'h_pmissions.png'});
console.log('ERR', JSON.stringify(errs));
await b.close();
