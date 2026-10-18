// File contents travel separately from ordinary input/render envelopes.
export class Drops {
  constructor(renderer){this.r=renderer;this.pending=new Set();this.upload=null;this.limits=null;}
  stop(){for(const c of this.pending)c.abort();this.pending.clear();}
  result(body){if(!body.accepted)alert(body.reason);}
  event(n,event,data){this.r.actions('event',{node_id:n.id,event,token:n.events[event],observed_render_rev:this.r.rev,data});}
  update(n,e){
    const current=()=>this.r.state.nodes.get(n.id);
    const point=ev=>{const b=e.getBoundingClientRect();return {x:ev.clientX-b.left,y:ev.clientY-b.top};};
    e.ondragenter=ev=>{
      const node=current();if(this.r.dirty || !node?.events.drop || node.props.disabled)return;
      ev.preventDefault();ev.stopPropagation();
      if(node.events.dragEnter)this.event(node,'dragEnter',point(ev));
    };
    e.ondragover=ev=>{
      const node=current();if(this.r.dirty || !node?.events.drop || node.props.disabled)return;
      // External files are never moved/deleted by a browser upload.
      if(!['all','uninitialized','copy','copyMove','copyLink'].includes(ev.dataTransfer.effectAllowed))return;
      ev.preventDefault();ev.stopPropagation();ev.dataTransfer.dropEffect='copy';
    };
    e.ondrop=async ev=>{
      const node=current();if(this.r.dirty || !node?.events.drop || node.props.disabled)return;
      ev.preventDefault();ev.stopPropagation();
      const c=new AbortController();this.pending.add(c);
      try {
        if(!['all','uninitialized','copy','copyMove','copyLink'].includes(ev.dataTransfer.effectAllowed))throw Error('Source does not allow copying');
        const files=Array.from(ev.dataTransfer.files),items=Array.from(ev.dataTransfer.items);
        if(items.some(i=>i.webkitGetAsEntry?.()?.isDirectory))throw Error('Dropping directories is not supported');
        const data={...point(ev),upload_id:null,text:ev.dataTransfer.getData('text/plain')||null,
          urls:ev.dataTransfer.getData('text/uri-list').split(/\r?\n/).filter(s=>s && !s.startsWith('#'))};
        const invalid=files.filter(f=>node.props.drop_extensions && !node.props.drop_extensions.some(x=>f.name.toLowerCase().endsWith(x)));
        if(invalid.length)throw Error('Unsupported file extension: '+invalid.map(f=>f.name).join(', '));
        if(files.length){
          const l=this.limits;
          if(!l || !this.upload)throw Error('Uploads are not ready');
          if(files.length>l.max_files || files.some(f=>f.size>l.max_file_bytes) || files.reduce((s,f)=>s+f.size,0)>l.max_session_bytes)throw Error('Upload limit exceeded');
          data.upload_id=await this.upload(files,node,c.signal);
        }
        if(c.signal.aborted)return;
        // The worker validates the original token even if this target vanished in transit.
        this.event(node,'drop',data);
      } catch(error){if(!c.signal.aborted)alert(error.message);}
      finally{this.pending.delete(c);}
    };
  }
}
