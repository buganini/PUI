// A module worker owns Python. Only plain records cross the local bridge.
import {nulls} from './values.js';
const CDN='https://cdn.jsdelivr.net/pyodide/v314.0.7/full/';
let initialized=false, dispatch=null, failed=false, epoch=null;
function fail(error) {
  if(failed)return;
  failed=true;console.error(error);
  postMessage({type:'failure',epoch,message:String(error)});
}
async function initialize(config) {
  epoch=config.epoch;
  if(config.build!==__PUI_BUILD__)throw Error('Worker build mismatch; reload the page');
  const progress=message=>postMessage({type:'loading',epoch,message});
  progress('Loading Python 3.14 / Pyodide 314.0.7…');
  const {loadPyodide}=await import(CDN+'pyodide.mjs');
  const python=await loadPyodide({indexURL:CDN,
    stdout:text=>console.log(text),stderr:text=>console.error(text)});
  progress('Loading cookbook packages…');
  await python.loadPackage(['pygments']);
  const response=await fetch(new URL('./app.zip?v='+__PUI_ARCHIVE_HASH__,import.meta.url));
  if(!response.ok)throw Error(`Cookbook download failed (${response.status})`);
  const archive=await response.arrayBuffer();
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',archive)),n=>n.toString(16).padStart(2,'0')).join('');
  if(digest!==__PUI_ARCHIVE_HASH__)throw Error('Cookbook archive version mismatch; rebuild and reload');
  python.unpackArchive(archive,'zip',{extractDir:'/app'});
  python.registerJsModule('_pui_bridge',{
    // This argument is a borrowed PyProxy, automatically released by Pyodide.
    send:record=>postMessage(nulls(record.toJs({dict_converter:Object.fromEntries,create_pyproxies:false}),undefined,null)),
    epoch:config.epoch, build:config.build, options:config.options,
  });
  progress('Starting cookbook…');
  await python.runPythonAsync(`
import os, sys, asyncio
os.chdir('/app')
sys.path.insert(0, '/app')
os.environ['PUI_BACKEND'] = 'pyodide'
from _pui_bridge import send, epoch, build, options
from PUI.pyodide.runtime import Runtime
from PUI import Options
Options.clear()
Options.update(options.to_py())
_pui_runtime = Runtime(asyncio.get_running_loop(), send, epoch=epoch, build=build)
from PUI.cookbook.app import Cookbook
_pui_task = Cookbook().start()
`);
  const owner=python.globals.get('_pui_runtime');
  dispatch=owner.receive.copy();
  const begin=owner.upload_begin.copy(),store=owner.uploads.copy();
  let uploading=false;
  const cancelled=new Set();
  async function upload(m){
    if(uploading){postMessage({type:'uploaded',epoch,id:m.id,error:'Another upload is in progress'});return;}
    let batch=null;
    try {
      uploading=true;
      let names=python.toPy(m.files.map(f=>f.name)),record;
      try{record=begin(m.node_id,m.token,names);batch=record.toJs({dict_converter:Object.fromEntries});}
      finally{names.destroy();record?.destroy();}
      for(let i=0;i<m.files.length;i++){
        const reader=m.files[i].stream().getReader();
        try{
          for(;;){const {value,done}=await reader.read();if(cancelled.has(m.id))throw Error('Upload cancelled');if(done)break;
            const data=python.toPy(value);try{store.write(batch.key,batch.files[i],data);}finally{data.destroy?.();}
          }
        }finally{await reader.cancel();reader.releaseLock();}
      }
      store.finish(batch.key);
      postMessage({type:'uploaded',epoch,id:m.id,upload_id:batch.key});
    }catch(error){if(batch)store.discard(batch.key);postMessage({type:'uploaded',epoch,id:m.id,error:String(error)});}
    finally{uploading=false;cancelled.delete(m.id);}
  }
  owner.destroy();
  // dispatch is owned for this worker lifetime; termination releases the interpreter.
  const convert=python.toPy;
  self.onmessage=event=>{
    if(failed)return;
    if(event.data?.type==='cancel_upload'){if(event.data.epoch===epoch && uploading)cancelled.add(event.data.id);return;}
    if(event.data?.type==='upload'){if(event.data.epoch===epoch)upload(event.data);return;}
    let record;
    try{record=convert(nulls(event.data,null,undefined));dispatch(record);}
    catch(error){fail(error);}
    finally{record?.destroy?.();}
  };
}
self.onmessage=event=>{
  if(initialized){fail(Error('Worker is still starting'));return;}
  initialized=true;
  const c=event.data;
  if(c?.type!=='initialize' || typeof c.epoch!=='string' || typeof c.build!=='string'){
    fail(Error('Invalid worker initialization'));return;
  }
  initialize(c).catch(fail);
};
