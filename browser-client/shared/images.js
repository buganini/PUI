// Bounded decoded-image store; the backend resolves resource IDs to URLs.
export function imageTransforms(ops) {
  return Array.isArray(ops) && ops.length<=32 && ops.every(o=>Array.isArray(o) &&
    (o[0]==='crop'?o.length===5 && o.slice(1).every(v=>Number.isInteger(v) && Math.abs(v)<=16384) && o[3]>0 && o[4]>0:
     o[0]==='scale' && o.length===5 && o.slice(1,3).every(v=>Number.isInteger(v) && v>0 && v<=16384) &&
       typeof o[3]==='boolean' && typeof o[4]==='boolean'));
}
const key=(url,ops)=>ops.length?JSON.stringify([url,ops]):url;
export class Images {
  constructor(url=value=>value){this.url=url;this.items=new Map();this.pixels=0;this.active=0;this.waiting=[];}
  async slot(work) {
    if(this.active>=8)await new Promise(resolve=>this.waiting.push(resolve));
    else this.active++;
    try{return await work();}finally{const next=this.waiting.shift();if(next)next();else this.active--;}
  }
  store(k,work) {
    const existing=this.items.get(k);if(existing)return existing.promise;
    if(this.items.size>=128)return Promise.reject(Error('Image count exceeds 128'));
    const item={pixels:0,image:null};this.items.set(k,item);
    item.promise=work().then(image=>{
      const pixels=image.naturalWidth===undefined?image.width*image.height:image.naturalWidth*image.naturalHeight;
      if(this.items.get(k)!==item)throw Error('Image was retired');
      if(!pixels || pixels>16777216 || this.pixels+pixels>33554432)throw Error('Decoded image budget exceeded');
      item.image=image;item.pixels=pixels;this.pixels+=pixels;return image;
    });
    return item.promise;
  }
  source(url) {
    return this.store(url,()=>this.slot(async()=>{
      if(!this.items.has(url))throw Error('Image was retired');
      const image=new Image();image.src=this.url(url);
      let timer;
      try {
        await Promise.race([image.decode(),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('Image load timed out')),15000);})]);
        return image;
      } catch(error){image.src='';throw error;}
      finally{clearTimeout(timer);}
    }));
  }
  resolve(url,ops) {
    if(!ops.length)return this.source(url);
    return this.store(key(url,ops),async()=>{
      let image=await this.source(url);
      for(const op of ops) {
        const canvas=document.createElement('canvas');
        if(op[0]==='crop'){canvas.width=op[3];canvas.height=op[4];}
        else {
          const ratio=op[3]?Math.min(op[1]/image.width,op[2]/image.height):null;
          canvas.width=ratio===null?op[1]:Math.max(1,Math.round(image.width*ratio));
          canvas.height=ratio===null?op[2]:Math.max(1,Math.round(image.height*ratio));
        }
        if(canvas.width*canvas.height>16777216)throw Error('Image transform exceeds pixel budget');
        const ctx=canvas.getContext('2d');
        if(op[0]==='crop')ctx.drawImage(image,-op[1],-op[2]);
        else {ctx.imageSmoothingEnabled=op[4];ctx.imageSmoothingQuality='high';ctx.drawImage(image,0,0,canvas.width,canvas.height);}
        if(image instanceof HTMLCanvasElement)image.width=image.height=0;
        image=canvas;
      }
      return image;
    });
  }
  retain(frames) {
    const keep=new Set();
    for(const f of frames)for(const c of f.commands)if(c.op==='image'){keep.add(c.resource);keep.add(key(c.resource,c.transforms));}
    for(const [k,item] of this.items)if(!keep.has(k)){
      this.pixels-=item.pixels;this.items.delete(k);
      if(item.image instanceof HTMLCanvasElement)item.image.width=item.image.height=0;
      else if(item.image)item.image.src='';
    }
  }
  async frame(frame) {
    const result=new Map();
    await Promise.all(frame.commands.filter(c=>c.op==='image').map(async c=>{result.set(c,await this.resolve(c.resource,c.transforms));}));
    return result;
  }
}
