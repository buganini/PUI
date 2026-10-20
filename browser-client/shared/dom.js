import { Completion } from './completion.js';
import { Drops } from './drop.js';
import { Canvases, validateFrame, patchFrame, canvasEvents } from './canvas.js';
import { applyLayout } from './layout.js';
import { Tables, validateTable } from './table.js';
import { validateStateBudget } from './budget.js';
const fields = ['props','layout','style','bindings','events'];
const tags = {Window:'section',VBox:'div',HBox:'div',Label:'span',Button:'button',
  TextField:'input',MaskedField:'input',Text:'pre',Spacer:'div',Divider:'hr',Scroll:'div',Grid:'div',ProgressBar:'progress',Views:'div',Tabs:'div',Tab:'div',
  Checkbox:'label',RadioButton:'label',ComboBox:'div',ComboBoxItem:'option',Canvas:'div',Stack:'div',Table:'div',Image:'img'};
const containers = new Set(['Window','VBox','HBox','Scroll','Grid','Views','Tabs','Tab','ComboBox','Stack']);
const isTextField = n => n.type==='TextField' || n.type==='MaskedField';
const roles={TextField:['model','edit_model'],MaskedField:['model','edit_model'],Tabs:['model'],Checkbox:['model'],RadioButton:['model'],ComboBox:['index_model','text_model']};
const nativeEvent=n=>({Table:'table',Tabs:'select',Checkbox:'toggle',RadioButton:'activate',ComboBox:n.props.editable?'edit':'choose'})[n.type];
const fail = message => { throw new Error(message); };
const copy = value => structuredClone(value);
const object = value => value!==null && typeof value==='object' && Object.getPrototypeOf(value)===Object.prototype;
const exact = (value, keys) => object(value) && Object.keys(value).sort().join(',')===keys.slice().sort().join(',');
const refValid = value => exact(value,['object_id','kind','key']) &&
  typeof value.object_id==='string' && /^[1-9][0-9]*$/.test(value.object_id) &&
  ((value.kind==='attr' && typeof value.key==='string') || (value.kind==='value' && value.key===null) ||
   (value.kind==='list' && Number.isSafeInteger(value.key)) ||
   (value.kind==='dict' && (typeof value.key==='string' || Number.isSafeInteger(value.key))));
const refEqual = (a,b) => a && b && a.object_id===b.object_id && a.kind===b.kind && a.key===b.key;
const allowedProps = {Window:['title'],VBox:['direction'],HBox:[],Label:['text','selectable'],
  Button:['text','disabled'],TextField:['text','placeholder'],MaskedField:['text','placeholder'],Text:['text'],Spacer:[],
  Divider:[],Scroll:['vertical','horizontal','scroll_x','scroll_y'],Grid:[],ProgressBar:['progress','maximum'],
  Views:['selected'],Tabs:['selected','position'],Tab:['label'],Checkbox:['text','checked','disabled'],RadioButton:['text','checked','disabled'],
  ComboBox:['disabled','selected','editable','autoexpand','text'],ComboBoxItem:['text'],Canvas:['show_fps'],Stack:[],Table:['rows','columns','column_header','row_headers','autofit'],Image:['src','alt']};

