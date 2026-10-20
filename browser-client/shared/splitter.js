// Pane sizes are client UI state. Ordinary server redraws retain the ratios.
export class Splitter {
  constructor(renderer, element) {
    this.renderer=renderer;this.element=element;this.handles=[];this.weights=[];
  }
  sync(node) {
    const ids=node.children.filter(id=>!this.renderer.elements.get(id).hidden);
    const signature=JSON.stringify([node.props.vertical,ids]);
    if(signature!==this.signature) {
      for(const handle of this.handles)handle.remove();
      this.drag=null;this.handles=[];this.weights=ids.map(()=>1);
      this.signature=signature;this.ids=ids;this.vertical=node.props.vertical;
      for(let index=0;index<ids.length-1;index++) {
        const handle=document.createElement('div');handle.className='pui-splitter-handle';
        handle.tabIndex=0;handle.setAttribute('role','separator');
        handle.setAttribute('aria-label',`Resize panes ${index+1} and ${index+2}`);
        handle.setAttribute('aria-orientation',this.vertical?'horizontal':'vertical');
        handle.setAttribute('aria-valuemin','0');handle.setAttribute('aria-valuemax','100');
        const pane=this.renderer.elements.get(ids[index]);pane.after(handle);
        handle.addEventListener('pointerdown',event=>{
          if(event.button!==0)return;
          event.preventDefault();event.stopPropagation();handle.focus();
          const [left,right]=this.sizes(index);
          this.drag={index,start:this.coordinate(event),left,total:left+right,
                     weight:this.weights[index]+this.weights[index+1]};
          handle.setPointerCapture(event.pointerId);
        });
        handle.addEventListener('pointermove',event=>{
          if(this.drag?.index!==index || !handle.hasPointerCapture(event.pointerId))return;
          const d=this.drag;this.resize(index,d.left+this.coordinate(event)-d.start,d.total,d.weight);
        });
        handle.addEventListener('pointerup',event=>{
          if(handle.hasPointerCapture(event.pointerId))handle.releasePointerCapture(event.pointerId);
          this.drag=null;
        });
        handle.addEventListener('lostpointercapture',()=>{this.drag=null;});
        handle.addEventListener('keydown',event=>{
          const negative=this.vertical?'ArrowUp':'ArrowLeft',positive=this.vertical?'ArrowDown':'ArrowRight';
          if(![negative,positive,'Home','End'].includes(event.key))return;
          event.preventDefault();event.stopPropagation();
          const [left,right]=this.sizes(index),total=left+right;
          const desired=event.key==='Home'?1:event.key==='End'?total-1:
            left+(event.key===negative?-1:1)*(event.shiftKey?50:10);
          this.resize(index,desired,total,this.weights[index]+this.weights[index+1]);
        });
        this.handles.push(handle);
      }
    }
    // Snapshot reconciliation may move panes around retained local handles.
    this.ids.forEach((id,index)=>{
      const pane=this.renderer.elements.get(id),handle=this.handles[index];
      if(handle && pane.nextSibling!==handle)pane.after(handle);
    });
    this.element.dataset.puiDirection=this.vertical?'vertical':'horizontal';
    this.element.style.flexDirection=this.vertical?'column':'row';
    this.apply();
  }
  coordinate(event) {return this.vertical?event.clientY:event.clientX;}
  sizes(index) {
    return this.ids.slice(index,index+2).map(id=>{
      const bounds=this.renderer.elements.get(id).getBoundingClientRect();
      return this.vertical?bounds.height:bounds.width;
    });
  }
  resize(index,size,total,weight) {
    if(total<=2)return;
    const fraction=Math.max(1,Math.min(total-1,size))/total;
    this.weights[index]=weight*fraction;this.weights[index+1]=weight*(1-fraction);
    this.apply();
  }
  apply() {
    this.ids.forEach((id,index)=>{this.renderer.elements.get(id).style.flex=`${this.weights[index]} 1 0px`;});
    this.handles.forEach((handle,index)=>handle.setAttribute('aria-valuenow',
      String(Math.round(100*this.weights[index]/(this.weights[index]+this.weights[index+1])))));
  }
}
