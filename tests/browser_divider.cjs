// Divider orientation shared by Web and Pyodide.
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
   const line=node('line','Divider');
   const box=node('box','VBox',{width:400,height:200},[node('label','Label',{},[],{text:'Text'}),line],{direction:'column'});
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[box],{title:'Divider'})],bindings:[],canvases:[]});
   const retained=r.elements.get('line');
   let rev=1;
   for(const direction of ['column','row','column','row']) {
    r.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,ops:[
     {op:'patch_node',node_id:'box',field:'props',set:{direction},unset:[]}]});
    const rect=retained.getBoundingClientRect(),vertical=direction==='row';
    if(vertical ? !(rect.width===1 && rect.height===200) : !(rect.height===1 && rect.width===400))
     throw Error(`Wrong ${direction} divider geometry: ${rect.width} x ${rect.height}`);
    if(retained!==r.elements.get('line') || retained.getAttribute('aria-orientation')!==(vertical?'vertical':'horizontal'))
     throw Error('Divider identity/orientation mismatch');
   }
   r.destroy();
  });
  console.log('Shared browser Divider: horizontal/vertical geometry and retained direction changes passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
