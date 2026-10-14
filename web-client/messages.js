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
  } else if(type==='result') {
    require(fields(b,'reply_to status code') && integer(b.reply_to,1) &&
      ['processed','stale','invalid','error'].includes(b.status) &&
      (b.status==='processed'?b.code===null:text(b.code)));
  } else if(type==='render') {
    require(object(b) && integer(b.rev,1) && integer(b.processed_seq));
    if(b.mode==='snapshot') require(fields(b,'mode base_rev rev processed_seq roots bindings canvases') &&
      b.base_rev===null && ['roots','bindings','canvases'].every(k=>Array.isArray(b[k])));
    else require(b.mode==='patch' && fields(b,'mode base_rev rev processed_seq ops') &&
      integer(b.base_rev) && b.rev>b.base_rev && Array.isArray(b.ops));
  } else if(type==='error') {
    require(fields(b,'code reply_to fatal message') && text(b.code) &&
      (b.reply_to===null || integer(b.reply_to,1)) && typeof b.fatal==='boolean' && typeof b.message==='string');
  } else if(type==='close') {
    require(fields(b,'reason') && typeof b.reason==='string');
  } else throw new Error('Unsupported server message');
}
