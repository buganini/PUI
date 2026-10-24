import { startAI } from './ai.js';
import { initializeCodec, encodeMessage, decodeMessage, StreamDecoder } from './protocol.js';
import { Renderer as BrowserRenderer } from '../shared/dom.js';
import { Controller } from '../shared/controller.js';
import { webResources } from './images.js';
import { validateServerBody } from './messages.js';
import { parseOptions, replaceStateRefs } from '../shared/options.js';
export { initializeCodec, encodeMessage, decodeMessage, StreamDecoder };
export { validateServerBody };
// Keep the Web test/embed entry's HTTP image defaults compatible.
export class Renderer extends BrowserRenderer {
  constructor(root,actions,control,onError) {super(root,actions,control,onError,webResources);}
}

export async function start(root) {
  const status=document.querySelector('#pui-status');
  const passthru=root.dataset.passthru==='true';
  const storageKey='pui:resume:'+location.pathname;
  const ownerKey='pui:resume-owner:'+location.pathname;
  // Same-account reauthentication preserves this marker; logout/account changes do not.
  if(sessionStorage.getItem(ownerKey)!==root.dataset.resumeOwner){
    sessionStorage.removeItem(storageKey);
    sessionStorage.setItem(ownerKey,root.dataset.resumeOwner);
  }
  let ws, epoch=null, seq=0, serverSeq=0;
  let attempt=0, generation=0;
  let stopped=false, downstream=null;
  const report=text=>{status.textContent=text;status.hidden=false;};
  root.inert=true;
  const stop=code=>{stopped=true;controller.stop();downstream?.close();ws?.close(code);};
  const send=(type,body)=>{
    if(!ws || ws.readyState!==WebSocket.OPEN) throw new Error('Connection is not open');
    const sent=++seq; ws.send(encodeMessage({v:1,type,session:type==='hello'?null:epoch,seq:sent,body}));return sent;
  };
  const controller=new Controller(root,{send,sentSequence:()=>seq,report,
    resources:webResources,RendererClass:Renderer,onApplied:()=>{status.hidden=true;},onError:error=>fatal(error),
    onOverflow:()=>{report('Input queue is full; reload to continue.');stop(4008);}});
  const fatal=error=>{if(stopped)return;console.error(error);report('Connection error: '+error.message);stop(4002);};
  controller.renderer.drops.upload=async(files,n,signal)=>{
    const form=new FormData();for(const file of files)form.append('files',file,file.name);
    const response=await fetch(root.dataset.upload,{method:'POST',body:form,signal,credentials:'same-origin',
      headers:{'X-PUI-Upload':root.dataset.uploadToken,'X-PUI-Session':sessionStorage.getItem(storageKey),
        'X-PUI-Epoch':epoch,'X-PUI-Node':n.id,'X-PUI-Target':n.events.drop}});
    if(!response.ok)throw Error(await response.text());
    return (await response.json()).upload_id;
  };
  await initializeCodec();
  function chooseSession(message) {
    const resumeId=sessionStorage.getItem(storageKey);
    root.inert=true;
    report('');
    const description=document.createElement('span');description.textContent=message;status.append(description);
    const actions=document.createElement('span');actions.className='pui-session-actions';
    const add=(label,callback)=>{
      const button=document.createElement('button');button.type='button';
      button.className='pui-Button';button.textContent=label;
      button.onclick=callback;
      actions.append(button);
    };
    if(resumeId)add('Resume session',()=>{attempt=0;report('Resuming session…');connect(resumeId);});
    add('Renew session',()=>sessionAction('renew',resumeId));
    if(root.dataset.authRequired==='true')add('Logout',()=>sessionAction('logout'));
    status.append(actions);
    if(resumeId){
      const note=document.createElement('span');note.className='pui-session-note';
      note.textContent='Resume keeps the previous state when available; expired sessions start fresh. Renew session resets this session; other sessions are kept. Unsent edits and pending actions are not replayed.';
      if(root.dataset.authRequired==='true')note.textContent+=' Renew keeps you signed in. Logout signs out of this browser session, including other tabs.';
      status.append(note);
    }
    actions.firstElementChild.focus();
  }
  function sessionAction(action,resumeId=null) {
    stop(1000);++generation;sessionStorage.removeItem(storageKey);root.replaceChildren();
    report(action==='renew'?'Renewing session…':'Signing out…');
    const form=document.createElement('form');form.method='post';form.action=root.dataset[action]+location.hash;
    const fields={csrf:root.dataset[action+'Token']};
    if(action==='renew')fields.resume_id=resumeId||'';
    for(const [name,value] of Object.entries(fields)){
      const input=document.createElement('input');input.type='hidden';input.name=name;input.value=value;form.append(input);
    }
    document.body.append(form);form.submit();
  }
  function connect(resumeId) {
    const current=++generation;
    downstream?.close();
    const decoder=downstream=new StreamDecoder();
    stopped=false;epoch=null;seq=serverSeq=0;controller.reset();
    const url=new URL(root.dataset.ws,location.href);
    if(url.protocol==='http:')url.protocol='ws:';if(url.protocol==='https:')url.protocol='wss:';
    ws=new WebSocket(url,'pui.v1.msgpack.zstd-stream');ws.binaryType='arraybuffer';
    let ordered=Promise.resolve(), established=false;
    ws.onopen=()=>send('hello',{client_build:root.dataset.build,
      capabilities:['render.snapshot','render.patch','binding.object_id','canvas.geometry','canvas.text','canvas.input','canvas.path','canvas.image','canvas.patch','state.refs'],
      viewport:{width:innerWidth,height:innerHeight,dpr:devicePixelRatio},
      resume_id:resumeId});
    ws.onmessage=event=>{ordered=ordered.then(()=>{
      if(current!==generation || stopped)return;
      const m=decoder.decode(new Uint8Array(event.data));
      validateServerBody(m.type,m.body);
      if(m.seq!==serverSeq+1)throw new Error('Server sequence mismatch');serverSeq=m.seq;
      if(m.type==='ready') {
        if(epoch!==null || m.seq!==1 || m.body.server_build!==root.dataset.build)throw new Error('Invalid ready');
        controller.renderer.drops.limits=m.body.upload_limits;
        epoch=m.session;sessionStorage.setItem(storageKey,m.body.resume_id);controller.activate(m.body.limits.max_pending_actions);established=true;attempt=0;
        if(!m.body.capabilities.includes('state.refs'))throw new Error('Server does not support URL options');
        send('options',{values:parseOptions(location.hash)});
        report(passthru?'Connected':m.body.resumed?'Connected · session resumed':resumeId?'Previous session expired · new session started':'Connected');return;
      }
      if(!controller.ready || m.session!==epoch)throw new Error('Session mismatch');
      if(m.type==='dialog') {
        const b=m.body, message=b.title?b.title+'\n\n'+b.message:b.message;
        let value=null;
        if(b.kind==='confirm')value=window.confirm(message);
        else if(b.kind==='prompt')value=window.prompt(message,b.default);
        else window.alert(message);
        send('dialog_result',{request_id:b.request_id,value});return;
      }
      if(m.type==='drop_result'){controller.renderer.drops.result(m.body);return;}
      if(m.type==='state_ref'){replaceStateRefs(m.body.values);return;}
      if(m.type==='result'){controller.result(m.body);return;}
      if(m.type==='error')throw new Error(m.body.message);
      if(m.type==='close'){report(m.body.reason);stop(1000);return;}
      if(m.type!=='render')throw new Error('Unsupported server message');
      controller.render(m.body);
    }).catch(fatal);};
    ws.onclose=event=>{
      decoder.close();
      if(current!==generation)return;
      const wasStopped=stopped;stopped=true;
      controller.stop();
      if(wasStopped)return;
      if(event.code===4005){
        root.replaceChildren();report('This session was taken over in another tab or device.');
        return;
      }
      if(event.code===4004){
        root.replaceChildren();report('Authentication expired. Sign in to resume. ');
        const link=document.createElement('a');link.href=root.dataset.entry;link.textContent='Sign in';status.append(link);
        return;
      }
      if(event.code===4001 || event.code===4003){
        sessionStorage.removeItem(storageKey);root.replaceChildren();
        report(event.code===4001?'Logged out. ':'Session renewed. ');
        const link=document.createElement('a');link.href=root.dataset.entry;link.textContent='Continue';status.append(link);
        return;
      }
      if(passthru && ![1000,1002,1008,4002,4008].includes(event.code) && attempt<5){
        report('Disconnected · reconnecting…');
        setTimeout(()=>{if(current===generation)connect(sessionStorage.getItem(storageKey));},
          Math.min(500*2**attempt++,5000));
        return;
      }
      if(!passthru && event.code===1008 && event.reason.includes('Session already has a connection')){
        chooseSession('The previous session is still connected. Retry resume or renew the session.');return;
      }
      if(!passthru && established && ![1002,1008,4002,4008].includes(event.code)){
        chooseSession('Disconnected · resume or renew the previous session.');return;
      }
      if(![1000,1002,1008,4002,4008].includes(event.code) && attempt<5){
        report('Disconnected · reconnecting without replaying pending actions…');
        setTimeout(()=>{if(current===generation)connect(resumeId);},Math.min(500*2**attempt++,5000));
      } else if(![1000,4002,4008].includes(event.code) || status.hidden)report('Disconnected: '+(event.reason || 'reload to reconnect'));
    };
  }
  startAI(root,{resumeId:()=>sessionStorage.getItem(storageKey),renew:id=>sessionAction('renew',id)});
  if(!passthru && sessionStorage.getItem(storageKey))chooseSession('Resume or renew the previous session.');
  else connect(passthru?sessionStorage.getItem(storageKey):null);
}
const root=document.querySelector('#pui-root');
if(root) start(root).catch(error=>{console.error(error);document.querySelector('#pui-status').textContent='Startup error: '+error.message;});
