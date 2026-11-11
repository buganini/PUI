// Column/row priorities shared by Web and Pyodide, including retained patches.
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
  const result=await page.evaluate(()=>{
   const node=(id,type,layout={},children=[],props={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
   const children=[node('a','Label',{width:40,height:20},[],{text:'A'}),
     node('hidden','Label',{visible:false,width:40,height:20},[],{text:'Hidden'}),
     node('b','Label',{width:40,height:20},[],{text:'B'})];
   const grid=node('grid','Grid',{gap:[9,13]},[
     node('c','Label',{width:40,height:20,row:0,column:0},[],{text:'C'}),
     node('d','Label',{width:40,height:20,row:0,column:1},[],{text:'D'}),
     node('e','Label',{width:80,height:20,row:1,column:0,columnspan:2},[],{text:'Span'})]);
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[
     node('box','HBox',{gap:12},children),grid])],bindings:[],canvases:[]});
   const rect=id=>r.elements.get(id).getBoundingClientRect();
   const initial=[rect('b').left-rect('a').right,rect('d').left-rect('c').right,rect('e').top-rect('c').bottom];
   r.apply({mode:'patch',base_rev:1,rev:2,processed_seq:0,ops:[
     {op:'patch_node',node_id:'box',field:'layout',set:{gap:0},unset:[]},
     {op:'patch_node',node_id:'grid',field:'layout',set:{gap:[0,0]},unset:[]} ]});
   return {initial,updated:[rect('b').left-rect('a').right,rect('d').left-rect('c').right,rect('e').top-rect('c').bottom]};
  });
  const assert=require('node:assert/strict');
  assert.deepEqual(result.initial,[12,13,9]);
  assert.deepEqual(result.updated,[0,0,0]);
  console.log('Shared Web/Pyodide gaps and retained zero reset passed');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
