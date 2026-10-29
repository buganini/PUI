import { validateApplicationBody } from '../shared/schema.js';
// Message bodies supported by the currently advertised browser capabilities.
const object = value => value!==null && typeof value==='object' && Object.getPrototypeOf(value)===Object.prototype;
const fields = (value, names) => object(value) && Object.keys(value).sort().join(',')===names.split(' ').sort().join(',');
const text = value => typeof value==='string' && value.length>0;
const integer = (value,min=0) => Number.isSafeInteger(value) && value>=min;
const require = condition => {if(!condition)throw new Error('Invalid server message body');};
const caps = ['render.snapshot','render.patch','binding.object_id'];

export function validateServerBody(type,b) {
  if(type==='dialog') {
    require(fields(b,b.kind==='savefile'?'request_id kind message title default options':'request_id kind message title default') && text(b.request_id) &&
      ['alert','confirm','prompt','savefile'].includes(b.kind) &&
      ['message','title','default'].every(key=>typeof b[key]==='string'));
    if(b.kind==='savefile'){
      const o=b.options;
      require(object(o) && ['choice','name','browse','overwrite'].includes(o.stage));
      if(o.stage==='name' || o.stage==='browse')require(typeof o.name==='string' && typeof o.error==='string');
      if(o.stage==='overwrite')require(typeof o.path==='string');
      if(o.stage==='browse')require(typeof o.directory==='string' && (o.parent===null || typeof o.parent==='string') &&
        typeof o.filter==='string' && integer(o.offset) && integer(o.total) && Array.isArray(o.entries) &&
        o.entries.length<=200 && o.entries.every(e=>fields(e,'name path directory') &&
          typeof e.name==='string' && typeof e.path==='string' && typeof e.directory==='boolean'));
    }
  } else if(type==='ready') {
    require(fields(b,'server_build capabilities limits resume_id resumed session_ttl upload_limits'));
    require(fields(b.upload_limits,'max_files max_file_bytes max_session_bytes') && Object.values(b.upload_limits).every(v=>integer(v,1)));
    require(text(b.server_build) && text(b.resume_id) && typeof b.resumed==='boolean' &&
      typeof b.session_ttl==='number' && Number.isFinite(b.session_ttl) && b.session_ttl>=0);
    require(Array.isArray(b.capabilities) && b.capabilities.every(text) &&
      new Set(b.capabilities).size===b.capabilities.length && caps.every(c=>b.capabilities.includes(c)));
    require(fields(b.limits,'max_wire_bytes max_decoded_bytes max_window_bytes max_items max_depth max_pending_actions') &&
      Object.values(b.limits).every(v=>integer(v,1)));
  } else if(type==='state_ref') {
    require(fields(b,'values') && Array.isArray(b.values) && b.values.every(pair=>
      Array.isArray(pair) && pair.length===2 && text(pair[0]) && typeof pair[1]==='string'));
  } else validateApplicationBody(type,b);
}
