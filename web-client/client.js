import { initializeCodec, encodeMessage, decodeMessage } from './protocol.js';
import { Renderer } from './dom.js';
export { initializeCodec, encodeMessage, decodeMessage };

export async function start(root) {
  const status=document.querySelector('#pui-status');
  const storageKey='pui:resume:'+location.pathname;
  let ws, epoch=null, seq=0, serverSeq=0, pending=new Set(), queue=[], ready=false;
  let attempt=0, awaitingSnapshot=true, recoveryCount=0, generation=0;
  const report=text=>{status.textContent=text;};
  const send=(type,body)=>{
    if(!ws || ws.readyState!==WebSocket.OPEN) throw new Error('Connection is not open');
    const sent=++seq; ws.send(encodeMessage({v:1,type,session:type==='hello'?null:epoch,seq:sent,body}));return sent;
  };
  const drain=()=>{while(ready && pending.size<64 && queue.length){const a=queue.shift();
    const n=send(a.type,a.body);pending.add(n);a.onSent?.(n);}};
  const renderer=new Renderer(root,(type,body,onSent)=>{
    if(!ready || renderer.dirty) return;
    if(queue.length>=256){report('Input queue is full; reconnect to continue.');ws.close(1008);return;}
    queue.push({type,body,onSent});drain();
  });
  const fatal=error=>{console.error(error);report('Connection error: '+error.message);ready=false;ws?.close(1002);};
  await initializeCodec();
  function connect() {
    const current=++generation;
    ready=false;epoch=null;seq=serverSeq=0;pending.clear();queue=[];
    renderer.drafts.clear();renderer.rev=0;renderer.dirty=true;awaitingSnapshot=true;recoveryCount=0;
    const url=new URL(root.dataset.ws,location.href);
    if(url.protocol==='http:')url.protocol='ws:';if(url.protocol==='https:')url.protocol='wss:';
    ws=new WebSocket(url,'pui.v1.msgpack.zstd');ws.binaryType='arraybuffer';
    let ordered=Promise.resolve();
    ws.onopen=()=>send('hello',{client_build:root.dataset.build,
      capabilities:['render.snapshot','render.patch','binding.object_id'],
      viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},
      resume_id:sessionStorage.getItem(storageKey)});
    ws.onmessage=event=>{ordered=ordered.then(()=>{
      if(current!==generation)return;
      const m=decodeMessage(new Uint8Array(event.data));
      if(m.seq!==serverSeq+1)throw new Error('Server sequence mismatch');serverSeq=m.seq;
      if(m.type==='ready') {
        if(epoch!==null || m.seq!==1 || m.body.server_build!==root.dataset.build)throw new Error('Invalid ready');
        epoch=m.session;sessionStorage.setItem(storageKey,m.body.resume_id);ready=true;attempt=0;
        report(m.body.resumed?'Connected · session resumed':'Connected');return;
      }
      if(!ready || m.session!==epoch)throw new Error('Session mismatch');
      if(m.type==='result'){pending.delete(m.body.reply_to);drain();return;}
      if(m.type==='error')throw new Error(m.body.message);
      if(m.type==='close'){ready=false;ws.close(1000);report(m.body.reason);return;}
      if(m.type!=='render')throw new Error('Unsupported server message');
      const b=m.body;
      if(!Number.isSafeInteger(b.rev) || b.rev<=0 || !Number.isSafeInteger(b.processed_seq) || b.processed_seq<0)
        throw new Error('Invalid render revision');
      if(!renderer.dirty && b.rev===renderer.rev){send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'applied'});return;}
      if(b.rev<renderer.rev){send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'discarded'});return;}
      try {
        if((b.mode==='snapshot' && !awaitingSnapshot) ||
          (b.mode==='patch' && (renderer.dirty || b.base_rev!==renderer.rev || b.rev<=b.base_rev)))
          throw new Error('Render base mismatch');
        renderer.apply(b);awaitingSnapshot=false;recoveryCount=0;
        send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'applied'});
      } catch(error) {
        renderer.dirty=true;awaitingSnapshot=true;
        send('ack',{render_rev:b.rev,applied_rev:renderer.rev,status:'discarded'});
        if(++recoveryCount>3)throw error;
        send('resync',{last_applied_rev:renderer.rev});
      }
    }).catch(fatal);};
    ws.onclose=event=>{
      if(current!==generation)return;
      ready=false;renderer.dirty=true;queue=[];pending.clear();
      if(event.code===1008 && event.reason.includes('Session already has a connection')){
        sessionStorage.removeItem(storageKey);setTimeout(connect,300);return;
      }
      if(![1000,1002,1008].includes(event.code) && attempt<5){
        report('Disconnected · reconnecting without replaying pending actions…');
        setTimeout(connect,Math.min(500*2**attempt++,5000));
      } else if(event.code!==1000)report('Disconnected: '+(event.reason || 'reload to reconnect'));
    };
  }
  connect();
}
const root=document.querySelector('#pui-root');
if(root) start(root).catch(error=>{console.error(error);document.querySelector('#pui-status').textContent='Startup error: '+error.message;});
