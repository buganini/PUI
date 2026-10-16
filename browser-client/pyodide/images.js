// Original bytes from this worker only; public URLs never bypass this registry.
export class Resources {
  constructor(){this.entries=new Map();}
  valid=ref=>typeof ref==='string' && this.entries.has(ref);
  url=ref=>{
    const entry=this.entries.get(ref);if(!entry)throw Error('Unknown image resource');
    return entry;
  };
  update(body) {
    if(!body || !Array.isArray(body.add) || !Array.isArray(body.keep) || body.keep.length>128 ||
      new Set(body.keep).size!==body.keep.length)throw Error('Invalid image registry');
    const additions=new Set();
    for(const e of body.add) {
      if(!/^image:[1-9][0-9]*$/.test(e.ref) || typeof e.mime!=='string' || !e.mime.startsWith('image/') ||
        !(e.data instanceof Uint8Array) || e.data.byteLength>64*1024*1024 ||
        !body.keep.includes(e.ref) || this.entries.has(e.ref) || additions.has(e.ref))
        throw Error('Invalid image resource');
      additions.add(e.ref);
    }
    for(const ref of body.keep)if(!this.entries.has(ref) && !additions.has(ref))throw Error('Missing image resource');
    for(const e of body.add)this.entries.set(e.ref,URL.createObjectURL(new Blob([e.data],{type:e.mime})));
    for(const [ref,url] of this.entries)if(!body.keep.includes(ref)){
      URL.revokeObjectURL(url);this.entries.delete(ref);
    }
  }
  close(){for(const url of this.entries.values())URL.revokeObjectURL(url);this.entries.clear();}
}
