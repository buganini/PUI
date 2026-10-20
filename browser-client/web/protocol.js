import { encode, decode } from '@msgpack/msgpack';
import { preload, compressSync, decompressSync, createDecompressStreamSync,
  setMaxDecompressedSize } from 'compress-utils/zstd';
import { RENDER_LIMITS } from '../shared/schema.js';

export const LIMITS = Object.freeze({max_wire_bytes: 8*1024*1024,
  ...RENDER_LIMITS, max_window_bytes: 16*1024*1024});
const types = new Set(['dialog','dialog_result','hello','ready','options','state_ref', 'drop_result','render','event','binding_write','result',
  'container_size', 'measure','ack','canvas_ack','resync','resource','release','error','close']);
const utf8 = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true});
const fail = message => { throw new Error(message); };
export async function initializeCodec() {
  await preload();
  await setMaxDecompressedSize(LIMITS.max_decoded_bytes);
}

function frameSize(bytes) {
  if (!(bytes instanceof Uint8Array) || bytes.length > LIMITS.max_wire_bytes) fail('Frame limit');
  let p = 0;
  const read = n => {
    if (p+n > bytes.length) fail('Truncated frame');
    let value = 0n;
    for (let i=0; i<n; i++) value |= BigInt(bytes[p++]) << BigInt(8*i);
    if (value > BigInt(Number.MAX_SAFE_INTEGER)) fail('Frame size limit');
    return Number(value);
  };
  if (read(4) !== 0xfd2fb528) fail('Expected Zstandard');
  const descriptor = read(1), single = (descriptor & 32) !== 0;
  if (descriptor & 24) fail('Reserved frame flags');
  let window = 0;
  if (!single) { const w = read(1), base = 2 ** (10+(w>>3)); window = base+base/8*(w&7); }
  if (read([0,1,2,4][descriptor&3]) !== 0) fail('Dictionary unsupported');
  const sizeBytes = [single ? 1 : 0, 2, 4, 8][descriptor>>6];
  if (!sizeBytes) fail('Content size required');
  const size = read(sizeBytes) + (sizeBytes === 2 ? 256 : 0);
  if (size > LIMITS.max_decoded_bytes || (single ? size : window) > LIMITS.max_window_bytes)
    fail('Decoded size/window limit');
  let last = false;
  while (!last) {
    const header = read(3), type = (header>>1)&3;
    last = !!(header&1);
    if (type === 3) fail('Reserved block type');
    p += type === 1 ? 1 : header>>3;
    if (p > bytes.length) fail('Truncated block');
  }
  if (descriptor&4) p += 4;
  if (p !== bytes.length) fail('Trailing/truncated frame');
  return size;
}

// The codec has per-container length limits. Preflight additionally rejects
// duplicate keys, invalid UTF-8, extensions and excessive aggregate depth/items.
function inspectMessagePack(bytes,checkNumbers=true) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let p=0, items=0;
  const need = n => { if (p+n > bytes.length) fail('Truncated MessagePack'); };
  const uint = n => { need(n); let v=0; for(let i=0;i<n;i++) v=v*256+bytes[p++]; return v; };
  const string = n => { need(n); const s=utf8.decode(bytes.subarray(p,p+n)); p+=n; return s; };
  function visit(depth) {
    if (++items > LIMITS.max_items) fail(`Value count exceeds limit (${items} > ${LIMITS.max_items})`);
    if (depth > LIMITS.max_depth) fail(`Nesting depth exceeds limit (${depth} > ${LIMITS.max_depth})`);
    const tag=uint(1);
    if (tag<=0x7f || tag>=0xe0 || tag===0xc0 || tag===0xc2 || tag===0xc3) return null;
    let length, map=false;
    if ((tag&0xe0)===0xa0) return string(tag&31);
    if ((tag&0xf0)===0x90) length=tag&15;
    else if ((tag&0xf0)===0x80) { length=tag&15; map=true; }
    else if (tag===0xdc || tag===0xdd) length=uint(tag===0xdc?2:4);
    else if (tag===0xde || tag===0xdf) { length=uint(tag===0xde?2:4); map=true; }
    else if (tag>=0xd9 && tag<=0xdb) return string(uint([1,2,4][tag-0xd9]));
    else if (tag>=0xc4 && tag<=0xc6) { const n=uint([1,2,4][tag-0xc4]); need(n); p+=n; return null; }
    else if (tag===0xca || tag===0xcb) {
      const n=tag===0xca?4:8; need(n);
      const value= n===4 ? view.getFloat32(p) : view.getFloat64(p); p+=n;
      if (checkNumbers && !Number.isFinite(value)) fail('Non-finite value'); return null;
    } else if (tag>=0xcc && tag<=0xd3) {
      const n=[1,2,4,8,1,2,4,8][tag-0xcc]; need(n);
      if(n===8 && checkNumbers) { const value=tag===0xcf?view.getBigUint64(p):view.getBigInt64(p);
        if(value>9007199254740991n || value< -9007199254740991n) fail('Unsafe integer'); }
      p+=n; return null;
    } else fail('Unsupported MessagePack type');
    if (length > LIMITS.max_items) fail('Container limit');
    const keys = map ? new Set() : null;
    for(let i=0;i<length;i++) {
      if(map) { const key=visit(depth+1);
        if(typeof key!=='string' || key==='__proto__' || keys.has(key)) fail('Invalid/duplicate map key');
        keys.add(key); }
      visit(depth+1);
    }
    return null;
  }
  visit(0);
  if(p!==bytes.length) fail('Trailing MessagePack');
}

