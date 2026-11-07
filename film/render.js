const {chromium}=require('playwright');
const OUT=process.argv[2], N=1500, W=4;
(async()=>{const b=await chromium.launch();
 await Promise.all([...Array(W)].map(async(_,w)=>{
  const p=await b.newPage({viewport:{width:1920,height:1080}});
  await p.goto('http://127.0.0.1:8123/film/film.html');await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(800);
  for(let f=w;f<N;f+=W){await p.evaluate(t=>window.setT(t),f/30);await p.screenshot({path:`${OUT}/f${String(f).padStart(4,'0')}.png`});}
  await p.close();}));
 await b.close();console.log('rendered',N)})();
