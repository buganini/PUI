// Pyodide maps None to undefined and JS null to jsnull. The shared schema uses
// null/None, so normalize the newly owned records in place at the bridge only.
export function nulls(value,from,to) {
  if(value===from)return to;
  if(Array.isArray(value))for(let i=0;i<value.length;i++)value[i]=nulls(value[i],from,to);
  else if(value && Object.getPrototypeOf(value)===Object.prototype)
    for(const key of Object.keys(value))value[key]=nulls(value[key],from,to);
  return value;
}
