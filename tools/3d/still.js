const { chromium } = require('playwright'); const path=require('path');
(async()=>{const b=await chromium.launch({args:['--use-gl=swiftshader','--enable-webgl','--ignore-gpu-blocklist','--allow-file-access-from-files']});
const p=await b.newPage({viewport:{width:1080,height:1920}});await p.goto('file://'+path.resolve(__dirname,'scene.html'));
await p.waitForFunction(()=>window.ready===true);
const shots=JSON.parse(process.argv[3]);let i=0;
for(const [t,r,l,bo] of shots){await p.evaluate(a=>window.renderFrame(...a),[t,r,l,bo]);await p.screenshot({path:process.argv[2]+'_'+(i++)+'.png'});}
await b.close();})();
