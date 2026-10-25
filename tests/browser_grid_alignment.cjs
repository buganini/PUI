// Center label text in filled Grid cells, without changing cell/span geometry.
const path=require('node:path');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const build=createRequire(path.join(root,'env/web-client/package.json'));
const modules=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[path.join(root,'browser-client/shared/dom.js')],bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await modules('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true});
 try {
  const page=await browser.newPage();
  await page.setContent('<main id="host"></main>');
  await page.addStyleTag({content:fs.readFileSync(path.join(root,'browser-client/shared/client.css'),'utf8')});
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   const check=(ok,message)=>{if(!ok)throw Error(message);};
   const node=(id,type,layout={},children=[],props={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
   const label=node('label','Label',{row:0,column:0},[],{text:'Field',selectable:true});
   const field=node('field','TextField',{row:0,column:1},[],{text:'Value'});
   const ref={object_id:'1',kind:'attr',key:'text'};
   field.bindings.model={ref,token:'attachment',slot_token:'slot',writable:true};
   const multiple=node('multiple','Label',{row:1,column:0},[],{text:'First line\nSecond line'});
   const tall=node('tall','Button',{row:1,column:1,height:90},[],{text:'Tall control'});
   const span=node('span','Label',{row:0,column:2,rowspan:2},[],{text:'Spanning'});
   const grid=node('grid','Grid',{width:700},[label,field,multiple,tall,span]);
   const box=node('box','VBox',{},[]);
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[grid,box],{title:'Alignment'})],bindings:[{ref,token:'slot',value_rev:1,value:'Value'}],canvases:[]});
   const rect=id=>r.elements.get(id).getBoundingClientRect();
   const textRect=id=>{const range=document.createRange();range.selectNodeContents(r.elements.get(id));return range.getBoundingClientRect();};
   const center=rect=>rect.y+rect.height/2;
   const centered=id=>Math.abs(center(rect(id))-center(textRect(id)))<2;
   check(centered('label') && Math.abs(center(textRect('label'))-center(rect('field')))<2,'Label and input do not share a center line');
   check(centered('multiple') && centered('span'),'Multiline/spanning label is not centered within its cell');
   check(rect('span').height===rect('tall').bottom-rect('label').top,'Spanning label stopped filling its cell');
   check(Math.abs(textRect('label').left-rect('label').left)<1,'Label text is no longer left-aligned');
   check(getComputedStyle(r.elements.get('label')).userSelect==='text','Selectable label changed');
   const retained=r.elements.get('label');
   r.apply({mode:'patch',base_rev:1,rev:2,processed_seq:0,ops:[
    {op:'patch_node',node_id:'field',field:'layout',set:{height:65},unset:[]}]});
   check(r.elements.get('label')===retained && centered('label'),'Resize lost retained label alignment');
   r.apply({mode:'patch',base_rev:2,rev:3,processed_seq:0,ops:[
    {op:'patch_node',node_id:'label',field:'layout',set:{},unset:['row','column']},
    {op:'place_node',node_id:'label',parent_id:'box',before_id:null}]});
   check(getComputedStyle(retained).display!=='flex','Grid alignment leaked after reparenting');
   r.destroy();
  });
  console.log('Grid alignment: label/input center lines, multiline labels, spans, resize, selection and reparenting passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
