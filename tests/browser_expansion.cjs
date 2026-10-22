// Nested expansion demand shared by Web and Pyodide.
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
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   const node=(id,type,layout={},children=[],props={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
   const leaf=node('leaf','Label',{weight:9},[],{text:'weighted'});
   const inner=node('inner','HBox',{},[leaf]);
   const box=node('box','VBox',{},[node('middle','VBox',{},[inner])]);
   const plain=node('plain','VBox',{},[node('label','Label',{},[],{text:'plain'})]);
   const row=node('row','HBox',{width:800,height:200},[box,plain]);
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[row],{title:'Expansion'})],bindings:[],canvases:[]});
   const grow=id=>Number(getComputedStyle(r.elements.get(id)).flexGrow);
   const check=(condition,message)=>{if(!condition)throw Error(message);};
   check(grow('box')===1 && grow('plain')===0,'Nested child demand should win over plain VBox');
   let rev=1;
   const patch=(id,set,unset=[])=>r.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,ops:[
    {op:'patch_node',node_id:id,field:'layout',set,unset}]});
   // Removing only the weighted leaf still leaves an HBox at priority 3.
   patch('inner',{visible:false});
   check(grow('box')===1 && grow('plain')===1,'Hidden subtree should withdraw inherited demand');
   patch('inner',{visible:true});
   check(grow('plain')===0,'Showing subtree should restore inherited demand');
   patch('box',{weight:0});
   check(grow('box')===0 && grow('plain')===1,'Explicit zero weight should block demand');
   patch('box',{width:120},['weight']);
   check(grow('plain')===1,'Fixed width should block inherited promotion');
   r.destroy();
  });
  console.log('Shared browser: nested expansion, hidden subtrees, weight=0 and fixed-width boundaries passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