function envelope(value) {
  if (!value || Object.keys(value).sort().join(',') !== 'body,seq,session,type,v' ||
      value.v!==1 || !types.has(value.type) || !Number.isSafeInteger(value.seq) || value.seq<=0 ||
      (value.type==='hello' ? value.session!==null : typeof value.session!=='string' || !value.session) ||
      !value.body || Object.getPrototypeOf(value.body)!==Object.prototype) fail('Invalid envelope');
  return value;
}
export function encodeMessage(value) {
  let count=0;
  function validate(v,depth=0) {
    if(++count>LIMITS.max_items) fail(`Value count exceeds limit (${count} > ${LIMITS.max_items})`);
    if(depth>LIMITS.max_depth) fail(`Nesting depth exceeds limit (${depth} > ${LIMITS.max_depth})`);
    if(v===null || typeof v==='boolean') return;
    if(typeof v==='number') {if(!Number.isFinite(v))fail('Non-finite number');return;}
    if(typeof v==='string') {
      for(let i=0;i<v.length;i++) {
        const code=v.charCodeAt(i);
        if(code>=0xd800 && code<=0xdbff) {const next=v.charCodeAt(++i);if(!(next>=0xdc00 && next<=0xdfff))fail('Invalid Unicode');}
        else if(code>=0xdc00 && code<=0xdfff)fail('Invalid Unicode');
      }
      return;
    }
    if(v instanceof Uint8Array)return;
    if(Array.isArray(v)){for(const item of v)validate(item,depth+1);return;}
    if(typeof v!=='object' || ![Object.prototype,null].includes(Object.getPrototypeOf(v)))fail('Unsupported value');
    for(const [k,item] of Object.entries(v)){if(k==='__proto__')fail('Unsupported map key');validate(k,depth+1);validate(item,depth+1);}
  }
  validate(value);
  envelope(value);
  const data=encode(value, {maxDepth: LIMITS.max_depth});
  if(data.length>LIMITS.max_decoded_bytes) fail('Decoded size limit');
  inspectMessagePack(data);
  const frame=compressSync(data,{level:1}); frameSize(frame); return frame;
}
export function decodeMessage(frame) {
  const size=frameSize(frame), data=decompressSync(frame,{expectedSize:size});
  if(data.length!==size) fail('Content size mismatch');
  return unpackMessage(data);
}

function unpackMessage(data,downstream=false) {
  inspectMessagePack(data,!downstream);
  const message=envelope(decode(data, {maxStrLength:LIMITS.max_decoded_bytes,
    maxBinLength:LIMITS.max_decoded_bytes,maxArrayLength:LIMITS.max_items,
    maxMapLength:LIMITS.max_items,maxExtLength:0}));
  if(downstream && message.type!=='render')inspectMessagePack(data);
  return message;
}

// Each downstream WebSocket message ends at a block-flush boundary and contains
// one complete envelope, including the entire DOM/Canvas batch for a render.
// Context belongs to this connection only; never replay compressed bytes.
export class StreamDecoder {
  constructor() {
    this.window=null;this.closed=false;
    this.decoder=createDecompressStreamSync();
  }
  close() {
    this.closed=true;this.decoder?.destroy();this.decoder=null;
  }
  decode(packet) {
    if(this.closed)fail('Compression stream is closed');
    try {
      const ends=this.preflight(packet),chunks=[];
      let start=0,size=0;
      for(const end of ends){
        const data=this.decoder.write(packet.subarray(start,end));
        start=end;size+=data.length;
        if(size>LIMITS.max_decoded_bytes)fail('Decoded batch limit');
        chunks.push(data);
      }
      // write() returns owned bytes; a single bounded write needs no extra copy.
      if(chunks.length===1)return unpackMessage(chunks[0],true);
      const data=new Uint8Array(size);
      let offset=0;
      for(const chunk of chunks){data.set(chunk,offset);offset+=chunk.length;}
      return unpackMessage(data,true);
    } catch(error) {this.close();throw error;}
  }
  preflight(packet) {
    if(!(packet instanceof Uint8Array) || !packet.length)fail('Expected nonempty binary batch');
    if(packet.length>LIMITS.max_wire_bytes)fail('Compressed batch limit');
    let p=0;
    if(this.window===null){
      if(packet.length<6 || packet[0]!==0x28 || packet[1]!==0xb5 ||
          packet[2]!==0x2f || packet[3]!==0xfd || packet[4]!==0)
        fail('Expected an open Zstandard stream');
      const descriptor=packet[5],base=2**(10+(descriptor>>3));
      this.window=base+base/8*(descriptor&7);
      if(this.window>LIMITS.max_window_bytes)fail('Stream window limit');
      p=6;
    }
    let blocks=0,outputBound=0;
    const ends=[];
    while(p<packet.length){
      if(p+3>packet.length)fail('Truncated stream block header');
      const header=packet[p]|packet[p+1]<<8|packet[p+2]<<16;
      const type=(header>>1)&3,size=header>>3;
      if((header&1) || type===3)fail('Ended stream or reserved block type');
      if(size>Math.min(this.window,128*1024))fail('Stream block limit');
      // The WASM stream API has no output cap. Split only at block boundaries
      // so each write can expand by at most one decoded-batch budget.
      const bound=type===2?Math.min(this.window,128*1024):size;
      if(outputBound+bound>LIMITS.max_decoded_bytes){ends.push(p);outputBound=0;}
      outputBound+=bound;
      p+=3+(type===1?1:size);
      if(p>packet.length)fail('Truncated stream block');
      blocks++;
    }
    if(!blocks)fail('Empty stream batch');
    ends.push(p);return ends;
  }
}
