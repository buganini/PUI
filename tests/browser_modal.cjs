const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),{createRequire}=require('module');
const root=path.resolve(__dirname,'..'),build=createRequire(root+'/env/web-client/package.json');
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[root+'/browser-client/shared/dom.js'],bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await (process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require)('playwright').chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true});
 try{
  const page=await browser.newPage();await page.setContent('<main id="host"></main>');
  await page.addStyleTag({content:fs.readFileSync(root+'/browser-client/shared/client.css','utf8')});
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   window.actions=[];window.r=new PUIRenderer.Renderer(document.getElementById('host'),(kind,body)=>actions.push(body));
   window.render=(open,inner=false,remove=false,text='Content')=>{
    const n=(id,type,props={},children=[],events={},layout={})=>({id,type,props,children,events,layout,style:{},bindings:{}});
    const nested=n('inner','Modal',{title:'Inner',open:inner},[n('innerLabel','Label',{text:'Inner content',selectable:false})],{dismiss:'i'});
    const modal=n('modal','Modal',{title:'Outer',open},[n('label','Label',{text,selectable:false}),nested],{dismiss:'m'},{width:320,height:180});
    r.apply({mode:'snapshot',base_rev:null,rev:r.rev+1,processed_seq:0,roots:[n('window','Window',{title:'test'},[n('box','VBox',{},[n('outside','Button',{text:'Outside',disabled:false},[],{click:'c'}),...remove?[]:[modal]])])],bindings:[],canvases:[]});
   };
   render(false);
  });
  const outside=page.locator('[data-pui-id="outside"]'),modal=page.locator('[data-pui-id="modal"]');
  await outside.focus();await page.evaluate(()=>render(true));
  assert(await modal.evaluate(e=>e.open && e.matches(':modal')));
  const retained=await modal.evaluate(e=>{e.saved=42;return e.getBoundingClientRect().width});assert.equal(retained,320);
  await page.evaluate(()=>render(true,false,false,'Updated'));
  assert.equal(await modal.evaluate(e=>e.saved),42);
  await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>actions.at(-1).event),'dismiss');
  await page.evaluate(()=>render(false));assert.equal(await page.evaluate(()=>document.activeElement.dataset.puiId),'outside');
  await page.evaluate(()=>render(true,true));assert.equal(await page.locator('dialog:modal').count(),2);
  await page.keyboard.press('Escape');assert.equal(await page.evaluate(()=>actions.at(-1).node_id),'inner');
  await page.evaluate(()=>render(true,false));assert.equal(await page.locator('dialog:modal').count(),1);
  await page.evaluate(()=>render(false,false,true));assert.equal(await page.locator('dialog:modal').count(),0);
  console.log('Native dialog open/close, nested Escape, focus restoration, retained updates and removal passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
