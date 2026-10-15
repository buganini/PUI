// Native table cells with local inline editors; values are committed by Python.
export function validateTable(p) {
  const keys=(v,names)=>v && Object.keys(v).sort().join(',')===names.split(' ').sort().join(',');
  const strings=v=>Array.isArray(v) && v.every(x=>typeof x==='string');
  if(!keys(p,'rows columns column_header row_headers autofit') || !strings(p.columns) ||
    typeof p.column_header!=='boolean' || typeof p.autofit!=='boolean' || !Array.isArray(p.rows) ||
    (p.row_headers!==null && (!strings(p.row_headers) || p.row_headers.length!==p.rows.length)) ||
    p.rows.length*p.columns.length>10000 || Math.max(p.rows.length,p.columns.length)>10000)throw Error('Invalid Table');
  const ids=new Set(),tokens=new Set();
  for(const row of p.rows) {
    if(!keys(row,'id cells') || typeof row.id!=='string' || !row.id || ids.has(row.id) ||
      !Array.isArray(row.cells) || row.cells.length!==p.columns.length)throw Error('Invalid Table row');
    ids.add(row.id);
    for(const c of row.cells) {
      if(c===null)continue;
      if(!keys(c,'token text editor value choices error') || typeof c.token!=='string' || !c.token || tokens.has(c.token) ||
        typeof c.text!=='string' || typeof c.error!=='string' || !strings(c.choices) ||
        ![null,'text','bool','choice'].includes(c.editor) ||
        (c.editor===null?c.value!==null:c.editor==='text'?typeof c.value!=='string':c.editor==='bool'?typeof c.value!=='boolean':
          c.value!==null && (!Number.isInteger(c.value) || c.value<0 || c.value>=c.choices.length)))throw Error('Invalid Table cell');
      tokens.add(c.token);
    }
  }
}

