// Pairs preserve URL order and allow any string key.
function readHash(hash, warn) {
  const values=new Map();
  for(const part of hash.split('#')) {
    if(!part)continue;
    try {
      const equals=part.indexOf('=');
      if(equals<1)throw new Error('Expected name=value');
      const name=decodeURIComponent(part.slice(0,equals));
      const text=decodeURIComponent(part.slice(equals+1));
      if(!name)throw new Error('Empty name');
      values.set(name,text);
    } catch(error) {warn('PUI: skipping invalid URL option:',error.message);}
  }
  return values;
}

export function parseOptions(hash, warn=console.warn) {
  return [...readHash(hash,warn)];
}

export function mergeStateRefs(hash, updates, warn=console.warn) {
  const values=readHash(hash,warn);
  let changed=false;
  // Last declaration wins before comparison, including duplicates in a batch.
  for(const [name,text] of new Map(updates)) {
    try {
      const value=JSON.parse(text);
      const formatted=typeof value==='string'?value:text;
      if(values.get(name)===formatted)continue;
      values.set(name,formatted);
      changed=true;
    } catch(error) {warn('PUI: skipping invalid State ref:',error.message);}
  }
  if(!changed)return null;
  return [...values].map(([name,text])=>'#'+encodeURIComponent(name)+'='+encodeURIComponent(text)).join('');
}

export function replaceStateRefs(updates) {
  try {
    const hash=mergeStateRefs(location.hash,updates);
    if(hash===null)return;
    const url=new URL(location.href);
    url.hash=hash;
    history.replaceState(history.state,'',url);
  } catch(error) {console.warn('PUI: could not update URL options:',error.message);}
}
