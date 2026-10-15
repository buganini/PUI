const login=require('./web_login.cjs');
// Real DOM tests for local drafts, keyed focus and partial-application recovery.
const assert=require('node:assert/strict');
const path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');

(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(), errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
  await page.getByText('Row 1',{exact:true}).waitFor();
  for(const fieldType of ['TextField','MaskedField']) {
  const checks=await page.evaluate(async fieldType=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const host=document.createElement('section');document.body.append(host);
   const actions=[];let sequence=10;
   const r=new Renderer(host,(type,body,onSent)=>{actions.push({type,body});onSent?.(sequence++);});
   const check=(condition,message)=>{if(!condition)throw new Error(message);};
   const ref={object_id:'12345',kind:'attr',key:'value'};
   const slot={ref,token:'s1',value_rev:1,value:'initial'};
   const attachment={ref,token:'a1',slot_token:'s1',writable:true};
   const node=(id,type,props={},children=[])=>({id,type,props,children,layout:{},style:{},bindings:{},events:{}});
   const editor=node('input',fieldType,{text:'initial',placeholder:''});
   editor.bindings.model=attachment;editor.events.input='input-event';
   const label=node('label','Label',{text:'initial',selectable:false});
   const button=node('button','Button',{text:'button',enabled:true});
   const left=node('left','VBox',{},[editor,label,button]), right=node('right','VBox');
   const root=node('window','Window',{title:'DOM tests'},[left,right]);
   const snapshot=rev=>({mode:'snapshot',base_rev:null,rev,processed_seq:1,
    roots:[structuredClone(root)],bindings:[structuredClone(slot)],canvases:[]});
   const patch=ops=>({mode:'patch',base_rev:r.rev,rev:r.rev+1,processed_seq:1,ops});
   const set=(id,props)=>({op:'patch_node',node_id:id,field:'props',set:props,unset:[]});
   const inputEvent=e=>e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText'}));
   r.apply(snapshot(1));
   check(document.title==='DOM tests','Window title was not applied');
   r.apply(patch([set('window',{title:''})]));
   check(document.title==='','Explicit empty Window title was replaced by a fallback');
   r.apply(patch([set('window',{title:'Updated title'})]));
   check(document.title==='Updated title','Updated Window title was not applied');
   const input=r.elements.get('input');
   check(input.type===(fieldType==='MaskedField'?'password':'text'),'Wrong native input type');input.focus();input.value='draft';inputEvent(input);
   input.setSelectionRange(2,4);
   const sent=actions.length;
   r.apply(patch([{op:'place_node',node_id:'input',parent_id:'right',before_id:null}]));
   check(r.elements.get('input')===input && input.parentElement===r.elements.get('right'),'Move replaced input');
   check(document.activeElement===input && input.selectionStart===2 && input.selectionEnd===4,'Move lost focus/selection');
   check(actions.length===sent,'Programmatic move emitted an input/commit');
   r.apply(patch([set('input',{text:'server update'}),{op:'put_binding',slot:{...slot,value:'server update',value_rev:2}}]));
   check(input.value==='draft','Server update overwrote local draft');
   input.blur();
   check(actions.at(-1).type==='binding_write' && actions.at(-1).body.value==='draft','Blur did not commit');
   input.focus();input.value='newer draft';inputEvent(input);
   const oldCommit=patch([set('input',{text:'DRAFT'}),{op:'put_binding',slot:{...slot,value:'DRAFT',value_rev:3}}]);
   oldCommit.processed_seq=10;r.apply(oldCommit);
   check(input.value==='newer draft','Old commit response overwrote newer typing');
   input.blur();
   const normalized=patch([set('input',{text:'NEWER DRAFT'}),{op:'put_binding',slot:{...slot,value:'NEWER DRAFT',value_rev:4}}]);
   normalized.processed_seq=11;r.apply(normalized);
   check(input.value==='NEWER DRAFT','Commit confirmation did not normalize draft');

   input.focus();const beforeComposition=actions.length;
   input.dispatchEvent(new CompositionEvent('compositionstart',{data:''}));
   input.value='中';inputEvent(input);input.blur();
   check(actions.length===beforeComposition,'Composition was sent/committed before completion');
   input.dispatchEvent(new CompositionEvent('compositionend',{data:'中'}));
   check(actions.length===beforeComposition+2 && actions.at(-2).type==='event' &&
    actions.at(-1).type==='binding_write' && actions.at(-1).body.value==='中','Composition end after blur lost ordering');
   const committed=patch([set('input',{text:'中'}),{op:'put_binding',slot:{...slot,value:'中',value_rev:5}}]);
   committed.processed_seq=12;r.apply(committed);

   input.focus();input.value='surviving draft';inputEvent(input);
   const beforeFailure=actions.length, previousRev=r.rev, previousState=r.state;
   const extra=node('partial','Label',{text:'partially inserted',selectable:false});
   const inputDescriptor=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');
   // Fail after real DOM mutations, during final editor readback. Public DOM
   // setters are restored immediately; this hook exists only in this test.
   Object.defineProperty(input,'value',{configurable:true,get(){return inputDescriptor.get.call(this);},
    set(){throw new Error('Injected readback failure');}});
   r.draft('input').editing=false;
   try {
    let failed=false;
    try {r.apply(patch([{op:'create_node',node:extra},
     {op:'place_node',node_id:'partial',parent_id:'left',before_id:null},
     set('label',{text:'partial update'}),set('input',{text:'changed'})]));}catch{failed=true;}
    check(failed && host.textContent.includes('partially inserted'),'Failure did not occur after DOM mutation');
    check(r.rev===previousRev && r.state===previousState,'Failed render promoted canonical state/revision');
   } finally {delete input.value;}
   r.draft('input').editing=true;r.dirty=true;
   const recovery=snapshot(previousRev+2);r.apply(recovery);
   check(!host.textContent.includes('partially inserted') && r.elements.get('label').textContent==='initial','Snapshot did not repair partial DOM');
   check(r.elements.get('input')===input && input.value==='surviving draft','Recovery lost surviving input/draft');
   check(actions.length===beforeFailure,'Recovery emitted application actions');
   const replacement=snapshot(r.rev+1);
   replacement.bindings[0]={...slot,token:'s2',ref:{...ref,object_id:'67890'},value:'replacement'};
   const replacementEditor=replacement.roots[0].children[0].children[0];
   replacementEditor.bindings.model={...attachment,ref:replacement.bindings[0].ref,slot_token:'s2',token:'a2'};
   replacementEditor.props.text='replacement';
   r.apply(replacement);
   check(input.value==='replacement','Rebinding retained an invalid old draft');
   // Native sizing and property removal must work on retained DOM elements.
   host.style.cssText='position:fixed;inset:0;width:600px;height:320px;display:flex;';
   const row=node('row','HBox',{},[replacementEditor,button,label]);row.layout.height=120;
   const sizing=snapshot(r.rev+1);sizing.roots[0].children=[row];sizing.bindings=replacement.bindings;
   button.events.click='button-click';label.events.click='label-click';
   r.apply(sizing);
   const field=r.elements.get('input'), nativeHeight=field.getBoundingClientRect().height;
   check(nativeHeight<60 && field.getBoundingClientRect().width>100,'HBox stretched editor height or lost horizontal expansion');
   const centered=()=>{
    const a=field.getBoundingClientRect(),b=r.elements.get('row').getBoundingClientRect();
    check(Math.abs(a.y+a.height/2-b.y-b.height/2)<1,'HBox editor is not vertically centered');
   };
   centered();
   const font=getComputedStyle(field).fontSize;
   r.apply(patch([{op:'patch_node',node_id:'input',field:'style',
    set:{color:'#ff0000',background:'#112233',font_size_pt:20,font_weight:'bold',font_family:'monospace'},unset:[]},
    {op:'patch_node',node_id:'input',field:'layout',set:{width:180,height:48,padding:[2,3,4,5],margin:[1,2,3,4]},unset:[]},
    set('input',{placeholder:'Hint'})]));
   check(getComputedStyle(field).color==='rgb(255, 0, 0)' && parseFloat(getComputedStyle(field).fontSize)>20,'Editor style was not applied');
   check(field.getBoundingClientRect().height===48 && field.placeholder==='Hint','Explicit height/placeholder was not applied');
   r.apply(patch([{op:'patch_node',node_id:'input',field:'style',set:{},
    unset:['color','background','font_size_pt','font_weight','font_family']},
    {op:'patch_node',node_id:'input',field:'layout',set:{},unset:['width','height','padding','margin']},
    set('input',{placeholder:''})]));
   check(field===r.elements.get('input') && getComputedStyle(field).fontSize===font &&
    field.getBoundingClientRect().height===nativeHeight && field.placeholder==='','Style/layout reset left stale values');
   const buttonElement=r.elements.get('button'), beforeDisabled=actions.length;
   r.apply(patch([set('button',{enabled:false})]));buttonElement.click();
   check(buttonElement.disabled && actions.length===beforeDisabled,'Disabled button emitted an action');
   r.apply(patch([set('button',{enabled:true})]));buttonElement.click();
   check(actions.length===beforeDisabled+1,'Re-enabled button did not activate');
   const labelElement=r.elements.get('label');
   check(labelElement.getAttribute('role')==='button' && labelElement.tabIndex===0,'Clickable label lacks keyboard semantics');
   r.apply(patch([{op:'patch_node',node_id:'label',field:'events',set:{},unset:['click']}]));
   check(!labelElement.hasAttribute('role') && labelElement.tabIndex===-1,'Removed click handler left keyboard semantics');
   for(const [kind,key] of [['list',-1],['dict',1],['dict','1']]) {
    const mapped=snapshot(r.rev+1), ref={object_id:'12345',kind,key};
    mapped.bindings[0]={...slot,ref,token:'mapped-slot'+mapped.rev};
    mapped.roots[0].children[0].children[0].bindings.model={...attachment,ref,slot_token:mapped.bindings[0].token,token:'mapped-attachment'+mapped.rev};
    r.apply(mapped);
    const e=r.elements.get('input');e.focus();e.value='mapped draft';inputEvent(e);e.blur();
    check(actions.at(-1).body.ref.kind===kind && actions.at(-1).body.ref.key===key,'Binding key type was not preserved');
   }
   host.remove();
   return ['keyed focus/selection','newer drafts','blur normalization','synthetic composition',
    'partial DOM recovery','rebinding cancellation','native editor sizing','style/layout resets','disabled buttons','label role removal','list/dict key types'];
  },fieldType);
  assert.deepEqual(errors,[]);console.log(fieldType+' real DOM checks passed: '+checks.join(', ')+'.');
  }
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
