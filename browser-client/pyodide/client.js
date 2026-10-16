import { Controller } from '../shared/controller.js';
import { Renderer } from '../shared/dom.js';
import { validateApplicationBody } from '../shared/schema.js';
import { Resources } from './images.js';
export { Renderer };

const root=document.getElementById('pui-root'),status=document.getElementById('pui-status');
const restart=document.getElementById('pui-restart');
const BUILD=__PUI_BUILD__;
let worker=null,controller=null,resources=null,epoch=null,outgoing=0,incoming=0;
function report(message){status.textContent=message;status.hidden=false;}
function dispose(){
  worker?.terminate();worker=null;
  controller?.stop();controller?.renderer.destroy();controller=null;
  resources?.close();resources=null;root.inert=true;
}
function fail(error){console.error(error);dispose();report(`Unable to run cookbook: ${error.message || error}. Restart to try again.`);}
function send(type,body){
  if(!worker)throw Error('Worker has stopped');
  const seq=++outgoing;worker.postMessage({v:1,epoch,seq,type,body});return seq;
}
export function start() {
 try {
  dispose();root.replaceChildren();outgoing=incoming=0;
  epoch=crypto.randomUUID();const current=epoch;
  resources=new Resources();
  controller=new Controller(root,{send,sentSequence:()=>outgoing,report,
    onApplied:()=>{status.hidden=true;},onError:fail,
    onOverflow:()=>fail(Error('Input queue is full')),resources});
  report('Starting Python…');
  worker=new Worker(new URL('./worker.js?v='+BUILD,import.meta.url),{type:'module'});
  worker.onerror=event=>{if(current===epoch)fail(Error(event.message || 'Python worker failed'));};
  worker.onmessage=({data:m})=>{
    if(current!==epoch || !worker)return;
    try {
      if(m.epoch!==epoch)throw Error('Worker epoch mismatch');
      if(m.type==='loading'){report(m.message);return;}
      if(m.type==='failure'){throw Error(m.message);}
      if(m.v!==1 || !Number.isSafeInteger(m.seq) || m.seq!==incoming+1)throw Error('Worker sequence mismatch');
      incoming=m.seq;
      if(m.type==='ready'){
        if(controller.ready || m.body.build!==BUILD || m.body.max_pending_actions!==64)throw Error('Worker build mismatch');
        controller.activate();
      }else if(!controller.ready)throw Error('Worker has not initialized');
      else if(m.type==='resources')resources.update(m.body);
      else if(m.type==='render')controller.render(m.body);
      else if(m.type==='result')controller.result(m.body);
      else {
        validateApplicationBody(m.type,m.body);
        if(m.type==='error')throw Error(m.body.message);
        dispose();report(m.body.reason);
      }
    }catch(error){fail(error);}
  };
  worker.postMessage({type:'initialize',epoch,build:BUILD});
 } catch(error){fail(error);}
}
restart.addEventListener('click',start);
addEventListener('pagehide',dispose);
addEventListener('pageshow',event=>{if(event.persisted)start();});
start();
