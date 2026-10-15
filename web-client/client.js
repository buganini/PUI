import { initializeCodec, encodeMessage, decodeMessage, StreamDecoder } from './protocol.js';
import { Renderer } from './dom.js';
import { validateServerBody } from './messages.js';
export { initializeCodec, encodeMessage, decodeMessage, StreamDecoder };
export { validateServerBody };
export { Renderer };

export async function start(root) {
  const status=document.querySelector('#pui-status');
  const storageKey='pui:resume:'+location.pathname;
  let ws, epoch=null, seq=0, serverSeq=0, pending=new Set(), queue=[], ready=false;
  let attempt=0, awaitingSnapshot=true, recoveryCount=0, generation=0;
  let actionLimit=64, stopped=false, downstream=null;
  const report=text=>{status.textContent=text;status.hidden=false;};
  const stop=code=>{stopped=true;ready=false;queue=[];pending.clear();downstream?.close();ws?.close(code);};
  const send=(type,body)=>{
    if(!ws || ws.readyState!==WebSocket.OPEN) throw new Error('Connection is not open');
    const sent=++seq; ws.send(encodeMessage({v:1,type,session:type==='hello'?null:epoch,seq:sent,body}));return sent;
  };
  const drain=()=>{while(ready && pending.size<actionLimit && queue.length){const a=queue.shift();
    const n=send(a.type,a.body);pending.add(n);a.onSent?.(n);}};
  const renderer=new Renderer(root,(type,body,onSent)=>{
    if(!ready || renderer.dirty) return;
    if(queue.length>=256){report('Input queue is full; reload to continue.');stop(4008);return;}
    queue.push({type,body,onSent});
    try{drain();}catch(error){fatal(error);}
  },(type,body)=>{
    if(ready && !renderer.dirty){try{send(type,body);}catch(error){fatal(error);}}
  },error=>fatal(error));
  const fatal=error=>{if(stopped)return;console.error(error);report('Connection error: '+error.message);stop(4002);};
  await initializeCodec();
  function connect() {
    const current=++generation;
    downstream?.close();
    const decoder=downstream=new StreamDecoder();
    ready=false;stopped=false;epoch=null;seq=serverSeq=0;pending.clear();queue=[];
    renderer.drafts.clear();renderer.controlEdits.clear();renderer.rev=0;renderer.dirty=true;awaitingSnapshot=true;recoveryCount=0;
    renderer.canvases.reset();
    const url=new URL(root.dataset.ws,location.href);
    if(url.protocol==='http:')url.protocol='ws:';if(url.protocol==='https:')url.protocol='wss:';
    ws=new WebSocket(url,'pui.v1.msgpack.zstd-stream');ws.binaryType='arraybuffer';
    let ordered=Promise.resolve();
    ws.onopen=()=>send('hello',{client_build:root.dataset.build,
      capabilities:['render.snapshot','render.patch','binding.object_id','canvas.geometry','canvas.text','canvas.input','canvas.path','canvas.image'],
      viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},
      resume_id:sessionStorage.getItem(storageKey)});
    ws.onmessage=event=>{ordered=ordered.then(()=>{
      if(current!==generation || stopped)return;
      const m=decoder.decode(new Uint8Array(event.data));
      validateServerBody(m.type,m.body);
      if(m.seq!==serverSeq+1)throw new Error('Server sequence mismatch');serverSeq=m.seq;
      if(m.type==='ready') {
        if(epoch!==null || m.seq!==1 || m.body.server_build!==root.dataset.build)throw new Error('Invalid ready');
        epoch=m.session;sessionStorage.setItem(storageKey,m.body.resume_id);ready=true;attempt=0;
        actionLimit=Math.min(64,m.body.limits.max_pending_actions);
        report(m.body.resumed?'Connected · session resumed':'Connected');return;
      }
      if(!ready || m.session!==epoch)throw new Error('Session mismatch');
      if(m.type==='result'){
        if(!pending.delete(m.body.reply_to))throw new Error('Result does not match a pending action');
        drain();return;
      }
      if(m.type==='error')throw new Error(m.body.message);
      if(m.type==='close'){report(m.body.reason);stop(1000);return;}
      if(m.type!=='render')throw new Error('Unsupported server message');
      const b=m.body;
      if(b.processed_seq>seq)throw new Error('Render confirms an unsent action');
      if(!renderer.dirty && b.rev===renderer.rev){send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'applied'});return;}
      // A dirty DOM cannot be repaired by an old snapshot or another patch.
      // Repeated in-flight renders do not consume snapshot recovery attempts.
      if(b.rev<renderer.rev || (renderer.dirty && (b.rev===renderer.rev ||
          (recoveryCount>0 && b.mode==='patch')))){
        send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'discarded'});return;
      }
      try {
        if((b.mode==='snapshot' && !awaitingSnapshot) ||
          (b.mode==='patch' && (renderer.dirty || b.base_rev!==renderer.rev || b.rev<=b.base_rev)))
          throw new Error('Render base mismatch');
        renderer.apply(b);awaitingSnapshot=false;recoveryCount=0;
        send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'applied'});
        status.hidden=true;
      } catch(error) {
        renderer.dirty=true;awaitingSnapshot=true;
        report('Recovering view…');
        send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'discarded'});
        if(++recoveryCount>3)throw error;
        send('resync',{last_applied_rev:renderer.rev});
      }
    }).catch(fatal);};
    ws.onclose=event=>{
      decoder.close();
      if(current!==generation)return;
      const wasStopped=stopped;stopped=true;
      ready=false;renderer.dirty=true;queue=[];pending.clear();
      if(wasStopped)return;
      if(event.code===1008 && event.reason.includes('Session already has a connection')){
        report('Reconnecting with a new session…');
        sessionStorage.removeItem(storageKey);setTimeout(connect,300);return;
      }
      if(![1000,1002,1008,4002,4008].includes(event.code) && attempt<5){
        report('Disconnected · reconnecting without replaying pending actions…');
        setTimeout(connect,Math.min(500*2**attempt++,5000));
      } else if(![1000,4002,4008].includes(event.code) || status.hidden)report('Disconnected: '+(event.reason || 'reload to reconnect'));
    };
  }
  connect();
}
const root=document.querySelector('#pui-root');
if(root) start(root).catch(error=>{console.error(error);document.querySelector('#pui-status').textContent='Startup error: '+error.message;});