function validate(state, imageURL) {
  if(state.roots.length>1 || (state.roots.length && state.nodes.get(state.roots[0])?.type!=='Window')) fail('Invalid root');
  const seen=new Set(), attachments=new Set(), usedSlots=new Set();
  function visit(id,parent=null) {
    if(seen.has(id) || !state.nodes.has(id)) fail('Duplicate/missing node');
    seen.add(id);
    const n=state.nodes.get(id);
    if(!exact(n,['id','type','children',...fields]) || !Object.hasOwn(tags,n.type) ||
      typeof n.id!=='string' || !n.id || !Array.isArray(n.children) || fields.some(f=>!object(n[f]))) fail('Invalid node');
    if(!containers.has(n.type) && n.children.length) fail('Children on terminal node');
    if(Object.keys(n.props).some(k=>k!=='drop_extensions' && !allowedProps[n.type].includes(k))) fail('Unknown property');
    const normalProps=Object.fromEntries(Object.entries(n.props).filter(([k])=>k!=='drop_extensions'));
    if(n.type==='Table')validateTable(normalProps);
    if(n.type==='Image' && (!exact(normalProps,['src','alt']) || !imageURL(n.props.src)))fail('Invalid Image source');
    for(const [k,v] of Object.entries(n.props)) {
      if(k==='drop_extensions'){if(v!==null && (!Array.isArray(v) || v.some(s=>typeof s!=='string' || (s!=='/' && !s.startsWith('.')))))fail('Invalid drop extensions');continue;}
      if(n.type==='Table')continue;
      if(k==='selected') {
        if(v!==null && (typeof v!=='string' || !n.children.includes(v)))fail('Invalid selected page');
      } else if(k==='position') {
        if(!['n','s','e','w'].includes(v))fail('Invalid tab position');
      } else if(['scroll_x','scroll_y'].includes(k)) {
        if(v!==null && (!Array.isArray(v) || v.length!==3 || !['start','end'].includes(v[0]) ||
          !Number.isFinite(v[1]) || v[1]<0 || !Number.isSafeInteger(v[2]) || v[2]<1)) fail('Invalid scroll request');
      } else if(['progress','maximum'].includes(k)) {
        if(!Number.isFinite(v) || v<0) fail('Invalid progress');
      } else if(['disabled','selectable','checked','editable','autoexpand','show_fps'].includes(k) ? typeof v!=='boolean' : typeof v!=='string') fail('Invalid property');
      if(k==='direction' && !['row','column'].includes(v))fail('Invalid direction');
      if(['vertical','horizontal'].includes(k) && !['auto','scroll','hidden'].includes(v)) fail('Invalid overflow');
    }
    for(const [k,v] of Object.entries(n.layout)) {
      if(k==='visible' || k==='observe_size') {
        if(typeof v!=='boolean')fail('Invalid visibility');
      } else if(['padding','margin'].includes(k)) {
        if(!Array.isArray(v) || v.length!==4 || v.some(x=>!Number.isFinite(x))) fail('Invalid spacing');
      } else if(['row','column','rowspan','columnspan'].includes(k)) {
        if(!Number.isInteger(v) || v<(k.endsWith('span')?1:0) || v>10000) fail('Invalid grid placement');
      } else if(!['width','height','weight'].includes(k) || !Number.isFinite(v) || v<0) fail('Invalid dimension');
    }
    if(['row','column','rowspan','columnspan'].some(k=>Object.hasOwn(n.layout,k)) &&
      state.nodes.get(parent)?.type!=='Grid') fail('Grid placement outside Grid');
    if(state.nodes.get(parent)?.type==='Grid' &&
      (!Object.hasOwn(n.layout,'row') || !Object.hasOwn(n.layout,'column'))) fail('Missing Grid position');
    if(n.type==='ProgressBar' && (!exact(normalProps,['progress','maximum']) ||
      n.props.progress>n.props.maximum)) fail('Invalid progress range');
    if(n.type==='Tabs' && n.children.some(id=>state.nodes.get(id)?.type!=='Tab'))fail('Tabs require Tab children');
    if(n.type==='Tab' && state.nodes.get(parent)?.type!=='Tabs')fail('Tab requires Tabs parent');
    if(n.type==='ComboBox' && n.children.some(id=>state.nodes.get(id)?.type!=='ComboBoxItem'))fail('Invalid ComboBox items');
    if(n.type==='ComboBoxItem' && state.nodes.get(parent)?.type!=='ComboBox')fail('ComboBoxItem requires ComboBox parent');
    for(const [k,v] of Object.entries(n.style)) {
      if(['color','background'].includes(k)) { if(!/^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(v)) fail('Invalid color'); }
      else if(['font_size_pt','font_weight'].includes(k)) {
        if(!Number.isFinite(v) && !(k==='font_weight' && ['normal','bold'].includes(v))) fail('Invalid font');
      } else if(k!=='font_family' || typeof v!=='string') fail('Invalid style');
    }
    for(const [name,token] of Object.entries(n.events))
      if(![...(n.type==='Canvas'?canvasEvents:['click','input',nativeEvent(n)]),'drop','dragEnter'].includes(name) || typeof token!=='string' || !token) fail('Invalid event');
    for(const [role,a] of Object.entries(n.bindings)) {
      const slot=state.slots.get(a?.slot_token);
      if(!roles[n.type]?.includes(role) ||
        !exact(a,['ref','slot_token','token','writable']) || !refValid(a.ref) || typeof a.token!=='string' || !a.token ||
        attachments.has(a.token) || typeof a.writable!=='boolean' || !slot || !refEqual(slot.ref,a.ref)) fail('Invalid attachment');
      attachments.add(a.token); usedSlots.add(a.slot_token);
    }
    if(isTextField(n) && !n.bindings.model) fail('Missing TextField model');
    if(n.type==='Tabs' && (!n.bindings.model || !n.events.select))fail('Missing Tabs selection');
    if(['Checkbox','RadioButton'].includes(n.type) && !n.bindings.model)fail('Missing control model');
    if(nativeEvent(n) && !n.events[nativeEvent(n)])fail('Missing native event');
    for(const child of n.children) visit(child,id);
  }
  for(const root of state.roots) visit(root);
  if(seen.size!==state.nodes.size || usedSlots.size!==state.slots.size) fail('Orphan records');
  let pixels=0;
  for(const f of state.canvases.values()) {
    validateFrame(f);if(state.nodes.get(f.node_id)?.type!=='Canvas')fail('Invalid Canvas owner');
    pixels+=Math.ceil(f.width*f.dpr)*Math.ceil(f.height*f.dpr);
  }
  if(pixels>33554432)fail('Canvas bitmap budget exceeded');
}
function slot(state, value) {
  if(!exact(value,['ref','token','value_rev','value']) || typeof value.token!=='string' || !value.token ||
    !Number.isSafeInteger(value.value_rev) || value.value_rev<=0 ||
    !refValid(value.ref)) fail('Invalid slot');
  const old=state.slots.get(value.token);
  if(old && (!refEqual(old.ref,value.ref) || value.value_rev<old.value_rev)) fail('Slot identity changed');
  state.slots.set(value.token,copy(value));
}
export function prepare(previous, body, imageURL=()=>false) {
  let state;
  if(body.mode==='snapshot') {
    if(!exact(body,['mode','base_rev','rev','processed_seq','roots','bindings','canvases']) ||
      body.base_rev!==null || !Array.isArray(body.roots) || !Array.isArray(body.bindings) ||
      !Array.isArray(body.canvases)) fail('Invalid snapshot');
    state={nodes:new Map(),roots:[],slots:new Map(),canvases:new Map()};
    function visit(n) {
      if(!object(n) || state.nodes.has(n.id) || !Array.isArray(n.children)) fail('Invalid snapshot node');
      const record=copy(n); record.children=n.children.map(c=>c.id); state.nodes.set(n.id,record);
      for(const child of n.children) visit(child);
    }
    for(const root of body.roots) { state.roots.push(root.id); visit(root); }
    for(const value of body.bindings) { if(state.slots.has(value.token)) fail('Duplicate slot'); slot(state,value); }
    for(const frame of body.canvases) {
      validateFrame(frame);if(state.canvases.has(frame.node_id))fail('Duplicate Canvas');state.canvases.set(frame.node_id,copy(frame));
    }
  } else {
    if(!exact(body,['mode','base_rev','rev','processed_seq','ops']) || !Array.isArray(body.ops)) fail('Invalid patch');
    state={nodes:new Map([...previous.nodes].map(([k,v])=>[k,copy(v)])),roots:previous.roots.slice(),
      slots:new Map([...previous.slots].map(([k,v])=>[k,copy(v)])),
      // Canvas display lists are immutable after publication. Replacement and
      // splice operations install new frames; failed prepares leave these intact.
      canvases:new Map(previous.canvases || [])};
    const parents=new Map();
    for(const id of state.roots) parents.set(id,null);
    for(const n of state.nodes.values()) for(const id of n.children) parents.set(id,n.id);
    const siblings=parent=>parent===null?state.roots:state.nodes.get(parent)?.children;
    function remove(id) {
      const n=state.nodes.get(id); if(!n) fail('Missing removal');
      for(const child of n.children.slice()) remove(child);
      const list=siblings(parents.get(id)); if(list) list.splice(list.indexOf(id),1);
      parents.delete(id); state.nodes.delete(id);
      state.canvases.delete(id);
    }
    for(const op of body.ops) {
      const n=state.nodes.get(op.node_id);
      if(op.op==='create_node') {
        if(!exact(op,['op','node']) || !object(op.node) || state.nodes.has(op.node.id) ||
          !Array.isArray(op.node.children) || op.node.children.length) fail('Invalid create');
        state.nodes.set(op.node.id,copy(op.node));
      } else if(op.op==='patch_node') {
        if(!exact(op,['op','node_id','field','set','unset']) || !n || !fields.includes(op.field) ||
          !object(op.set) || !Array.isArray(op.unset) || new Set(op.unset).size!==op.unset.length ||
          op.unset.some(k=>typeof k!=='string' || Object.hasOwn(op.set,k))) fail('Invalid map patch');
        Object.assign(n[op.field],copy(op.set)); for(const key of op.unset) delete n[op.field][key];
      } else if(op.op==='place_node') {
        if(!exact(op,['op','node_id','parent_id','before_id']) || !n || op.node_id===op.before_id ||
          (op.parent_id!==null && !containers.has(state.nodes.get(op.parent_id)?.type))) fail('Invalid placement');
        let ancestor=op.parent_id;
        while(ancestor!==null && ancestor!==undefined) {
          if(ancestor===op.node_id) fail('Placement cycle'); ancestor=parents.get(ancestor);
        }
        const target=siblings(op.parent_id);
        if(op.before_id!==null && !target.includes(op.before_id)) fail('Missing sibling');
        if(parents.has(op.node_id)) { const old=siblings(parents.get(op.node_id)); old.splice(old.indexOf(op.node_id),1); }
        target.splice(op.before_id===null?target.length:target.indexOf(op.before_id),0,op.node_id);
        parents.set(op.node_id,op.parent_id);
      } else if(op.op==='remove_node') {
        if(!exact(op,['op','node_id'])) fail('Invalid remove'); remove(op.node_id);
      } else if(op.op==='put_binding') {
        if(!exact(op,['op','slot'])) fail('Invalid binding'); slot(state,op.slot);
      } else if(op.op==='remove_binding') {
        if(!exact(op,['op','slot_token']) || !state.slots.delete(op.slot_token)) fail('Invalid binding removal');
      } else if(op.op==='put_canvas') {
        if(!exact(op,['op','frame']))fail('Invalid Canvas update');validateFrame(op.frame);
        state.canvases.set(op.frame.node_id,copy(op.frame));
      } else if(op.op==='patch_canvas') {
        const frame=patchFrame(state.canvases.get(op.frame?.node_id),op);
        state.canvases.set(frame.node_id,frame);
      } else if(op.op==='remove_canvas') {
        if(!exact(op,['op','node_id']) || !state.canvases.delete(op.node_id))fail('Invalid Canvas removal');
      } else fail('Unsupported operation');
    }
  }
  validate(state,imageURL); validateStateBudget(state); return state;
}

