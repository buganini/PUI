// Grid cell filling shared by Web and Pyodide.
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
  const result=await page.evaluate(()=>{
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   const node=(id,type,layout={},children=[],props={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
   const a=node('a','Label',{row:0,column:0,rowspan:2,height:120},[],{text:'A'});
   const b=node('b','Label',{row:0,column:1,rowspan:2,height:60,width:60},[],{text:'B'});
   const c=node('c','Label',{row:2,column:0,columnspan:2,height:180},[],{text:'C'});
   const grid=node('grid','Grid',{width:500},[a,b,c],{columns:2});
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[grid],{title:'Grid'})],bindings:[],canvases:[]});
   const rect=id=>r.elements.get(id).getBoundingClientRect();
   const filled=Math.abs(rect('a').height-rect('b').height)<1 &&
     rect('b').width>=60 && Math.abs(rect('c').right-rect('b').right)<1;
   const retained=r.elements.get('b');
   r.apply({mode:'patch',base_rev:1,rev:2,processed_seq:0,ops:[
    {op:'patch_node',node_id:'b',field:'layout',set:{rowspan:1},unset:[]}]});
   const unexpanded=rect('b').height>=60 && rect('b').height<rect('a').height;
   r.apply({mode:'patch',base_rev:2,rev:3,processed_seq:0,ops:[
    {op:'patch_node',node_id:'b',field:'layout',set:{rowspan:2},unset:[]}]});
   const expandedAgain=Math.abs(rect('a').height-rect('b').height)<1 && r.elements.get('b')===retained;
   r.destroy();
   return {filled,unexpanded,expandedAgain};
  });
  assert.deepEqual(result,{filled:true,unexpanded:true,expandedAgain:true});
  console.log('Shared browser Grid: expanded spans fill cells with explicit dimensions; toggle retains elements.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
