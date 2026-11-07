const {chromium}=require('playwright');
const CARDS={title:6,brand:10,rooms:28,flow:28,end:10}, W=4, OUT=process.argv[2];
const fs=require('fs');
(async()=>{const b=await chromium.launch();
 const ONLY=process.argv[3]?process.argv[3].split(','):null;
 for(const [card,secs] of Object.entries(CARDS)){if(ONLY&&!ONLY.includes(card))continue;fs.mkdirSync(`${OUT}/${card}`,{recursive:true});const N=secs*30;
  await Promise.all([...Array(W)].map(async(_,w)=>{const p=await b.newPage({viewport:{width:1920,height:1080}});
   await p.goto(`http://127.0.0.1:8123/demo-video/cards.html?card=${card}`);await p.evaluate(()=>document.fonts.ready);await p.waitForTimeout(600);
   for(let f=w;f<N;f+=W){await p.evaluate(t=>window.setT(t),f/30);await p.screenshot({path:`${OUT}/${card}/f${String(f).padStart(4,'0')}.png`})}await p.close()}));
  console.log('done',card)}
 await b.close()})();
