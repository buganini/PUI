// Data/render limits shared by browser runtimes; no codec imports.
export const RENDER_LIMITS = Object.freeze({max_decoded_bytes: 32*1024*1024,
  max_items: 5000000, max_depth: 64});

// Message bodies supported by the currently advertised browser capabilities.
const object = value => value!==null && typeof value==='object' && Object.getPrototypeOf(value)===Object.prototype;
const fields = (value, names) => object(value) && Object.keys(value).sort().join(',')===names.split(' ').sort().join(',');
const text = value => typeof value==='string' && value.length>0;
const integer = (value,min=0) => Number.isSafeInteger(value) && value>=min;
const require = condition => {if(!condition)throw new Error('Invalid server message body');};

export function validateApplicationBody(type,b) {
  if(type==='result') {
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
