// Pure URL synchronization tests: no browser or transport dependencies.
const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');

(async()=>{
  const {parseOptions,mergeStateRefs,replaceStateRefs}=await import(pathToFileURL(
    path.resolve(__dirname,'../browser-client/web/options.js')));
  const warnings=[],warn=(...args)=>warnings.push(args);
  assert.deepEqual(parseOptions('#a=1#a=2#text=%22hello%20%23%3D%E4%B8%96%E7%95%8C%22#null=null'),
    [['a','2'],['text','"hello #=世界"'],['null','null']]);
  assert.deepEqual(parseOptions('#text=unquoted#badpercent=%zz#missing#ok=true',warn),
    [['text','unquoted'],['ok','true']]);
  assert.equal(warnings.length,2);
  assert.deepEqual(parseOptions('#page=Button#empty=#number=00123#bool=false#csv=a,b,c#object=%7B%22a%22%3A1%7D'),
    [['page','Button'],['empty',''],['number','00123'],['bool','false'],['csv','a,b,c'],['object','{"a":1}']]);
  assert.equal(mergeStateRefs('#a=1#obj=%7B%22x%22:1,%22y%22:2%7D',
    [['obj','{"x":1,"y":2}'],['a','1']]),null);
  assert.equal(mergeStateRefs('#obj=%7B%22x%22:1,%22y%22:2%7D',[['obj','{"y":2,"x":1}']]),
    '#obj=%7B%22y%22%3A2%2C%22x%22%3A1%7D');
  assert.equal(mergeStateRefs('#a=1',[['a','2'],['a','1']]),null);
  assert.equal(mergeStateRefs('#a=1#unsubscribed=3',[['a','2'],['new','[1,2]']]),
    '#a=2#unsubscribed=3#new=%5B1%2C2%5D');
  assert.equal(mergeStateRefs('#a=%5B1,2%5D',[['a','[2,1]']]),'#a=%5B2%2C1%5D');
  assert.equal(mergeStateRefs('#a=1',[]),null);
  assert.equal(mergeStateRefs('#page=%22Button%22',[['page','"Button"']]),'#page=Button');
  assert.equal(mergeStateRefs('#page=Button',[['page','"Button"']]),null);
  assert.equal(mergeStateRefs('#page=Button#keep=unquoted',[['page','"State Binding"']]),
    '#page=State%20Binding#keep=unquoted');
  for(const text of ['', '123', 'true', 'null', '世界 #=&', '"quoted"', '[1,2]', '{"x":1}', 'a,b,c', '{bad']) {
    const expected='#text='+encodeURIComponent(text);
    assert.equal(mergeStateRefs('',[['text',JSON.stringify(text)]]),expected);
    assert.equal(mergeStateRefs(expected,[['text',JSON.stringify(text)]]),null);
    assert.deepEqual(parseOptions(expected),[['text',text]]);
  }
  assert.equal(mergeStateRefs('',[['__proto__','{"polluted":true}']]),
    '#__proto__=%7B%22polluted%22%3Atrue%7D');
  assert.equal({}.polluted,undefined);
  global.location={hash:'#a=1#keep=true',href:'https://example.com/pui/?query=yes#a=1#keep=true'};
  let calls=[];
  global.history={state:{router:'preserved'},replaceState(...args){calls.push(args);location.hash=args[2].hash;}};
  replaceStateRefs([['a','1']]);
  assert.equal(calls.length,0);
  replaceStateRefs([['a','2'],['other','"text"']]);
  assert.equal(calls.length,1);
  assert.equal(calls[0][0],history.state);
  assert.equal(calls[0][2].href,'https://example.com/pui/?query=yes#a=2#keep=true#other=text');
  replaceStateRefs([['a','2'],['other','"text"']]);
  assert.equal(calls.length,1);
  console.log('String URL Options parsing, ordered merge, exact comparison and replaceState passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
