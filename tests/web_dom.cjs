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
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await page.getByText('Row 1',{exact:true}).waitFor();
  const checks=await page.evaluate(async()=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const host=document.createElement('section');document.body.append(host);
   const actions=[];let sequence=10;
   const r=new Renderer(host,(type,body,onSent)=>{actions.push({type,body});onSent?.(sequence++);});
   const check=(condition,message)=>{if(!condition)throw new Error(message);};
   const ref={object_id:'12345',kind:'attr',key:'value'};
   const slot={ref,token:'s1',value_rev:1,value:'initial'};
   const attachment={ref,token:'a1',slot_token:'s1',writable:true};
   const node=(id,type,props={},children=[])=>({id,type,props,children,layout:{},style:{},bindings:{},events:{}});
   const editor=node('input','TextField',{text:'initial',placeholder:''});
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
   const input=r.elements.get('input');input.focus();input.value='draft';inputEvent(input);
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
   host.remove();
   return ['keyed focus/selection','newer drafts','blur normalization','synthetic composition',
    'partial DOM recovery','rebinding cancellation'];
  });
  assert.deepEqual(errors,[]);console.log('Real DOM checks passed: '+checks.join(', ')+'.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
