import { validateApplicationBody } from '../shared/schema.js';
// Message bodies supported by the currently advertised browser capabilities.
const object = value => value!==null && typeof value==='object' && Object.getPrototypeOf(value)===Object.prototype;
const fields = (value, names) => object(value) && Object.keys(value).sort().join(',')===names.split(' ').sort().join(',');
const text = value => typeof value==='string' && value.length>0;
const integer = (value,min=0) => Number.isSafeInteger(value) && value>=min;
const require = condition => {if(!condition)throw new Error('Invalid server message body');};
const caps = ['render.snapshot','render.patch','binding.object_id'];

export function validateServerBody(type,b) {
  if(type==='ready') {
    require(fields(b,'server_build capabilities limits resume_id resumed session_ttl'));
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
