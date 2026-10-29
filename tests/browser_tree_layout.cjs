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
   const check=(condition,message)=>{if(!condition)throw Error(message);};
   const node=(id,type,layout={},children=[],props={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
   for(const container of ['HBox','VBox','nested'])for(const sizing of ['auto','minimum','fixed']) {
    const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
    const layout=sizing==='fixed'?{width:120,height:80}:sizing==='minimum'?{weight:1,minWidth:120,minHeight:80}:{weight:1};
    const tree=node('tree','Tree',layout,[],{nodes:[{id:1,parent:0,text:'Branch'}],expanded:[],selected:null,expandable:true});
    tree.events.tree='tree-event';
    const children=container==='nested'?[node('inner','HBox',{},[tree])]:[tree];
    const box=node('box',container==='nested'?'VBox':container,{width:800,height:400},children);
    r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[box],{title:'Tree sizing'})],bindings:[],canvases:[]});
    const rect=r.elements.get('tree').getBoundingClientRect();
    const arrow=r.elements.get('tree').querySelector('.pui-tree-arrow').getBoundingClientRect();
    check(arrow.width>=32 && arrow.height>=32,'Tree arrow hit target is too small');
    if(sizing==='fixed')check(Math.abs(rect.width-120)<1 && Math.abs(rect.height-80)<1,container+' fixed Tree should keep desired size');
    else check(rect.width>=799 && rect.height>=399,container+' '+sizing+' Tree should fill both axes: '+rect.width+'x'+rect.height);
    r.destroy();
   }
  });
  console.log('Tree fills HBox/VBox/nested layouts on both axes; desired sizes stop expansion and minimums do not.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
