// Retained single-column tree, shared by Web and Pyodide. No HTML labels.
export function validateTree(p) {
  const exact=(o,keys)=>o && !Array.isArray(o) && Object.keys(o).sort().join(',')===keys.sort().join(',');
  const positive=n=>Number.isSafeInteger(n) && n>0;
  if(!exact(p,['nodes','expanded','selected','expandable']) || !Array.isArray(p.nodes) || p.nodes.length>10000 ||
     !Array.isArray(p.expanded) || typeof p.expandable!=='boolean')throw Error('Invalid Tree');
  const ids=new Set([0]),parents=new Set();
  for(const n of p.nodes) {
    if(!exact(n,['id','parent','text']) || !positive(n.id) || ids.has(n.id) || !ids.has(n.parent) || typeof n.text!=='string')throw Error('Invalid Tree node');
    ids.add(n.id);parents.add(n.parent);
  }
  if(new Set(p.expanded).size!==p.expanded.length || p.expanded.some(k=>!positive(k) || !ids.has(k) || !parents.has(k)) ||
     (p.selected!==null && (!positive(p.selected) || !ids.has(p.selected))))throw Error('Invalid Tree state');
}

export class Trees {
  constructor(renderer) {this.renderer=renderer;this.records=new Map();}
  add(id,element) {
    const s={element,rows:new Map(),pending:[],props:null,token:null,focus:null,search:'',searched:0};
    this.records.set(id,s);element.setAttribute('role','tree');element.tabIndex=0;
    element.addEventListener('click',e=>this.click(id,e,false));
    element.addEventListener('dblclick',e=>this.click(id,e,true));
    element.addEventListener('keydown',e=>this.key(id,e));
    element.addEventListener('focusin',e=>{const row=e.target.closest('[data-tree-item]');if(row)s.focus=Number(row.dataset.treeItem);});
  }
  remove(id) {this.records.delete(id);}
  reset() {for(const s of this.records.values())s.pending=[];}
  sync(n,processed) {
    const s=this.records.get(n.id);
    if(s.token!==n.events.tree)s.pending=[];
    s.token=n.events.tree;s.props=n.props;
    s.pending=s.pending.filter(a=>a.seq===null || a.seq>processed);
    this.render(s);
  }
  state(s) {
    const nodes=new Map(s.props.nodes.map(n=>[n.id,n])),expanded=new Set(s.props.expanded);
    let selected=s.props.selected;
    for(const a of s.pending)if(nodes.has(a.item)) {
      if(a.action==='expanded')expanded.add(a.item);
      else if(a.action==='collapsed')expanded.delete(a.item);
      else selected=a.item;
    }
    const visible=[],shown=new Set([0]),depth=new Map([[0,-1]]),children=new Map();
    for(const n of nodes.values()) {
      if(!children.has(n.parent))children.set(n.parent,[]);
      children.get(n.parent).push(n.id);
      depth.set(n.id,depth.get(n.parent)+1);
      if(shown.has(n.parent) && (!n.parent || expanded.has(n.parent))){visible.push(n.id);shown.add(n.id);}
    }
    return {nodes,expanded,selected,visible,depth,children};
  }
  render(s) {
    if(!s.props)return;
    const v=this.state(s),hadFocus=s.element.contains(document.activeElement);
    for(const [key,row] of s.rows)if(!v.nodes.has(key)){row.remove();s.rows.delete(key);}
    let focus=s.focus ?? v.selected;
    while(focus && !v.visible.includes(focus))focus=v.nodes.get(focus)?.parent;
    s.focus=focus || (v.visible.includes(v.selected)?v.selected:v.visible[0]) || null;
    s.element.tabIndex=v.visible.length?-1:0;
    let previous=null;
    for(const key of v.visible) {
      const n=v.nodes.get(key),branch=v.children.has(key);
      let row=s.rows.get(key);
      if(!row){
        row=document.createElement('div');row.className='pui-tree-row';row.dataset.treeItem=key;row.setAttribute('role','treeitem');
        const arrow=document.createElement('span');arrow.dataset.treeToggle='';arrow.className='pui-tree-arrow';arrow.setAttribute('aria-hidden','true');
        const label=document.createElement('span');label.className='pui-tree-label';row.append(arrow,label);s.rows.set(key,row);
      }
      row.hidden=false;row.tabIndex=key===s.focus?0:-1;
      row.style.paddingInlineStart=`${v.depth.get(key)*20}px`;
      row.setAttribute('aria-level',v.depth.get(key)+1);
      row.setAttribute('aria-posinset',v.children.get(n.parent).indexOf(key)+1);
      row.setAttribute('aria-setsize',v.children.get(n.parent).length);
      row.setAttribute('aria-selected',key===v.selected?'true':'false');
      if(branch)row.setAttribute('aria-expanded',v.expanded.has(key)?'true':'false');else row.removeAttribute('aria-expanded');
      row.firstChild.textContent=branch?(v.expanded.has(key)?'▾':'▸'):'';
      row.firstChild.style.visibility=branch?'visible':'hidden';row.lastChild.textContent=n.text;
      const before=previous?previous.nextSibling:s.element.firstChild;
      if(row!==before)s.element.insertBefore(row,before);
      previous=row;
    }
    const visible=new Set(v.visible);
    for(const [key,row] of s.rows)if(!visible.has(key))row.hidden=true;
    if(hadFocus)(s.rows.get(s.focus) || s.element).focus({preventScroll:true});
  }
  send(id,item,action) {
    const r=this.renderer,s=this.records.get(id),n=r.state.nodes.get(id);
    if(r.applying || r.dirty || !n?.events.tree)return;
    const v=this.state(s);
    if(!v.nodes.has(item))return;
    if(['expanded','collapsed'].includes(action) && (!s.props.expandable || !v.children.has(item)))return;
    const editor=r.focusedEditor();if(editor)r.commit(editor);
    const pending={item,action,seq:null};s.pending.push(pending);
    r.actions('event',{node_id:id,event:'tree',token:n.events.tree,observed_render_rev:r.rev,data:{item,action}},seq=>{pending.seq=seq;});
    this.render(s);
  }
  focus(s,key) {s.focus=key;this.render(s);const row=s.rows.get(key);row?.focus({preventScroll:true});row?.scrollIntoView({block:'nearest',inline:'nearest'});}
  click(id,e,double) {
    const s=this.records.get(id),row=e.target.closest('[data-tree-item]');
    if(!row || !s.element.contains(row) || this.renderer.dirty || this.renderer.applying)return;
    e.stopPropagation();const item=Number(row.dataset.treeItem),v=this.state(s);
    this.focus(s,item);
    if(e.target.closest('[data-tree-toggle]')) {
      if(!double)this.send(id,item,v.expanded.has(item)?'collapsed':'expanded');
    } else {
      this.send(id,item,double?'dblclicked':'clicked');
      if(double && v.children.has(item))this.send(id,item,v.expanded.has(item)?'collapsed':'expanded');
    }
  }
  key(id,e) {
    const s=this.records.get(id);if(!s.props || e.ctrlKey || e.metaKey || e.altKey || this.renderer.dirty || this.renderer.applying)return;
    const v=this.state(s),current=v.visible.includes(s.focus)?s.focus:v.visible[0];if(!current)return;
    let target=current,action='selected';const i=v.visible.indexOf(current);
    switch(e.key) {
      case 'ArrowDown':target=v.visible[Math.min(i+1,v.visible.length-1)];break;
      case 'ArrowUp':target=v.visible[Math.max(0,i-1)];break;
      case 'Home':target=v.visible[0];break;
      case 'End':target=v.visible.at(-1);break;
      case 'ArrowRight':if(v.children.has(current)){if(v.expanded.has(current))target=v.children.get(current)[0];else action='expanded';}break;
      case 'ArrowLeft':if(v.expanded.has(current))action='collapsed';else target=v.nodes.get(current).parent || current;break;
      case 'Enter':case ' ':action='clicked';break;
      default:
        if(e.key.length!==1)return;
        const now=Date.now();s.search=(now-s.searched<700?s.search:'')+e.key.toLocaleLowerCase();s.searched=now;
        target=[...v.visible.slice(i+1),...v.visible.slice(0,i+1)].find(k=>v.nodes.get(k).text.toLocaleLowerCase().startsWith(s.search));
        if(!target)return;
    }
    e.preventDefault();e.stopPropagation();this.send(id,target,action);
    if(action==='clicked' && v.children.has(target))this.send(id,target,v.expanded.has(target)?'collapsed':'expanded');
    this.focus(s,target);
  }
}
