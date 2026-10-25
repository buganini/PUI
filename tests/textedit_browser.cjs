// Real Chromium textarea checks against the shared Web/Pyodide renderer.
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
  for(const buffered of [false,true]){
   const page=await browser.newPage(), errors=[];
   page.on('pageerror', error=>errors.push(error.message));
   await page.setContent('<main id="host"></main>');
   await page.addStyleTag({content:fs.readFileSync(path.join(root,'browser-client/shared/client.css'),'utf8')});
   await page.addScriptTag({content:bundle.outputFiles[0].text});
   await page.evaluate(buffered=>{
    window.actions=[];let seq=1,rev=0;
    const r=window.renderer=new PUIRenderer.Renderer(document.getElementById('host'),(kind,body,onSent)=>{actions.push({kind,body});onSent?.(seq++);});
    const ref={object_id:'1',kind:'attr',key:'text'};
    const slot={ref,token:'slot',value_rev:1,value:''};
    const draft={ref:{...ref,key:'draft'},token:'draft-slot',value_rev:1,value:''};
    const attachment=s=>({ref:s.ref,token:s.token+'-attachment',slot_token:s.token,writable:true});
    const node=(id,type,props,children=[])=>({id,type,props,children,layout:{},style:{},bindings:{},events:{}});
    const editor=node('edit','TextEdit',{text:'',placeholder:'Multiline hint',readonly:false,wrap:true});
    editor.bindings.model=attachment(slot);editor.events.input='input';
    if(buffered)editor.bindings.edit_model=attachment(draft);
    const other=node('other','Button',{text:'Other',disabled:false});
    const parent=node('root','Window',{title:'TextEdit'},[editor,other]);
    window.redraw=(props={})=>{
     Object.assign(editor.props,props);
     if(Object.hasOwn(props,'text')){slot.value=props.text;slot.value_rev++;}
     r.apply({mode:'snapshot',base_rev:null,rev:++rev,processed_seq:seq-1,roots:[structuredClone(parent)],bindings:[slot,...(buffered?[draft]:[])].map(x=>structuredClone(x)),canvases:[]});
    };
    redraw();
    window.original=r.elements.get('edit');
   }, buffered);
   const editor=page.locator('textarea');
   assert.equal(await editor.getAttribute('placeholder'),'Multiline hint');
   await editor.fill('first');await editor.press('End');await editor.press('Enter');await editor.press('b');
   assert.equal(await editor.inputValue(),'first\nb');
   assert.equal(await page.evaluate(()=>actions.some(a=>a.body.phase==='commit')),false);
   assert.equal(await editor.evaluate(e=>document.activeElement===e),true);
   await page.evaluate(()=>{original.setSelectionRange(1,4);redraw({placeholder:'Updated',wrap:false});});
   assert.equal(await editor.evaluate(e=>e===original && e.selectionStart===1 && e.selectionEnd===4),true);
   assert.equal(await editor.getAttribute('wrap'),'off');
   await page.evaluate(()=>redraw({text:'server change'}));
   assert.equal(await editor.inputValue(),'first\nb');
   await editor.press('Tab');
   assert.equal(await page.evaluate(()=>actions.filter(a=>a.body.phase==='commit').length),1);
   assert.equal(await page.evaluate(()=>actions.at(-1).body.value),'first\nb');
   await page.evaluate(()=>redraw({text:'confirmed'}));
   assert.equal(await editor.inputValue(),'confirmed');
   await editor.focus();
   await page.evaluate(()=>{
    window.beforeIME=actions.length;
    original.dispatchEvent(new CompositionEvent('compositionstart'));
    original.value='中文\n';
    original.dispatchEvent(new InputEvent('input',{bubbles:true,isComposing:true}));
    original.blur();
   });
   assert.equal(await page.evaluate(()=>actions.length===beforeIME),true);
   await page.evaluate(()=>original.dispatchEvent(new CompositionEvent('compositionend',{data:'中文'})));
   assert.equal(await page.evaluate(()=>actions.length===beforeIME+2),true);
   await page.evaluate(()=>redraw({readonly:true,text:'read only'}));
   const count=await page.evaluate(()=>actions.length);
   await editor.focus();await editor.press('x');
   assert.equal(await editor.inputValue(),'read only');
   await page.evaluate(()=>{original.select();original.dispatchEvent(new InputEvent('input',{bubbles:true}));original.blur();});
   assert.equal(await page.evaluate(()=>actions.length),count);
   assert.equal(await editor.evaluate(e=>e.selectionEnd-e.selectionStart),9);
   await page.evaluate(()=>redraw({text:'programmatic'}));
   assert.equal(await editor.inputValue(),'programmatic');
   assert.equal(await page.evaluate(()=>actions.length),count);
   assert.deepEqual(errors,[]);
   await page.close();
  }
  console.log('TextEdit: Enter/newlines, drafts, blur, IME, retained selection, readonly and silent updates passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
