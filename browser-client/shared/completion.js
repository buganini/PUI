// Input keeps focus; candidates are independent of the server's complete option set.
export class Completion {
  constructor(renderer,id,input,list) {
    this.renderer=renderer;this.id=id;this.input=input;this.list=list;this.active=-1;this.all=false;
    this.popup=document.createElement('div');this.popup.id='pui-completion-'+id;
    this.popup.setAttribute('role','listbox');this.popup.hidden=true;
    this.popup.style.cssText='position:fixed;z-index:2147483647;overflow:auto;box-sizing:border-box;border:1px solid GrayText;max-height:240px';
    document.body.append(this.popup);
    input.setAttribute('role','combobox');input.setAttribute('aria-autocomplete','list');
    input.setAttribute('aria-controls',this.popup.id);input.setAttribute('aria-expanded','false');input.autocomplete='off';
    input.addEventListener('input',()=>{if(!renderer.draft(id).composing)this.refresh(true,false);});
    input.addEventListener('compositionstart',()=>this.hide());
    input.addEventListener('compositionend',()=>queueMicrotask(()=>{if(input.isConnected && document.activeElement===input)this.refresh(true,false);}));
    input.addEventListener('blur',()=>this.hide());
    input.addEventListener('keydown',event=>this.key(event));
    this.popup.addEventListener('pointerdown',event=>{if(event.button===0 && event.target.closest('[role=option]'))event.preventDefault();});
    this.popup.addEventListener('click',event=>{const option=event.target.closest('[role=option]');if(option)this.choose(Number(option.dataset.index));});
    this.reposition=()=>{if(!this.popup.hidden)this.position();};
    window.addEventListener('resize',this.reposition);document.addEventListener('scroll',this.reposition,true);
  }
  refresh(show=false,all=this.all) {
    if(show)this.all=all;
    const n=this.renderer.state.nodes.get(this.id);
    if(this.renderer.dirty || !n?.props.editable || (n.props.autoexpand===false && !this.all) || n.props.disabled || this.renderer.draft(this.id).composing){this.hide();return;}
    if(!show && this.popup.hidden)return;
    const words=this.input.value.trim().toLowerCase().split(/\s+/u);
    this.items=Array.from(this.list.children).filter(option=>this.all || words.some(word=>option.textContent.toLowerCase().includes(word)));
    const signature=JSON.stringify(this.items.map(item=>[item.dataset.puiId,item.textContent]));
    if(!show && signature===this.signature){this.position();return;}
    this.signature=signature;
    this.active=-1;this.input.removeAttribute('aria-activedescendant');this.popup.replaceChildren();
    this.items.forEach((item,index)=>{const option=document.createElement('div');option.id=this.popup.id+'-'+index;option.setAttribute('role','option');option.setAttribute('aria-selected','false');option.dataset.index=index;option.textContent=item.textContent;option.style.padding='4px 8px';this.popup.append(option);});
    this.popup.hidden=!this.items.length;this.input.setAttribute('aria-expanded',String(!this.popup.hidden));this.position();
  }
  position() {
    const rect=this.input.getBoundingClientRect(),style=getComputedStyle(this.input);
    Object.assign(this.popup.style,{font:style.font,color:style.color,backgroundColor:style.backgroundColor,width:rect.width+'px',left:Math.max(0,Math.min(rect.left,innerWidth-rect.width))+'px'});
    const height=this.popup.offsetHeight;
    this.popup.style.top=(rect.bottom+height>innerHeight?Math.max(0,rect.top-height):rect.bottom)+'px';
  }
  key(event) {
    if(event.isComposing || event.keyCode===229)return;
    if(this.popup.hidden) {
      if(event.key==='ArrowDown')this.refresh(true);
      if(this.popup.hidden)return;
    }
    if(event.key==='ArrowDown' || event.key==='ArrowUp') {
      event.preventDefault();event.stopImmediatePropagation();
      this.active=this.active<0?(event.key==='ArrowDown'?0:this.items.length-1):(this.active+(event.key==='ArrowDown'?1:-1)+this.items.length)%this.items.length;
      Array.from(this.popup.children).forEach((e,i)=>{e.setAttribute('aria-selected',String(i===this.active));e.style.background=i===this.active?'Highlight':'';e.style.color=i===this.active?'HighlightText':'';});
      const active=this.popup.children[this.active];this.input.setAttribute('aria-activedescendant',active.id);active.scrollIntoView({block:'nearest'});
    } else if(event.key==='Enter' && this.active>=0) {
      event.preventDefault();event.stopImmediatePropagation();this.choose(this.active);
    } else if(event.key==='Escape') {
      event.preventDefault();event.stopImmediatePropagation();this.hide();
    } else if(event.key==='Tab')this.hide();
  }
  choose(index) {
    const item=this.items?.[index];if(!item?.isConnected || !this.list.contains(item))return;
    this.input.value=item.textContent;this.renderer.input(this.id);this.hide();this.renderer.commit(this.id);this.input.focus();
  }
  hide() {this.popup.hidden=true;this.active=-1;this.input.setAttribute('aria-expanded','false');this.input.removeAttribute('aria-activedescendant');}
  destroy() {this.popup.remove();window.removeEventListener('resize',this.reposition);document.removeEventListener('scroll',this.reposition,true);}
}
