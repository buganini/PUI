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
  await page.evaluate(()=>{
   const check=(ok,message)=>{if(!ok)throw Error(message);};
   const node=(id,type,layout={},children=[],props={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
   const label=node('label','Label',{row:0,column:0},[],{text:'Field'});
   const value=node('value','Label',{row:0,column:1},[],{text:'Value'});
   const input=node('input','TextField',{row:0,column:2},[],{text:'input'});
   const bodyLabel=node('body-label','Label',{row:1,column:0,columnspan:2},[],{text:'Body'});
   const body=node('body','TextEdit',{row:1,column:2},[],{text:'body'});
   const footer=node('footer','Label',{row:2,column:0,columnspan:3},[],{text:'Footer'});
   const grid=node('grid','Grid',{width:700,height:400},[label,value,input,bodyLabel,body,footer],{columns:null});
   const bindings=[input,body].map(child=>{
    const ref={object_id:'1',kind:'attr',key:child.id};
    child.bindings.model={ref,token:'a-'+child.id,slot_token:'s-'+child.id,writable:true};
    return {ref,token:'s-'+child.id,value_rev:1,value:child.props.text};
   });
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[grid],{title:'Grid sizing'})],bindings,canvases:[]});
   const rect=id=>r.elements.get(id).getBoundingClientRect();
   const initial=rect('label'), editor=r.elements.get('input');
   const columns=()=>getComputedStyle(r.elements.get('grid')).gridTemplateColumns.split(' ').map(parseFloat);
   check(initial.width<100 && rect('value').width<100 && rect('input').width>400,'Static label columns expanded');
   check(rect('input').height<60 && rect('body').height>250 && rect('footer').height<40,'Wrong row expansion');
   let rev=1;
   const patch=(id,set,unset=[],field='layout')=>r.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,ops:[
    {op:'patch_node',node_id:id,field,set,unset}]});
   patch('grid',{columns:3},[],'props');
   check(rect('label').width===initial.width,'Automatic placement forced equal columns');
   patch('grid',{width:900,height:500});
   check(rect('label').width===initial.width && rect('input').width>600,'Resize changed compact columns');
   check(rect('body').height>350,'Resize did not grow the winning row');
   editor.focus();editor.value='local draft';
   editor.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText'}));
   patch('label',{weight:2});
   check(rect('label').width>500 && rect('label').height>350,'Weight did not win both axes');
   patch('label',{weight:0});
   check(rect('label').width===initial.width && rect('label').height===initial.height,'Weight removal did not restore compact tracks');
   check(r.elements.get('input')===editor && editor.value==='local draft' && document.activeElement===editor,'Lost retained editor state');
   patch('input',{visible:false});patch('body',{visible:false});
   check(rect('footer').width<150 && rect('footer').height<40,'Static Grid expanded after hiding editors');
   patch('input',{visible:true,column:1,columnspan:2});patch('value',{visible:false});
   const spanning=columns();
   check(spanning[0]<100 && spanning[1]>200 && spanning[2]>200,'Spanning editor did not promote every covered column');
   patch('input',{weight:0});
   check(rect('footer').width<400,'Zero weight did not suppress expansion');
   r.destroy();
   const nested=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   input.layout={};
   const wrapped=node('wrapped','VBox',{row:0,column:0},[input]);
   const plain=node('plain','VBox',{row:0,column:1},[node('plain-label','Label',{},[],{text:'plain'})]);
   const nestedGrid=node('nested-grid','Grid',{width:700,height:200},[wrapped,plain]);
   nested.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,
    roots:[node('window','Window',{},[nestedGrid],{title:'Nested Grid'})],bindings:[bindings[0]],canvases:[]});
   const width=id=>nested.elements.get(id).getBoundingClientRect().width;
   check(width('wrapped')>500 && width('plain')<100,'Nested editor demand did not promote its column');
   nested.apply({mode:'patch',base_rev:1,rev:2,processed_seq:0,ops:[
    {op:'patch_node',node_id:'input',field:'layout',set:{visible:false},unset:[]}]});
   check(Math.abs(width('wrapped')-width('plain'))<1,'Hidden descendant did not withdraw column demand');
   nested.destroy();
  });
  console.log('Shared browser Grid: compact tracks, both axes, weights, spans, visibility, resize and retained editor passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
