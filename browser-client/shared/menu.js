// Native popovers keep dropdowns above clipped Window/Scroll content. Their
// nested DOM ownership gives outside-click and Escape dismissal to the browser.
export class Menus {
  constructor(renderer) {
    this.r=renderer;this.items=new Map();this.abort=new AbortController();
    window.addEventListener('resize',()=>this.closeAll(),{signal:this.abort.signal});
    document.addEventListener('scroll',event=>{
      if(!event.target.closest?.('.pui-menu-popup'))this.closeAll();
    },{capture:true,signal:this.abort.signal});
  }
  button(id) {return this.items.get(id)?.button || this.r.elements.get(id);}
  parent(id) {return [...this.r.state.nodes.values()].find(n=>n.children.includes(id));}
  entries(parent) {
    return (parent?.children || []).filter(id=>{
      const n=this.r.state.nodes.get(id),e=this.r.elements.get(id);
      return n && !n.props.disabled && n.layout.visible!==false && e && !e.hidden;
    });
  }
  top(id) {
    let parent=this.parent(id);
    while(parent?.type==='Menu'){id=parent.id;parent=this.parent(id);}
    return id;
  }
  closeAll() {
    for(const {popup} of [...this.items.values()].reverse())
      if(popup.matches(':popover-open'))popup.hidePopover();
  }
  make(n,e) {
    if(n.type==='MenuBar') {e.setAttribute('role','menubar');e.setAttribute('aria-label','Application menu');return;}
    let button=e;
    if(n.type==='Menu') {
      e.setAttribute('role','none');
      button=document.createElement('button');button.type='button';
      const popup=document.createElement('div');popup.popover='auto';
      popup.className='pui-menu-popup';popup.id='pui-menu-'+n.id;
      popup.setAttribute('role','menu');button.id='pui-menu-button-'+n.id;
      popup.setAttribute('aria-labelledby',button.id);
      button.setAttribute('aria-haspopup','menu');button.setAttribute('aria-expanded','false');
      button.setAttribute('aria-controls',popup.id);e.append(button,popup);
      this.items.set(n.id,{button,popup});
      popup.addEventListener('toggle',()=>button.setAttribute('aria-expanded',String(popup.matches(':popover-open'))));
      button.addEventListener('click',event=>{
        event.stopPropagation();
        if(popup.matches(':popover-open'))popup.hidePopover();else this.open(n.id);
      });
    } else {
      e.addEventListener('click',()=>{
        if(e.disabled)return;
        const top=this.top(n.id);this.closeAll();this.button(top)?.focus();
      });
    }
    button.setAttribute('role','menuitem');button.tabIndex=-1;
    button.addEventListener('keydown',event=>this.key(n.id,event));
  }
  update(n) {
    const {button}=this.items.get(n.id);button.textContent=n.props.text;
    button.setAttribute('aria-label',n.props.text);
  }
  open(id,last=false) {
    if(this.r.applying || this.r.dirty)return;
    const item=this.items.get(id);if(!item)return;
    const {button,popup}=item;
    // Opening a sibling closes only its subtree, preserving ancestor popovers.
    const parent=this.parent(id);
    for(const sibling of parent?.children || [])if(sibling!==id) {
      const other=this.items.get(sibling)?.popup;
      if(other?.matches(':popover-open'))other.hidePopover();
    }
    popup.showPopover();
    const rect=button.getBoundingClientRect(),nested=parent?.type==='Menu';
    const width=popup.offsetWidth,height=popup.offsetHeight;
    let left=nested?rect.right:rect.left,top=nested?rect.top:rect.bottom;
    if(left+width>innerWidth-4)left=nested?rect.left-width:innerWidth-width-4;
    if(top+height>innerHeight-4)top=nested?innerHeight-height-4:rect.top-height;
    popup.style.left=Math.max(4,left)+'px';popup.style.top=Math.max(4,top)+'px';
    button.setAttribute('aria-expanded','true');
    const entries=this.entries(this.r.state.nodes.get(id));
    this.button(last?entries.at(-1):entries[0])?.focus();
  }
  key(id,event) {
    const parent=this.parent(id),topLevel=parent?.type==='MenuBar',key=event.key;
    const entries=this.entries(parent),index=entries.indexOf(id);
    const focus=index=>this.button(entries[(index+entries.length)%entries.length])?.focus();
    if(key==='Tab') {this.button(this.top(id))?.focus();this.closeAll();return;}
    if(key==='Escape') {
      event.preventDefault();event.stopPropagation();
      const owner=topLevel?id:parent?.id,popup=this.items.get(owner)?.popup;
      if(popup?.matches(':popover-open'))popup.hidePopover();
      this.button(owner)?.focus();return;
    }
    if(key==='Home' || key==='End')focus(key==='Home'?0:entries.length-1);
    else if(topLevel && (key==='ArrowRight' || key==='ArrowLeft')) {
      const open=[...this.items.values()].some(item=>item.popup.matches(':popover-open'));
      this.closeAll();const next=(index+(key==='ArrowRight'?1:-1)+entries.length)%entries.length;
      focus(next);if(open)this.open(entries[next]);
    } else if(topLevel && (key==='ArrowDown' || key==='ArrowUp'))this.open(id,key==='ArrowUp');
    else if(!topLevel && (key==='ArrowDown' || key==='ArrowUp'))focus(index+(key==='ArrowDown'?1:-1));
    else if(!topLevel && key==='ArrowRight' && this.items.has(id))this.open(id);
    else if(!topLevel && key==='ArrowLeft') {
      this.items.get(parent.id)?.popup.hidePopover();this.button(parent.id)?.focus();
    } else return; // Native button activation handles Enter and Space.
    event.preventDefault();event.stopPropagation();
  }
  sync() {
    for(const n of this.r.state.nodes.values())if(n.type==='MenuBar') {
      const entries=this.entries(n),active=entries.find(id=>this.button(id)===document.activeElement);
      for(const id of n.children)this.button(id).tabIndex=id===(active || entries[0])?0:-1;
    }
    for(const [id,{popup}] of this.items) {
      let node=this.r.state.nodes.get(id),visible=true;
      while(node){if(node.layout.visible===false)visible=false;node=this.parent(node.id);}
      if(!visible && popup.matches(':popover-open'))popup.hidePopover();
    }
  }
  remove(id) {
    const popup=this.items.get(id)?.popup;
    if(popup?.matches(':popover-open'))popup.hidePopover();
    this.items.delete(id);
  }
  destroy() {this.closeAll();this.abort.abort();}
}