export class Tables {
  constructor(renderer) {this.renderer=renderer;this.records=new Map();}
  add(id,element) {
    const table=document.createElement('table'),head=document.createElement('thead'),body=document.createElement('tbody');
    table.append(head,body);element.append(table);
    this.records.set(id,{table,head,body,rows:new Map(),cells:new Map(),editor:null,sequence:0,widths:null});
    element.addEventListener('click',event=>this.activate(id,event,false));
    element.addEventListener('dblclick',event=>this.activate(id,event,true));
    element.addEventListener('keydown',event=>{
      if(event.target.matches('input,select'))return;
      const td=event.target.closest('td');if(!td)return;
      if(event.key==='Enter'){event.preventDefault();this.start(id,td);}
      const moves={ArrowLeft:[0,-1],ArrowRight:[0,1],ArrowUp:[-1,0],ArrowDown:[1,0]};
      if(moves[event.key]) {
        event.preventDefault();const [dr,dc]=moves[event.key],r=td.parentElement.sectionRowIndex,c=td.cellIndex;
        this.records.get(id).body.rows[r+dr]?.cells[c+dc]?.focus();
      }
    });
  }
  send(id,cell,action,value=null,done) {
    const r=this.renderer,n=r.state.nodes.get(id),s=this.records.get(id);
    if(r.applying || r.dirty || !n?.events.table)return;
    r.actions('event',{node_id:id,event:'table',token:n.events.table,observed_render_rev:r.rev,
      data:{cell,action,value,edit_seq:++s.sequence}},done);
  }
  activate(id,event,double) {
    if(this.renderer.applying || this.renderer.dirty)return;
    const td=event.target.closest('td'),s=this.records.get(id);
    if(!td || !s.body.contains(td) || !td.dataset.cell || event.target.matches('input,option'))return;
    event.stopPropagation();
    if(event.target.matches('select')) {
      this.send(id,td.dataset.cell,double?'dblclick':'click');return;
    }
    const focused=this.renderer.focusedEditor();if(focused)this.renderer.commit(focused);
    this.send(id,td.dataset.cell,double?'dblclick':'click');
    if(!double)this.start(id,td);
  }
  start(id,td) {
    const s=this.records.get(id),cell=s.cells.get(td.dataset.cell);
    if(!cell?.data.editor || s.editor?.td===td)return;
    this.commit(id);
    // An unfinished composition must stay attached until compositionend.
    if(s.editor?.composing)return;
    if(s.editor)this.finish(id);
    const c=cell.data,input=c.editor==='choice'?td.querySelector('select'):document.createElement('input');
    const error=c.editor==='choice'?td.querySelector('.pui-cell-error'):this.errorElement();
    if(c.editor!=='choice') {
      if(c.editor==='bool'){input.type='checkbox';input.checked=c.value;}
      else {input.type='text';input.value=c.value;}
      this.listen(id,td,input);
      td.replaceChildren(input,error);
    }
    s.editor={td,input,error,token:c.token,composing:false,pending:null,version:0,committed:-1};
    input.focus();if(c.editor==='text')input.select();
  }
  errorElement() {
    const error=document.createElement('span');error.className='pui-cell-error';error.setAttribute('role','alert');return error;
  }
  listen(id,td,input) {
    input.dataset.puiEditor=id;input.setAttribute('aria-label','Edit cell');
    const active=()=>{const e=this.records.get(id)?.editor;return e?.input===input?e:null;};
    if(input.tagName==='SELECT')input.addEventListener('focus',()=>this.start(id,td));
    input.addEventListener('input',()=>{const e=active();if(e)e.version++;});
    input.addEventListener('compositionstart',()=>{const e=active();if(e)e.composing=true;});
    input.addEventListener('compositionend',()=>{const e=active();if(e){e.composing=false;if(document.activeElement!==input)this.commit(id);}});
    input.addEventListener('change',()=>{
      if(input.tagName==='SELECT')this.start(id,td);
      const e=active();if(e && input.type!=='text'){e.version++;this.commit(id);}
    });
    input.addEventListener('blur',()=>{if(active())this.commit(id);});
    input.addEventListener('keydown',event=>{
      const e=active();if(!e || event.isComposing || e.composing)return;
      if(event.key==='Escape'){event.preventDefault();this.finish(id);td.focus();}
      else if(event.key==='Enter' && input.tagName!=='SELECT'){event.preventDefault();this.commit(id);}
    });
  }
  display(id,td,c) {
    if(c?.editor!=='choice'){td.textContent=c?.text || '';return;}
    let input=td.querySelector('select');
    if(!input) {
      input=document.createElement('select');this.listen(id,td,input);
      td.replaceChildren(input,this.errorElement());
    }
    // Retain the native select and its focus across acknowledged edits/redraws.
    if(input.options.length!==c.choices.length+1 || c.choices.some((label,i)=>input.options[i+1].textContent!==label)) {
      const blank=document.createElement('option');blank.value='';blank.disabled=true;blank.hidden=true;
      input.replaceChildren(blank);
      c.choices.forEach((label,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=label;input.append(option);});
    }
    input.value=c.value===null?'':String(c.value);input.disabled=false;
    input.setAttribute('aria-invalid',String(!!c.error));
    td.querySelector('.pui-cell-error').textContent=c.error;
  }
  commit(id) {
    const s=this.records.get(id),e=s?.editor;
    if(!e || e.composing || e.committed===e.version || this.renderer.applying || this.renderer.dirty)return;
    const c=s.cells.get(e.token)?.data;if(!c)return;
    const value=c.editor==='bool'?e.input.checked:c.editor==='choice'?(e.input.value===''?null:Number(e.input.value)):e.input.value;
    if(value===c.value && !c.error){this.finish(id);return;}
    e.committed=e.version;const pending=e.pending={version:e.version,seq:null,
      focus:e.input.tagName==='SELECT' && document.activeElement===e.input};
    this.send(id,e.token,'commit',value,seq=>{pending.seq=seq;});
    e.input.disabled=true;
  }
  finish(id) {
    const s=this.records.get(id),e=s?.editor;if(!e)return;
    s.editor=null;const c=s.cells.get(e.token)?.data;
    this.display(id,e.td,c);
  }
  sync(id,p,processed) {
    const s=this.records.get(id),wanted=new Set(),cells=new Map();
    const focus=s.editor?.pending?.focus && document.activeElement===document.body?s.editor.input:null;
    const heading=[...(p.row_headers===null?[]:['']),...p.columns];
    s.head.hidden=!p.column_header;
    const h=s.head.rows[0] || s.head.insertRow();
    while(h.children.length>heading.length)h.lastChild.remove();
    heading.forEach((label,i)=>{const th=h.children[i] || h.appendChild(document.createElement('th'));th.scope='col';th.textContent=label;});
    p.rows.forEach((row,r)=>{
      wanted.add(row.id);let tr=s.rows.get(row.id);
      if(!tr){tr=document.createElement('tr');s.rows.set(row.id,tr);}
      const current=s.body.children[r];if(current!==tr) {
        if(s.body.moveBefore && tr.isConnected)s.body.moveBefore(tr,current || null);else s.body.insertBefore(tr,current || null);
      }
      const offset=p.row_headers===null?0:1;
      if(offset && tr.firstElementChild?.tagName!=='TH')tr.prepend(document.createElement('th'));
      if(!offset && tr.firstElementChild?.tagName==='TH')tr.firstElementChild.remove();
      if(offset){tr.firstChild.scope='row';tr.firstChild.textContent=p.row_headers[r];}
      while(tr.children.length>offset+row.cells.length)tr.lastChild.remove();
      row.cells.forEach((c,col)=>{
        const td=tr.children[col+offset] || tr.appendChild(document.createElement('td'));
        td.tabIndex=c?0:-1;
        if(c){td.dataset.cell=c.token;cells.set(c.token,{td,data:c});}else delete td.dataset.cell;
        if(s.editor?.td===td && s.editor.token!==c?.token)this.finish(id);
        if(s.editor?.td!==td)this.display(id,td,c);
      });
    });
    for(const [key,tr] of s.rows)if(!wanted.has(key)){tr.remove();s.rows.delete(key);}
    s.cells=cells;
    const e=s.editor,c=e && cells.get(e.token)?.data;
    if(e && !c)this.finish(id);
    else if(e) {
      e.error.textContent=c.error;
      e.input.setAttribute('aria-invalid',String(!!c.error));
      if(e.pending?.seq!==null && e.pending && processed>=e.pending.seq) {
        if(c.error){e.pending=null;e.committed=-1;e.input.disabled=false;e.input.focus();}
        else if(e.version===e.pending.version && !e.composing)this.finish(id);
      }
    }
    if(p.autofit){s.table.style.tableLayout='auto';s.table.style.width='';s.widths=null;}
    else {
      const count=heading.length;
      if(!s.widths || s.widths.length!==count) {
        s.table.style.tableLayout='auto';s.table.style.width='';
        s.widths=[...h.children].map(th=>Math.max(20,th.getBoundingClientRect().width));
      }
      s.table.style.tableLayout='fixed';s.table.style.width=s.widths.reduce((a,b)=>a+b,0)+'px';
      [...h.children].forEach((th,i)=>{th.style.width=s.widths[i]+'px';});
    }
    if(p.autofit)for(const th of h.children)th.style.width='';
    if(focus?.isConnected && !focus.disabled && document.activeElement===document.body)focus.focus();
  }
  remove(id){this.records.delete(id);}
}
