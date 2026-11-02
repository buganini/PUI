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
   const button=node('button','Button',{row:0,column:1},[],{text:'Connect',disabled:false});
   const field=node('field','TextField',{row:1,column:1},[],{text:'Wide'});
   const ref={object_id:'1',kind:'attr',key:'field'};
   field.bindings.model={ref,token:'a-field',slot_token:'s-field',writable:true};
   const grid=node('grid','Grid',{width:650,height:400},[
    node('tall','Label',{width:120,height:180,row:0,column:0},[],{text:'Tall'}),button,field],{columns:null});
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[grid],{title:'Grid'})],bindings:[{ref,token:'s-field',value_rev:1,value:'Wide'}],canvases:[]});
   let rev=1;const results=[];
   for(const weight of [null,1,0]){
    if(weight!==null)r.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,ops:[{op:'patch_node',node_id:'button',field:'layout',set:{weight},unset:[]}]});
    const size=id=>{const e=r.elements.get(id),b=e.getBoundingClientRect();return [b.width,b.height];};
    results.push({weight,button:size('button'),field:size('field')});
   }
   return results;
  });
  const assert=require('node:assert/strict');
  const [compact,weighted,restored]=result;
  assert(compact.button[0]<150 && compact.button[1]<60, 'Default Button stretched');
  assert(weighted.button[0]>300 && weighted.button[1]>180, 'Weighted Button did not fill');
  assert.deepEqual(restored.button,compact.button, 'Clearing weight did not restore content size');
  for(const row of result)assert(row.field[0]>300 && row.field[1]<60, 'TextField fill changed');
  console.log('Shared Web/Pyodide compact and weighted Grid cells passed');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
