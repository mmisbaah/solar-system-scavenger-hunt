import { chromium } from 'playwright';
const b = await chromium.launch(process.env.CHROMIUM ? { executablePath: process.env.CHROMIUM } : {});
for (const [w,h] of [[1280,800],[1366,640],[1024,768],[768,1024],[390,760],[375,667],[360,600]]) {
  const p = await b.newPage({ viewport: {width:w,height:h} });
  await p.goto('file://' + process.cwd() + '/index.html'); await p.waitForTimeout(500);
  const t = await p.evaluate(() => { const h = document.querySelector('#home'), i = document.querySelector('#homeBody'); return [h.scrollHeight, h.clientHeight, i.scrollHeight, i.clientHeight]; });
  await p.screenshot({path:`fit_${w}x${h}_t.png`});
  await p.click('[data-hplay]', {force:true}); await p.waitForTimeout(200);
  const m = await p.evaluate(() => { const h = document.querySelector('#home'), i = document.querySelector('#homeBody'); return [h.scrollHeight, h.clientHeight, i.scrollHeight, i.clientHeight]; });
  await p.screenshot({path:`fit_${w}x${h}_m.png`});
  console.log(w+'x'+h, 'title', t.join('/'), 'missions', m.join('/'));
  await p.close();
}
await b.close();
