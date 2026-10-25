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
   const plainContent=width('plain-label');
   check(Math.abs(width('plain')-width('wrapped')-plainContent)<1,
     'Equal-priority columns did not share extra space after accounting for content');
   nested.destroy();

   // A Grid competing with an outer Spacer must keep its intrinsic width.
   // Several HBox cells have equal priority, and one crosses two columns.
   // 1fr tracks incorrectly enlarge the short tools column in this case.
   const compact=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   const tools=node('tools','HBox',{row:0,column:1},[
    node('up','Button',{},[],{text:'↑'}),node('down','Button',{},[],{text:'↓'}),
    node('remove','Button',{},[],{text:'×'})]);
   input.layout={weight:1};
   const details=node('details','HBox',{row:0,column:2},[
    node('note','Label',{},[],{text:'Note:'}),input]);
   const outputs=node('outputs','HBox',{row:1,column:2,columnspan:2},[
    node('output-label','Label',{},[],{text:'Output settings for the selected item'}),
    node('output-button','Button',{},[],{text:'Configure'})]);
   const compactGrid=node('compact-grid','Grid',{},[
    node('number','Label',{row:0,column:0},[],{text:'1.'}),tools,details,outputs]);
   const outer=node('outer','HBox',{width:900,height:180},[
    compactGrid,node('outer-space','Spacer',{weight:1})]);
   compact.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,
    roots:[node('window','Window',{},[outer],{title:'Compact nested Grid'})],bindings:[bindings[0]],canvases:[]});
   const bounds=id=>compact.elements.get(id).getBoundingClientRect();
   const trackSizes=()=>getComputedStyle(compact.elements.get('compact-grid')).gridTemplateColumns.split(' ').map(parseFloat);
   const natural=trackSizes(), gridWidth=bounds('compact-grid').width, space=bounds('outer-space').width;
   const toolsWidth=bounds('up').width+bounds('down').width+bounds('remove').width+16;
   check(Math.abs(bounds('tools').width-toolsWidth)<1,'Intrinsic Grid widened the tools column');
   check(space>100,'Intrinsic Grid consumed the outer Spacer');
   check(bounds('outputs').width>=bounds('output-label').width+bounds('output-button').width+8,
     'Spanning content did not fit its natural tracks');
   let compactRev=1;
   const compactPatch=(id,set,unset=[],field='layout')=>compact.apply({mode:'patch',base_rev:compactRev,rev:++compactRev,processed_seq:0,
    ops:[{op:'patch_node',node_id:id,field,set,unset}]});
   compactPatch('outer',{width:1100});
   check(Math.abs(bounds('compact-grid').width-gridWidth)<1 && Math.abs(bounds('outer-space').width-space-200)<1,
     'Resize distributed outer extra space to the compact Grid');
   compact.elements.get('outer').style.width='1200px';
   check(Math.abs(bounds('compact-grid').width-gridWidth)<1 && Math.abs(bounds('outer-space').width-space-300)<1,
     'Container resize without a render patch changed intrinsic Grid width');
   compact.elements.get('outer').style.width='1100px';
   compactPatch('outer-space',{visible:false});
   const expanded=trackSizes(), added=expanded.map((v,i)=>v-natural[i]);
   check(Math.abs(added[0])<1 && added[1]>0 && Math.abs(added[1]-added[2])<1 && Math.abs(added[2]-added[3])<1,
     'Equal-priority tracks did not share only the extra space, including the span');
   compactPatch('outer-space',{visible:true});
   check(Math.abs(bounds('tools').width-toolsWidth)<1,'Restoring Spacer did not restore intrinsic column widths');
   compactPatch('note',{text:'A considerably longer annotation for the selected item:'},[],'props');
   check(bounds('compact-grid').width>gridWidth && Math.abs(bounds('tools').width-toolsWidth)<1,
     'Content update widened unrelated equal-priority column');
   compact.destroy();
   const rows=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   rows.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,
    roots:[node('window','Window',{},[node('rows','Grid',{width:300,height:200},[
     node('short','Label',{row:0,column:0,height:20,weight:1},[],{text:'Short'}),
     node('tall','Label',{row:1,column:0,height:60,weight:1},[],{text:'Tall'})])],{title:'Row sizing'})],bindings:[],canvases:[]});
   const rowHeight=id=>rows.elements.get(id).getBoundingClientRect().height;
   check(rowHeight('short')>20 && Math.abs(rowHeight('tall')-rowHeight('short')-40)<1,
     'Equal-weight rows did not retain individual size requirements before sharing extra height');
   rows.destroy();
   // Real forms mix compact label columns and an editor with full-width
   // toolbars/nested sections farther down the same Grid. Their intrinsic
   // widths must be satisfied by the editor column, not the label columns.
   const form=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   input.layout={row:1,column:2};
   const formGrid=node('form-grid','Grid',{width:1000},[
    node('action-label','Label',{row:0,column:0},[],{text:'Action'}),
    node('toolbar','HBox',{row:0,column:1,columnspan:3},[
     node('action','Button',{},[],{text:'Run'}),node('action-space','Spacer',{weight:1})]),
    node('field-label','Label',{row:1,column:0},[],{text:'Field name'}),
    node('field-value','Label',{row:1,column:1},[],{text:'Value'}),input,
    node('wide-section','HBox',{row:2,column:0,columnspan:3},[
     node('wide-content','VBox',{width:700},[node('section-label','Label',{},[],{text:'Nested section'})]),
     node('section-space','Spacer',{weight:1})])]);
   form.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,
    roots:[node('window','Window',{},[formGrid],{title:'Spanning form sections'})],bindings:[bindings[0]],canvases:[]});
   const formWidth=id=>form.elements.get(id).getBoundingClientRect().width;
   const labelWidth=formWidth('field-label'),valueWidth=formWidth('field-value');
   check(labelWidth<100 && valueWidth<100 && formWidth('input')>750,
     'Spanning section widened lower-priority label columns: '+JSON.stringify([labelWidth,valueWidth,formWidth('input'),getComputedStyle(form.elements.get('form-grid')).gridTemplateColumns]));
   form.apply({mode:'patch',base_rev:1,rev:2,processed_seq:0,ops:[
    {op:'patch_node',node_id:'form-grid',field:'layout',set:{width:1200},unset:[]},
    {op:'patch_node',node_id:'wide-content',field:'layout',set:{width:900},unset:[]}]});
   check(formWidth('field-label')===labelWidth && formWidth('field-value')===valueWidth && formWidth('input')>950,
     'Resizing spanning content changed lower-priority column widths');
   form.destroy();
  });
  console.log('Shared browser Grid: compact tracks, both axes, weights, spans, visibility, resize and retained editor passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
