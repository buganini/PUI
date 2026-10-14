const fields = ['props','layout','style','bindings','events'];
const tags = {Window:'section',VBox:'div',HBox:'div',Label:'span',Button:'button',
  TextField:'input',Text:'pre',Spacer:'div',Divider:'hr',Scroll:'div',Grid:'div',ProgressBar:'progress'};
const containers = new Set(['Window','VBox','HBox','Scroll','Grid']);
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
const allowedProps = {Window:['title'],VBox:[],HBox:[],Label:['text','selectable'],
  Button:['text','enabled'],TextField:['text','placeholder'],Text:['text'],Spacer:[],
  Divider:[],Scroll:['vertical','horizontal'],Grid:[],ProgressBar:['progress','maximum']};

function validate(state) {
  if(state.roots.length>1 || (state.roots.length && state.nodes.get(state.roots[0])?.type!=='Window')) fail('Invalid root');
  const seen=new Set(), attachments=new Set(), usedSlots=new Set();
  function visit(id,parent=null) {
    if(seen.has(id) || !state.nodes.has(id)) fail('Duplicate/missing node');
    seen.add(id);
    const n=state.nodes.get(id);
    if(!exact(n,['id','type','children',...fields]) || !Object.hasOwn(tags,n.type) ||
      typeof n.id!=='string' || !n.id || !Array.isArray(n.children) || fields.some(f=>!object(n[f]))) fail('Invalid node');
    if(!containers.has(n.type) && n.children.length) fail('Children on terminal node');
    if(Object.keys(n.props).some(k=>!allowedProps[n.type].includes(k))) fail('Unknown property');
    for(const [k,v] of Object.entries(n.props)) {
      if(['progress','maximum'].includes(k)) {
        if(!Number.isFinite(v) || v<0) fail('Invalid progress');
      } else if(['enabled','selectable'].includes(k) ? typeof v!=='boolean' : typeof v!=='string') fail('Invalid property');
      if(['vertical','horizontal'].includes(k) && !['auto','scroll','hidden'].includes(v)) fail('Invalid overflow');
    }
    for(const [k,v] of Object.entries(n.layout)) {
      if(['padding','margin'].includes(k)) {
        if(!Array.isArray(v) || v.length!==4 || v.some(x=>!Number.isFinite(x))) fail('Invalid spacing');
      } else if(['row','column','rowspan','columnspan'].includes(k)) {
        if(!Number.isInteger(v) || v<(k.endsWith('span')?1:0) || v>10000) fail('Invalid grid placement');
      } else if(!['width','height','weight'].includes(k) || !Number.isFinite(v) || v<0) fail('Invalid dimension');
    }
    if(['row','column','rowspan','columnspan'].some(k=>Object.hasOwn(n.layout,k)) &&
      state.nodes.get(parent)?.type!=='Grid') fail('Grid placement outside Grid');
    if(state.nodes.get(parent)?.type==='Grid' &&
      (!Object.hasOwn(n.layout,'row') || !Object.hasOwn(n.layout,'column'))) fail('Missing Grid position');
    if(n.type==='ProgressBar' && (!exact(n.props,['progress','maximum']) ||
      n.props.progress>n.props.maximum)) fail('Invalid progress range');
    for(const [k,v] of Object.entries(n.style)) {
      if(['color','background'].includes(k)) { if(!/^#[0-9a-f]{6}([0-9a-f]{2})?$/i.test(v)) fail('Invalid color'); }
      else if(['font_size_pt','font_weight'].includes(k)) {
        if(!Number.isFinite(v) && !(k==='font_weight' && ['normal','bold'].includes(v))) fail('Invalid font');
      } else if(k!=='font_family' || typeof v!=='string') fail('Invalid style');
    }
    for(const [name,token] of Object.entries(n.events))
      if(!['click','input'].includes(name) || typeof token!=='string' || !token) fail('Invalid event');
    for(const [role,a] of Object.entries(n.bindings)) {
      const slot=state.slots.get(a?.slot_token);
      if(n.type!=='TextField' || !['model','edit_model'].includes(role) ||
        !exact(a,['ref','slot_token','token','writable']) || !refValid(a.ref) || typeof a.token!=='string' || !a.token ||
        attachments.has(a.token) || typeof a.writable!=='boolean' || !slot || !refEqual(slot.ref,a.ref)) fail('Invalid attachment');
      attachments.add(a.token); usedSlots.add(a.slot_token);
    }
    if(n.type==='TextField' && !n.bindings.model) fail('Missing TextField model');
    for(const child of n.children) visit(child,id);
  }
  for(const root of state.roots) visit(root);
  if(seen.size!==state.nodes.size || usedSlots.size!==state.slots.size) fail('Orphan records');
}
function slot(state, value) {
  if(!exact(value,['ref','token','value_rev','value']) || typeof value.token!=='string' || !value.token ||
    !Number.isSafeInteger(value.value_rev) || value.value_rev<=0 ||
    !refValid(value.ref)) fail('Invalid slot');
  const old=state.slots.get(value.token);
  if(old && (!refEqual(old.ref,value.ref) || value.value_rev<old.value_rev)) fail('Slot identity changed');
  state.slots.set(value.token,copy(value));
}
export function prepare(previous, body) {
  let state;
  if(body.mode==='snapshot') {
    if(!exact(body,['mode','base_rev','rev','processed_seq','roots','bindings','canvases']) ||
      body.base_rev!==null || !Array.isArray(body.roots) || !Array.isArray(body.bindings) ||
      !Array.isArray(body.canvases) || body.canvases.length) fail('Invalid snapshot');
    state={nodes:new Map(),roots:[],slots:new Map()};
    function visit(n) {
      if(!object(n) || state.nodes.has(n.id) || !Array.isArray(n.children)) fail('Invalid snapshot node');
      const record=copy(n); record.children=n.children.map(c=>c.id); state.nodes.set(n.id,record);
      for(const child of n.children) visit(child);
    }
    for(const root of body.roots) { state.roots.push(root.id); visit(root); }
    for(const value of body.bindings) { if(state.slots.has(value.token)) fail('Duplicate slot'); slot(state,value); }
  } else {
    if(!exact(body,['mode','base_rev','rev','processed_seq','ops']) || !Array.isArray(body.ops)) fail('Invalid patch');
    state={nodes:new Map([...previous.nodes].map(([k,v])=>[k,copy(v)])),roots:previous.roots.slice(),
      slots:new Map([...previous.slots].map(([k,v])=>[k,copy(v)]))};
    const parents=new Map();
    for(const id of state.roots) parents.set(id,null);
    for(const n of state.nodes.values()) for(const id of n.children) parents.set(id,n.id);
    const siblings=parent=>parent===null?state.roots:state.nodes.get(parent)?.children;
    function remove(id) {
      const n=state.nodes.get(id); if(!n) fail('Missing removal');
      for(const child of n.children.slice()) remove(child);
      const list=siblings(parents.get(id)); if(list) list.splice(list.indexOf(id),1);
      parents.delete(id); state.nodes.delete(id);
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
      } else fail('Unsupported operation');
    }
  }
  validate(state); return state;
}

export class Renderer {
  constructor(root, actions) {
    this.root=root; this.actions=actions; this.elements=new Map(); this.drafts=new Map();
    this.state={nodes:new Map(),roots:[],slots:new Map()}; this.rev=0; this.dirty=false; this.applying=false;
  }
  make(n) {
    const e=document.createElement(tags[n.type]); e.dataset.puiId=n.id; e.className='pui-'+n.type;
    if(n.type==='Button') e.type='button';
    if(n.type==='TextField') {
      e.type='text'; e.addEventListener('input',()=>this.input(n.id));
      e.addEventListener('compositionstart',()=>{this.draft(n.id).composing=true;});
      e.addEventListener('compositionend',()=>{this.draft(n.id).composing=false;this.input(n.id);
        if(document.activeElement!==e) this.commit(n.id);});
      e.addEventListener('blur',()=>this.commit(n.id));
      e.addEventListener('keydown',event=>{if(event.key==='Enter' && !event.isComposing){this.commit(n.id);e.blur();}});
    }
    e.addEventListener('click',event=>{
      if(this.applying || this.dirty || !this.state.nodes.get(n.id)?.events.click) return;
      event.stopPropagation();
      const focused=document.activeElement?.dataset.puiId;
      if(focused && this.state.nodes.get(focused)?.type==='TextField') this.commit(focused);
      const record=this.state.nodes.get(n.id);
      this.actions('event',{node_id:n.id,event:'click',token:record.events.click,observed_render_rev:this.rev,data:{}});
    });
    if(n.type==='Label') e.addEventListener('keydown',event=>{
      if((event.key==='Enter' || event.key===' ') && this.state.nodes.get(n.id)?.events.click){event.preventDefault();e.click();}
    });
    this.elements.set(n.id,e); return e;
  }
  draft(id) {
    if(!this.drafts.has(id)) this.drafts.set(id,{editSeq:0,committed:0,editing:false,composing:false,lastSent:0,pending:null});
    return this.drafts.get(id);
  }
  input(id) {
    if(this.applying || this.dirty) return;
    const n=this.state.nodes.get(id), e=this.elements.get(id), d=this.draft(id);
    if(d.value!==e.value) {d.value=e.value;d.editSeq++;}
    d.editing=true;
    if(d.composing || d.lastSent===d.editSeq) return;
    d.lastSent=d.editSeq;
    if(n.bindings.edit_model) this.write(n,'edit_model','input',d);
    else if(n.events.input) this.actions('event',{node_id:id,event:'input',token:n.events.input,
      observed_render_rev:this.rev,data:{value:e.value,edit_seq:d.editSeq,composing:false}});
  }
  write(n,role,phase,d,onSent) {
    const a=n.bindings[role], s=this.state.slots.get(a.slot_token);
    this.actions('binding_write',{node_id:n.id,role,phase,ref:a.ref,slot_token:a.slot_token,
      attachment_token:a.token,observed_render_rev:this.rev,observed_value_rev:s.value_rev,
      edit_seq:d.editSeq,value:this.elements.get(n.id).value},onSent);
  }
  commit(id) {
    if(this.applying || this.dirty) return;
    const n=this.state.nodes.get(id); if(!n || n.type!=='TextField') return;
    const d=this.draft(id);
    if(d.composing || !d.editing || d.committed===d.editSeq) return;
    d.committed=d.editSeq;
    const pending={seq:null,editSeq:d.editSeq}; d.pending=pending;
    this.write(n,'model','commit',d,seq=>{pending.seq=seq;});
  }
  update(n) {
    const e=this.elements.get(n.id); e.style.cssText='';
    if(n.type==='Window') document.title=n.props.title || 'PUI';
    if(['Label','Button','Text'].includes(n.type)) e.textContent=n.props.text ?? '';
    if(n.type==='Label') {
      e.style.userSelect=n.props.selectable?'text':'none';
      if(n.events.click) {e.setAttribute('role','button');e.tabIndex=0;e.style.cursor='pointer';}
      else {e.removeAttribute('role');e.removeAttribute('tabindex');}
    }
    if(n.type==='Button') e.disabled=n.props.enabled===false;
    if(n.type==='TextField') e.placeholder=n.props.placeholder || '';
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
    if(n.layout.weight!==undefined) e.style.flex=n.layout.weight+' 1 0px';
    for(const name of ['padding','margin']) if(n.layout[name]) e.style[name]=n.layout[name].map(v=>v+'px').join(' ');
    for(const [name,prop] of [['color','color'],['background','backgroundColor'],['font_weight','fontWeight'],['font_family','fontFamily']])
      if(n.style[name]!==undefined) e.style[prop]=n.style[name];
    if(n.style.font_size_pt!==undefined) e.style.fontSize=n.style.font_size_pt+'pt';
  }
  place(id,parent,before) {
    const e=this.elements.get(id), p=parent===null?this.root:this.elements.get(parent), anchor=before===null?null:this.elements.get(before);
    if(e.parentNode===p && e.nextSibling===anchor) return;
    if(p.moveBefore && e.isConnected && p.isConnected) p.moveBefore(e,anchor);
    else p.insertBefore(e,anchor);
  }
  apply(body) {
    const next=prepare(this.state,body), active=document.activeElement;
    this.applying=true;
    try {
      if(body.mode==='snapshot') {
        for(const n of next.nodes.values()) {
          const old=this.elements.get(n.id);
          if(old && this.state.nodes.get(n.id)?.type!==n.type) {old.remove();this.elements.delete(n.id);}
          if(!this.elements.has(n.id)) this.make(n);
          this.update(n);
        }
        const walk=(ids,parent)=>{let before=null;for(const id of ids.slice().reverse()){this.place(id,parent,before);before=id;}
          for(const id of ids) walk(next.nodes.get(id).children,id);};
        walk(next.roots,null);
        for(const [id,e] of this.elements) if(!next.nodes.has(id)){e.remove();this.elements.delete(id);this.drafts.delete(id);}
      } else for(const op of body.ops) {
        if(op.op==='create_node') {this.make(op.node);this.update(next.nodes.get(op.node.id));}
        else if(op.op==='patch_node') this.update(next.nodes.get(op.node_id));
        else if(op.op==='place_node') this.place(op.node_id,op.parent_id,op.before_id);
        else if(op.op==='remove_node') {
          const e=this.elements.get(op.node_id);
          for(const child of [e,...e.querySelectorAll('[data-pui-id]')]) {
            this.elements.delete(child.dataset.puiId);this.drafts.delete(child.dataset.puiId);
          }
          e.remove();
        }
      }
      for(const n of next.nodes.values()) if(n.type==='TextField') {
        const e=this.elements.get(n.id); let d=this.draft(n.id);
        if(d.token!==n.bindings.model.token){this.drafts.delete(n.id);d=this.draft(n.id);d.token=n.bindings.model.token;}
        if(d.pending && d.pending.seq!==null && body.processed_seq>=d.pending.seq &&
          d.editSeq===d.pending.editSeq && !d.composing) {d.editing=false;d.pending=null;}
        if(!d.editing && !d.composing) {if(e.value!==n.props.text)e.value=n.props.text;d.value=e.value;}
      }
      if(active?.isConnected && active!==document.activeElement && document.activeElement===document.body)
        active.focus({preventScroll:true});
      this.state=next;
      this.rev=body.rev;this.dirty=false;
    } finally {this.applying=false;}
  }
}
