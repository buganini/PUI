// Shared Web/Pyodide renderer: hiding retains DOM, collapses space, and respects Views.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const build=createRequire(path.join(root,'env/web-client/package.json'));
const browserModules=process.env.PUI_BROWSER_MODULES
  ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[path.join(root,'browser-client/shared/dom.js')],
  bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await browserModules('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  await page.setContent('<main id="host"></main>');
  await page.addStyleTag({content:fs.readFileSync(path.join(root,'browser-client/shared/client.css'),'utf8')});
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  const result=await page.evaluate(()=>{
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   const node=(id,type,props={},children=[])=>({id,type,props,children,layout:{},style:{},bindings:{},events:{}});
   const input=node('input','TextField',{text:'original',placeholder:''});
   const ref={object_id:'12345',kind:'attr',key:'value'};
   const slot={ref,token:'slot',value_rev:1,value:'original'};
   input.bindings.model={ref,token:'attachment',slot_token:'slot',writable:true};
   input.events.input='input-event';
   const other=node('other','Label',{text:'Other',selectable:false});
   const views=node('views','Views',{selected:'input'},[input,other]);
   const window=node('window','Window',{title:'Visibility'},[views]);
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[window],bindings:[slot],canvases:[]});
   const native=r.elements.get('input');native.value='draft';native.dispatchEvent(new InputEvent('input',{bubbles:true}));
   const patch=(id,field,set,unset=[])=>r.apply({mode:'patch',base_rev:r.rev,rev:r.rev+1,processed_seq:0,
     ops:[{op:'patch_node',node_id:id,field,set,unset}]});
   patch('input','layout',{visible:false});
   const hidden=native.getClientRects().length===0 && r.elements.get('other').hidden;
   patch('input','layout',{},['visible']);
   const restored=r.elements.get('input')===native && native.value==='draft' && native.getClientRects().length>0;
   patch('views','props',{selected:'other'});
   patch('input','layout',{visible:true});
   const selection=native.hidden && !r.elements.get('other').hidden;
   patch('views','layout',{visible:false});
   const container=r.elements.get('views').getClientRects().length===0;
   r.destroy();return {hidden,restored,selection,container};
  });
  assert.deepEqual(result,{hidden:true,restored:true,selection:true,container:true});
  console.log('Visibility preserves DOM/drafts, collapses layout and respects page selection.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
