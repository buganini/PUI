// Bound the reconstructed render state too: small deltas must not grow an
// unbounded retained display list. Published records are immutable, so cached
// subtree sizes can be reused without re-encoding or revisiting every scalar.
import { RENDER_LIMITS as LIMITS } from './schema.js';
const sizes=new WeakMap(),strings=new Map(),utf8=new TextEncoder();
const arrayHeader=n=>n<16?1:n<65536?3:5;
function stringBytes(value) {
  if(strings.has(value))return strings.get(value);
  const n=utf8.encode(value).length,bytes=n+(n<32?1:n<256?2:n<65536?3:5);
  if(value.length<64 && strings.size<256)strings.set(value,bytes);
  return bytes;
}
function usage(value) {
  if(value===null || typeof value==='boolean')return {items:1,bytes:1,depth:0};
  if(typeof value==='string')return {items:1,bytes:stringBytes(value),depth:0};
  if(typeof value==='number') {
    const bytes=!Number.isSafeInteger(value)?9:value>=0?
      (value<128?1:value<256?2:value<65536?3:value<=0xffffffff?5:9):
      (value>=-32?1:value>=-128?2:value>=-32768?3:value>=-2147483648?5:9);
    return {items:1,bytes,depth:0};
  }
  if(sizes.has(value))return sizes.get(value);
  let result;
  if(value instanceof Uint8Array) {
    const n=value.length;
    result={items:1,bytes:n+(n<256?2:n<65536?3:5),depth:0};
  } else {
    const array=Array.isArray(value),entries=array?value:Object.entries(value);
    result={items:1,bytes:arrayHeader(entries.length),depth:0};
    for(const entry of entries) {
      if(!array){result.items++;result.bytes+=stringBytes(entry[0]);result.depth=Math.max(result.depth,1);}
      const child=usage(array?entry:entry[1]);
      result.items+=child.items;result.bytes+=child.bytes;result.depth=Math.max(result.depth,1+child.depth);
    }
  }
  sizes.set(value,result);
  return result;
}

export function validateStateBudget(state) {
  // Count the nested snapshot representation, rather than Map storage or the
  // child IDs used internally by the DOM renderer. No full tree copy is needed.
  function node(id) {
    const n=state.nodes.get(id),result={...usage({...n,children:[]})};
    result.bytes+=arrayHeader(n.children.length)-1;
    for(const id of n.children) {
      const child=node(id);
      result.items+=child.items;result.bytes+=child.bytes;result.depth=Math.max(result.depth,2+child.depth);
    }
    return result;
  }
  const result={...usage({roots:[],bindings:[],canvases:[]})};
  for(const [values,measure] of [[state.roots,node],[state.slots.values(),usage],[state.canvases.values(),usage]]) {
    let count=0;
    for(const value of values) {
      const child=measure(value);count++;
      result.items+=child.items;result.bytes+=child.bytes;result.depth=Math.max(result.depth,2+child.depth);
      if(result.items>LIMITS.max_items || result.bytes>LIMITS.max_decoded_bytes || result.depth>LIMITS.max_depth)
        throw new Error('Reconstructed render exceeds limits');
    }
    result.bytes+=arrayHeader(count)-1;
  }
  if(result.bytes>LIMITS.max_decoded_bytes)throw new Error('Reconstructed render exceeds limits');
}