export class Renderer {
  constructor(root, actions, control=()=>{}, onError=error=>{throw error;},resources={valid:()=>false,url:value=>value}) {
    this.resources=resources;
    this.sizes=new Map();this.sizeControl=control;
    this.root=root; this.actions=actions; this.elements=new Map(); this.drafts=new Map();
    this.scrolls=new Map();
    this.tabs=new Map();
    this.combos=new Map();this.controlEdits=new Map();
    this.tables=new Tables(this);
    this.drops=new Drops(this);
    this.state={nodes:new Map(),roots:[],slots:new Map(),canvases:new Map()}; this.rev=0; this.dirty=false; this.applying=false;
    this.canvases=new Canvases(this,control,onError);
  }
  make(n) {
    const e=document.createElement(tags[n.type]); e.dataset.puiId=n.id; e.className='pui-'+n.type;
    if(n.type==='Button') e.type='button';
    if(n.type==='Image')e.addEventListener('error',()=>console.warn('PUI Image could not load: '+e.alt));
    if(n.type==='Canvas')this.canvases.add(n.id,e);
    if(n.type==='Table')this.tables.add(n.id,e);
    if(['Checkbox','RadioButton'].includes(n.type)) {
      const input=document.createElement('input'),label=document.createElement('span');
      input.type=n.type==='Checkbox'?'checkbox':'radio';e.append(input,label);
      input.addEventListener(n.type==='Checkbox'?'change':'click',()=>{
        this.nativeAction(n.id,nativeEvent(n),n.type==='Checkbox'?{checked:input.checked}:{},
          n.type==='Checkbox'?input.checked:n.id);
      });
    }
    if(n.type==='ComboBox') {
      const select=document.createElement('select'),input=document.createElement('input'),list=document.createElement('datalist');
      const blank=document.createElement('option');blank.value='';blank.hidden=true;blank.disabled=true;select.append(blank);
      list.id='pui-choices-'+n.id;input.dataset.puiEditor=n.id;
      e.append(select,input,list);this.combos.set(n.id,{select,input,list,editable:n.props.editable});
      select.addEventListener('change',()=>{if(select.value)this.nativeAction(n.id,'choose',{item_id:select.value},select.value);});
      const c=this.combos.get(n.id);
      c.completion=new Completion(this,n.id,input,list);
      c.button=document.createElement('button');c.button.type='button';c.button.textContent='▾';
      c.button.setAttribute('aria-label','Show choices');c.button.tabIndex=-1;e.append(c.button);
      c.button.addEventListener('pointerdown',event=>event.preventDefault());
      c.button.addEventListener('click',()=>{input.focus();if(c.completion.popup.hidden)c.completion.refresh(true,true);else c.completion.hide();});
      this.listenEditor(input,n.id);
    }
    if(n.type==='Tabs') {
      const header=document.createElement('div'),pages=document.createElement('div');
      header.className='pui-tab-list';header.setAttribute('role','tablist');
      pages.className='pui-tab-pages';e.append(header,pages);
      this.tabs.set(n.id,{header,pages,buttons:new Map()});
    }
    if(n.type==='Scroll') {
      const state={axes:[{anchor:'start',offset:0,last:0,request:null},{anchor:'start',offset:0,last:0,request:null}]};
      state.observer=new ResizeObserver(()=>{if(!this.applying && !this.dirty)this.restoreScroll(n.id);});
      this.scrolls.set(n.id,state);
      e.addEventListener('scroll',()=>{if(!this.applying && !this.dirty)this.captureScroll(n.id);});
    }
    if(isTextField(n)) {
      e.type=n.type==='MaskedField'?'password':'text';this.listenEditor(e,n.id);
    }
    e.addEventListener('click',event=>{
      if(['Checkbox','RadioButton','Canvas','Table'].includes(n.type))return;
      if(this.applying || this.dirty || !this.state.nodes.get(n.id)?.events.click) return;
      event.stopPropagation();
      const focused=this.focusedEditor();if(focused)this.commit(focused);
      const record=this.state.nodes.get(n.id);
      this.actions('event',{node_id:n.id,event:'click',token:record.events.click,observed_render_rev:this.rev,data:{}});
    });
    if(n.type==='Label') e.addEventListener('keydown',event=>{
      if((event.key==='Enter' || event.key===' ') && this.state.nodes.get(n.id)?.events.click){event.preventDefault();e.click();}
    });
    this.elements.set(n.id,e); return e;
  }
  focusedEditor() {return document.activeElement?.dataset.puiEditor || document.activeElement?.dataset.puiId;}
  editor(id) {return this.combos.get(id)?.input || this.elements.get(id);}
  listenEditor(e,id) {
    e.addEventListener('input',()=>this.input(id));
    e.addEventListener('compositionstart',()=>{this.draft(id).composing=true;});
    e.addEventListener('compositionend',()=>{this.draft(id).composing=false;this.input(id);if(document.activeElement!==e)this.commit(id);});
    e.addEventListener('blur',()=>this.commit(id));
    e.addEventListener('keydown',event=>{if(event.key==='Enter' && !event.isComposing){this.commit(id);e.blur();}});
  }
  controlKey(n) {
    return n.type==='RadioButton'?'radio:'+n.bindings.model.slot_token+':'+this.elements.get(n.id).parentElement?.dataset.puiId:n.id;
  }
  nativeAction(id,event,data,value) {
    if(this.applying || this.dirty)return;
    const n=this.state.nodes.get(id);if(!n?.events[event] || n.props.disabled===true)return;
    const focused=this.focusedEditor();if(focused)this.commit(focused);
    const pending={node:id,token:n.events[event],value,seq:null};
    this.controlEdits.set(this.controlKey(n),pending);
    this.actions('event',{node_id:id,event,token:n.events[event],observed_render_rev:this.rev,data},seq=>{pending.seq=seq;});
  }
  draft(id) {
    if(!this.drafts.has(id)) this.drafts.set(id,{editSeq:0,committed:0,editing:false,composing:false,lastSent:0,pending:null});
    return this.drafts.get(id);
  }
  input(id,notify=true) {
    if(this.applying || this.dirty) return;
    const n=this.state.nodes.get(id), e=this.editor(id), d=this.draft(id);
    if(d.value!==e.value) {d.value=e.value;d.editSeq++;}
    d.editing=true;
    if(!notify)return;
    if(d.composing || d.lastSent===d.editSeq) return;
    d.lastSent=d.editSeq;
    if(n.bindings.edit_model) this.write(n,'edit_model','input',d);
    else if(n.events.input) this.actions('event',{node_id:id,event:'input',token:n.events.input,
      observed_render_rev:this.rev,data:{value:e.value,edit_seq:d.editSeq,composing:false}},
      seq=>{d.inputSeq=seq;});
  }
  write(n,role,phase,d,onSent) {
    const a=n.bindings[role], s=this.state.slots.get(a.slot_token);
    this.actions('binding_write',{node_id:n.id,role,phase,ref:a.ref,slot_token:a.slot_token,
      attachment_token:a.token,observed_render_rev:this.rev,observed_value_rev:s.value_rev,
      edit_seq:d.editSeq,value:this.elements.get(n.id).value},onSent);
  }
  commit(id) {
    if(this.applying || this.dirty) return;
    if(this.state.nodes.get(id)?.type==='Table'){this.tables.commit(id);return;}
    const n=this.state.nodes.get(id); if(!n || (!isTextField(n) && !(n.type==='ComboBox' && n.props.editable))) return;
    if(n.props.disabled===true)return;
    const d=this.draft(id);
    if(d.composing || !d.editing || d.committed===d.editSeq) return;
    if(n.type==='ComboBox' && d.inputSeq>(this.processedSeq || 0)){
      d.commitRequested=true;return;
    }
    d.commitRequested=false;
    d.committed=d.editSeq;
    const pending={seq:null,editSeq:d.editSeq}; d.pending=pending;
    if(n.type==='ComboBox')this.actions('event',{node_id:id,event:'edit',token:n.events.edit,
      observed_render_rev:this.rev,data:{value:this.editor(id).value,edit_seq:d.editSeq,composing:false}},seq=>{pending.seq=seq;});
    else this.write(n,'model','commit',d,seq=>{pending.seq=seq;});
  }
  update(n) {
    const e=this.elements.get(n.id); e.style.cssText='';
    this.drops.update(n,e);
    if(n.type==='VBox')e.style.flexDirection=n.props.direction || '';
    if(n.type==='Window') document.title=n.props.title ?? 'PUI';
    if(['Label','Button','Text'].includes(n.type)) e.textContent=n.props.text ?? '';
    if(n.type==='Label') {
      e.style.userSelect=n.props.selectable?'text':'none';
      if(n.events.click) {e.setAttribute('role','button');e.tabIndex=0;e.style.cursor='pointer';}
      else {e.removeAttribute('role');e.removeAttribute('tabindex');}
    }
    if(n.type==='Button') e.disabled=n.props.disabled===true;
    if(n.type==='Canvas')this.canvases.update(n);
    if(isTextField(n)) e.placeholder=n.props.placeholder || '';
    if(n.type==='Image'){const url=this.resources.url(n.props.src);if(e.getAttribute('src')!==url)e.src=url;e.alt=n.props.alt;}
    if(['Checkbox','RadioButton'].includes(n.type)){
      e.lastElementChild.textContent=n.props.text;
      e.firstElementChild.disabled=n.props.disabled===true;
    }
    if(n.type==='ComboBoxItem')e.textContent=n.props.text;
    if(n.type==='ComboBox') {
      const c=this.combos.get(n.id);c.editable=n.props.editable;
      c.input.hidden=!c.editable;c.select.hidden=c.editable;c.button.hidden=!c.editable;
      c.button.disabled=n.props.disabled===true;
      c.input.setAttribute('aria-autocomplete',n.props.autoexpand===false?'none':'list');
      c.input.disabled=c.select.disabled=n.props.disabled===true;
    }
    if(n.type==='Scroll') {e.style.overflowY=n.props.vertical;e.style.overflowX=n.props.horizontal;}
    if(n.type==='ProgressBar') {
      e.max=n.props.maximum || 1;
      if(n.props.maximum===0) e.removeAttribute('value'); else e.value=n.props.progress;
    }
    for(const [position,span,property] of [['row','rowspan','gridRow'],['column','columnspan','gridColumn']])
      if(n.layout[position]!==undefined) e.style[property]=`${n.layout[position]+1} / span ${n.layout[span] || 1}`;
    for(const name of ['width','height']) if(n.layout[name]!==undefined) {
      e.style[name]=n.layout[name]+'px'; e.style['min'+name[0].toUpperCase()+name.slice(1)]=n.layout[name]+'px';
    }
    for(const name of ['padding','margin']) if(n.layout[name]) e.style[name]=n.layout[name].map(v=>v+'px').join(' ');
    for(const [name,prop] of [['color','color'],['background','backgroundColor'],['font_weight','fontWeight'],['font_family','fontFamily']])
      if(n.style[name]!==undefined) e.style[prop]=n.style[name];
    if(n.style.font_size_pt!==undefined) e.style.fontSize=n.style.font_size_pt+'pt';
  }
  place(id,parent,before) {
    const combo=this.combos.get(parent);
    const e=this.elements.get(id), p=parent===null?this.root:(combo?(combo.editable?combo.list:combo.select):(this.tabs.get(parent)?.pages || this.elements.get(parent))), anchor=before===null?null:this.elements.get(before);
    if(e.parentNode===p && e.nextSibling===anchor) return;
    if(p.moveBefore && e.isConnected && p.isConnected) p.moveBefore(e,anchor);
    else p.insertBefore(e,anchor);
  }
  captureScroll(id) {
    const state=this.scrolls.get(id),e=this.elements.get(id);
    if(!state || !e?.clientWidth || !e.clientHeight)return;
    for(const [axis,position,size,client] of [[0,'scrollLeft','scrollWidth','clientWidth'],[1,'scrollTop','scrollHeight','clientHeight']]) {
      const a=state.axes[axis],max=Math.max(0,e[size]-e[client]),value=e[position];
      if(max===0 || Math.abs(value-a.last)<1)continue;
      if(max>20) {if(value<=10)a.anchor='start';else if(value>=max-10)a.anchor='end';}
      a.offset=a.anchor==='start'?value:max-value;a.last=value;
    }
  }
  restoreScroll(id) {
    const state=this.scrolls.get(id),e=this.elements.get(id);
    if(!state || !e?.isConnected || !e.clientWidth || !e.clientHeight)return;
    for(const [axis,position,size,client] of [[0,'scrollLeft','scrollWidth','clientWidth'],[1,'scrollTop','scrollHeight','clientHeight']]) {
      const a=state.axes[axis],max=Math.max(0,e[size]-e[client]);
      e[position]=Math.max(0,Math.min(max,a.anchor==='start'?a.offset:max-a.offset));a.last=e[position];
    }
  }
  resetSizes() {
    for(const observer of this.sizes.values())observer.disconnect();
    this.sizes.clear();
  }
  observeSize(n) {
    const previous=this.sizes.get(n.id);
    if(!n.layout.observe_size) {
      previous?.disconnect();this.sizes.delete(n.id);return;
    }
    if(previous)return;
    const observer=new ResizeObserver(entries=>{
      if(this.dirty)return;
      const {width,height}=entries[0].contentRect;
      this.sizeControl('container_size',{node_id:n.id,width,height});
    });
    observer.observe(this.elements.get(n.id));this.sizes.set(n.id,observer);
  }
  forget(id) {
    this.sizes.get(id)?.disconnect();this.sizes.delete(id);
    this.tables.remove(id);
    this.canvases.remove(id);
    this.scrolls.get(id)?.observer.disconnect();this.scrolls.delete(id);
    this.elements.delete(id);this.drafts.delete(id);
    this.tabs.delete(id);
    this.combos.get(id)?.completion.destroy();
    this.combos.delete(id);
    for(const [key,value] of this.controlEdits)if(value.node===id)this.controlEdits.delete(key);
  }
  destroy() {
    for(const id of this.elements.keys())this.forget(id);
    this.canvases.destroy();
    this.drops.stop();
  }
  selectTab(id,pageId) {
    if(this.applying || this.dirty)return;
    const n=this.state.nodes.get(id);
    if(!n?.events.select || !n.children.includes(pageId))return;
    const focused=this.focusedEditor();
    if(focused)this.commit(focused);
    this.actions('event',{node_id:id,event:'select',token:n.events.select,
      observed_render_rev:this.rev,data:{page_id:pageId}});
  }
  showPages(next) {
    for(const n of next.nodes.values())this.observeSize(n);
    for(const n of next.nodes.values())this.elements.get(n.id).hidden=n.layout.visible===false;
    for(const n of next.nodes.values()) if(['Views','Tabs'].includes(n.type)) {
      for(const id of n.children)this.elements.get(id).hidden=id!==n.props.selected || next.nodes.get(id).layout.visible===false;
      if(n.type!=='Tabs')continue;
      const state=this.tabs.get(n.id),vertical=['e','w'].includes(n.props.position);
      this.elements.get(n.id).dataset.position=n.props.position;
      state.header.setAttribute('aria-orientation',vertical?'vertical':'horizontal');
      for(const [id,button] of state.buttons)if(!n.children.includes(id)){button.remove();state.buttons.delete(id);}
      for(const [index,id] of n.children.entries()) {
        let button=state.buttons.get(id);
        if(!button) {
          button=document.createElement('button');button.type='button';button.setAttribute('role','tab');
          button.id='pui-tab-'+id;button.setAttribute('aria-controls','pui-panel-'+id);
          button.addEventListener('click',event=>{event.stopPropagation();this.selectTab(n.id,id);});
          button.addEventListener('keydown',event=>{
            const current=this.state.nodes.get(n.id),vertical=['e','w'].includes(current.props.position),ids=current.children;
            let i=ids.indexOf(id);
            if(event.key===(vertical?'ArrowDown':'ArrowRight'))i=(i+1)%ids.length;
            else if(event.key===(vertical?'ArrowUp':'ArrowLeft'))i=(i+ids.length-1)%ids.length;
            else if(event.key==='Home')i=0;else if(event.key==='End')i=ids.length-1;else return;
            event.preventDefault();state.buttons.get(ids[i]).focus();this.selectTab(n.id,ids[i]);
          });
          state.buttons.set(id,button);
        }
        button.textContent=next.nodes.get(id).props.label;
        button.setAttribute('aria-selected',String(id===n.props.selected));button.tabIndex=id===n.props.selected?0:-1;
        const page=this.elements.get(id);page.id='pui-panel-'+id;page.setAttribute('role','tabpanel');
        page.setAttribute('aria-labelledby',button.id);
        const anchor=state.header.children[index] || null;
        if(anchor!==button) {
          if(state.header.moveBefore && button.isConnected)state.header.moveBefore(button,anchor);
          else state.header.insertBefore(button,anchor);
        }
      }
    }
  }
  syncControls(next,processed) {
    for(const [key,pending] of this.controlEdits) {
      const source=next.nodes.get(pending.node);
      if(!source || source.events[nativeEvent(source)]!==pending.token ||
        (pending.seq!==null && processed>=pending.seq))this.controlEdits.delete(key);
    }
    for(const n of next.nodes.values())if(n.type==='RadioButton')this.elements.get(n.id).firstElementChild.name=this.controlKey(n);
    for(const n of next.nodes.values()) {
      const e=this.elements.get(n.id),pending=this.controlEdits.get(this.controlKey(n));
      if(['Checkbox','RadioButton'].includes(n.type)) {
        e.firstElementChild.checked=pending?(n.type==='RadioButton'?pending.value===n.id:pending.value):n.props.checked;
      } else if(n.type==='ComboBox') {
        const c=this.combos.get(n.id),parent=c.editable?c.list:c.select;
        for(const id of n.children) {
          const item=this.elements.get(id);
          item.value=c.editable?next.nodes.get(id).props.text:id;
          if(item.parentNode!==parent)parent.append(item);
        }
        c.select.value=pending?pending.value:(n.props.selected || '');
      }
    }
  }
  apply(body) {
    const next=prepare(this.state,body,this.resources.valid), active=document.activeElement;
    if(!this.dirty)for(const id of this.scrolls.keys())this.captureScroll(id);
    this.applying=true;
    try {
      if(body.mode==='snapshot') {
        for(const n of next.nodes.values()) {
          const old=this.elements.get(n.id);
          if(old && this.state.nodes.get(n.id)?.type!==n.type) {old.remove();this.forget(n.id);}
          if(!this.elements.has(n.id)) this.make(n);
          this.update(n);
        }
        const walk=(ids,parent)=>{let before=null;for(const id of ids.slice().reverse()){this.place(id,parent,before);before=id;}
          for(const id of ids) walk(next.nodes.get(id).children,id);};
        walk(next.roots,null);
        for(const [id,e] of this.elements) if(!next.nodes.has(id)){e.remove();this.forget(id);}
      } else for(const op of body.ops) {
        if(op.op==='create_node') {this.make(op.node);this.update(next.nodes.get(op.node.id));}
        else if(op.op==='patch_node') this.update(next.nodes.get(op.node_id));
        else if(op.op==='place_node') this.place(op.node_id,op.parent_id,op.before_id);
        else if(op.op==='remove_node') {
          const e=this.elements.get(op.node_id);
          for(const child of [e,...e.querySelectorAll('[data-pui-id]')]) {
            this.forget(child.dataset.puiId);
          }
          e.remove();
        }
      }
      this.showPages(next);
      this.syncControls(next,body.processed_seq);
      for(const n of next.nodes.values())if(n.type==='Table')this.tables.sync(n.id,n.props,body.processed_seq);
      applyLayout(next,this.elements);
      for(const n of next.nodes.values()) if(n.type==='Scroll') {
        const state=this.scrolls.get(n.id),e=this.elements.get(n.id);
        for(const [axis,key] of [[0,'scroll_x'],[1,'scroll_y']]) {
          const request=n.props[key],a=state.axes[axis];
          if(request && request[2]!==a.request) {a.anchor=request[0];a.offset=request[1];a.request=request[2];}
        }
        state.observer.disconnect();state.observer.observe(e);
        for(const child of e.children)state.observer.observe(child);
        this.restoreScroll(n.id);
      }
      for(const n of next.nodes.values()) if(isTextField(n) || (n.type==='ComboBox' && n.props.editable)) {
        const e=this.editor(n.id),token=isTextField(n)?n.bindings.model.token:(n.events.input || n.events.edit); let d=this.draft(n.id);
        if(d.token!==token){this.drafts.delete(n.id);d=this.draft(n.id);d.token=token;}
        if(d.pending && d.pending.seq!==null && body.processed_seq>=d.pending.seq &&
          d.editSeq===d.pending.editSeq && !d.composing) {d.editing=false;d.pending=null;}
        if(!d.editing && !d.composing) {if(e.value!==n.props.text)e.value=n.props.text;d.value=e.value;}
      }
      if(active?.isConnected && active!==document.activeElement && document.activeElement===document.body)
        active.focus({preventScroll:true});
      this.canvases.sync(next,body);
      this.state=next;
      this.rev=body.rev;this.dirty=false;
      this.processedSeq=body.processed_seq;
      for(const c of this.combos.values())c.completion.refresh();
    } finally {this.applying=false;}
    for(const [id,d] of this.drafts)if(d.commitRequested)this.commit(id);
  }
}
