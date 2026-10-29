import { Renderer } from './dom.js';
import { validateApplicationBody } from './schema.js';

// Transport supplies sequence numbers and lifecycle; this controller owns UI credit.
export class Controller {
  constructor(root,{send,sentSequence,report,onApplied,onError,onOverflow,resources,RendererClass=Renderer}) {
    Object.assign(this,{root,send,sentSequence,report,onApplied,onError,onOverflow});
    this.pending=new Set();this.queue=[];this.ready=false;
    this.actionLimit=64;this.awaitingSnapshot=true;this.recoveryCount=0;
    this.renderer=new RendererClass(root,(type,body,onSent)=>this.action(type,body,onSent),
      (type,body)=>{
        if(this.ready && !this.renderer.dirty){try{this.send(type,body);}catch(error){this.onError(error);}}
      },onError,resources);
    root.inert=true;
  }
  stop() {
    this.ready=false;this.root.inert=true;this.queue=[];this.pending.clear();
    this.renderer.drops?.stop();
    this.renderer.dirty=true;
  }
  reset() {
    this.stop();
    this.renderer.drafts.clear();this.renderer.controlEdits.clear();this.renderer.rev=0;
    this.awaitingSnapshot=true;this.recoveryCount=0;this.renderer.canvases.reset();
    this.renderer.resetSizes?.();
    this.renderer.trees?.reset();
  }
  activate(limit=64) {this.actionLimit=Math.min(64,limit);this.ready=true;}
  action(type,body,onSent) {
    if(!this.ready || this.renderer.dirty)return;
    const action={type,body,onSent};
    if(this.queue.length>=256){this.onOverflow();return;}
    this.queue.push(action);
    try{this.drain();}catch(error){this.onError(error);}
  }
  drain() {
    while(this.ready && this.pending.size<this.actionLimit && this.queue.length) {
      const a=this.queue.shift(),n=this.send(a.type,a.body);this.pending.add(n);
      a.onSent?.(n);
    }
  }
  result(body) {
    validateApplicationBody('result',body);
    if(!this.pending.delete(body.reply_to))throw new Error('Result does not match a pending action');
    this.drain();
  }
  render(body) {
    validateApplicationBody('render',body);
    const r=this.renderer,b=body;
    if(b.processed_seq>this.sentSequence())throw new Error('Render confirms an unsent action');
    if(!r.dirty && b.rev===r.rev){this.send('ack',{render_rev:b.rev,applied_rev:r.rev,status:'applied'});return;}
    // An obsolete patch/snapshot cannot repair a dirty DOM or spend recovery credit.
    if(b.rev<r.rev || (r.dirty && (b.rev===r.rev || (this.recoveryCount>0 && b.mode==='patch')))) {
      this.send('ack',{render_rev:b.rev,applied_rev:r.rev,status:'discarded'});return;
    }
    try {
      if((b.mode==='snapshot' && !this.awaitingSnapshot) ||
        (b.mode==='patch' && (r.dirty || b.base_rev!==r.rev || b.rev<=b.base_rev)))
        throw new Error('Render base mismatch');
      r.apply(b);this.awaitingSnapshot=false;this.recoveryCount=0;
      this.send('ack',{render_rev:b.rev,applied_rev:r.rev,status:'applied'});
      this.onApplied();this.root.inert=false;
    } catch(error) {
      r.dirty=true;this.awaitingSnapshot=true;this.report('Recovering view…');
      this.send('ack',{render_rev:b.rev,applied_rev:r.rev,status:'discarded'});
      if(++this.recoveryCount>3)throw error;
      this.send('resync',{last_applied_rev:r.rev});
    }
  }
}
