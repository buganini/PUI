// Native ResizeObserver measurements shared by Web and Pyodide.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const build=createRequire(path.join(root,'env/web-client/package.json'));
const modules=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[path.join(root,'browser-client/shared/dom.js')],bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await modules('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  await page.setContent('<main id="host"></main>');
  await page.addStyleTag({content:fs.readFileSync(path.join(root,'browser-client/shared/client.css'),'utf8')});
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   window.measures=[];
   window.renderer=new PUIRenderer.Renderer(document.getElementById('host'),()=>{},(type,body)=>measures.push({type,...body}));
   const node=(id,type,layout={},children=[])=>({id,type,props:type==='Window'?{title:'Adaptive'}:{},children,layout,style:{},bindings:{},events:{}});
   const box=node('box','VBox',{observe_size:true,width:800,height:300,padding:[10,20,10,20]});
   renderer.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[box])],bindings:[],canvases:[]});
  });
  await page.waitForFunction(()=>measures.length>0);
  let first=await page.evaluate(()=>measures.at(-1));
  assert.equal(first.type,'container_size');assert.equal(first.width,760);assert.equal(first.height,280);
  await page.evaluate(()=>{
   const e=renderer.elements.get('box');e.style.width='500px';e.style.minWidth='500px';
  });
  await page.waitForFunction(()=>measures.at(-1)?.width===460);
  await page.evaluate(()=>renderer.destroy());
  assert.equal(await page.evaluate(()=>renderer.sizes.size),0);
  console.log('Container content size, native resize and observer cleanup pass.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
