// Uses an existing Playwright installation and Chrome; no browser runtime ships.
const assert = require('node:assert/strict');
const path = require('node:path');
const {createRequire} = require('node:module');
const requireBrowser = process.env.PUI_BROWSER_MODULES
  ? createRequire(path.join(process.env.PUI_BROWSER_MODULES, 'package.json')) : require;
const {chromium} = requireBrowser('playwright');
const {spawnSync} = require('node:child_process');
const url = process.env.PUI_WEB_URL || 'http://localhost:8866/pui/';

(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 const page=await context.newPage(), errors=[], sentFrames=[];
 page.on('websocket',socket=>socket.on('framesent',frame=>sentFrames.push(Buffer.from(frame.payload).toString('base64'))));
 page.on('pageerror',error=>errors.push(error.message));
 page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
 const waitText=async(value)=>page.waitForFunction(v=>document.querySelector('#pui-root').innerText.includes(v),value);
 try {
  await page.goto(url.replace(/\/$/,''));
  await page.getByText('Row 1',{exact:true}).waitFor();
  assert.equal(new URL(page.url()).pathname,'/pui/');
  await page.locator('#pui-status').waitFor({state:'hidden'});
  assert.equal((await page.locator('#pui-root').boundingBox()).y,0);
  await page.getByRole('button',{name:'Button',exact:true}).click();
  await page.getByRole('button',{name:'B',exact:true}).click();
  await page.locator('.pui-Label').filter({hasText:/^B$/}).waitFor();
  await page.getByRole('button',{name:'TextField',exact:true}).click();
  const input=page.locator('input').first();
  await input.waitFor();
  await input.fill('not a number');
  await input.press('Enter');
  await page.waitForFunction(()=>document.querySelector('input').value==='1.23');
  await input.fill('3.5');
  await input.press('Enter');
  await waitText('State:3.5');
  assert.equal(await input.inputValue(),'3.5');
  const editor=page.locator('input').nth(1);
  await editor.fill('4.5');
  await waitText('Editing:4.5');
  assert.equal(await editor.inputValue(),'4.5');
  await editor.press('Enter');
  await waitText('State:4.5');
  await input.fill('8');
  await page.getByRole('button',{name:'Set something',exact:true}).click();
  await waitText('State:something'); // blur commits before the button's callback
  const resume=await page.evaluate(()=>sessionStorage.getItem('pui:resume:'+location.pathname));
  await page.reload();
  await page.getByRole('button',{name:'Set something',exact:true}).waitFor();
  await waitText('State:something');
  await page.locator('#pui-status').waitFor({state:'hidden'});
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('pui:resume:'+location.pathname)),resume);
  await page.locator('input').first().fill('6.5');
  await page.locator('input').first().press('Enter');
  await waitText('State:6.5'); // edit sequences restart under the new connection epoch
  const other=await context.newPage();
  await other.goto(url); await other.getByText('Row 1',{exact:true}).waitFor();
  assert.notEqual(await other.evaluate(()=>sessionStorage.getItem('pui:resume:'+location.pathname)),resume);
  await other.close();
  await page.getByRole('button',{name:'Table',exact:true}).click();
  await page.getByText('Not Supported for this backend',{exact:true}).waitFor();
  await page.getByRole('button',{name:'State Binding',exact:true}).click();
  await page.locator('input').waitFor();
  const beforeInput=sentFrames.length;
  await page.locator('input').fill('中文');
  const inputActions=await page.evaluate(async frames=>{
   const {decodeMessage}=await import(document.querySelector('script[type=module]').src);
   return frames.map(frame=>decodeMessage(Uint8Array.from(atob(frame),c=>c.charCodeAt(0))).type)
    .filter(type=>type==='event' || type==='binding_write');
  },sentFrames.slice(beforeInput));
  assert.deepEqual(inputActions,[]); // a model-only field keeps typing entirely local
  await page.locator('input').press('Tab');
  await waitText('var: 中文');
  // Cross-language framing fixture with Unicode, binary, null and exact integers.
  const python=process.env.PUI_PYTHON || 'env/bin/python';
  const encoded=spawnSync(python,['-c',
   "from PUI.web.protocol import Codec; import base64; print(base64.b64encode(Codec().encode({'v':1,'type':'event','session':'test','seq':1,'body':{'values':[None,True,1,1.5,'中文',b'\\x00\\xff',9007199254740991], 'object_id':'18446744073709551615'}})).decode())"],{encoding:'utf8'});
  assert.equal(encoded.status,0,encoded.stderr);
  const roundtrip=await page.evaluate(async base64=>{
   const source=document.querySelector('script[type=module]').src;
   const {decodeMessage,encodeMessage}=await import(source);
   const bytes=Uint8Array.from(atob(base64.trim()),c=>c.charCodeAt(0));
   const value=decodeMessage(bytes);
   if(value.body.values[4]!=='中文' || value.body.values[5][1]!==255)throw new Error('Codec mismatch');
   for(const invalid of [new Uint8Array([...bytes,...bytes]),bytes.slice(0,-1)]) {
    let rejected=false;try{decodeMessage(invalid);}catch{rejected=true;}if(!rejected)throw new Error('Invalid frame accepted');
   }
   const result=encodeMessage(value);
   return btoa(String.fromCharCode(...result));
  },encoded.stdout);
  const decoded=spawnSync(python,['-c',
   "from PUI.web.protocol import Codec; import base64,sys; v=Codec().decode(base64.b64decode(sys.argv[1])); assert v['body']['values'][5]==b'\\x00\\xff'; assert v['body']['values'][6]==9007199254740991; print('roundtrip ok')",roundtrip],{encoding:'utf8'});
  assert.equal(decoded.status,0,decoded.stderr);
  const malformed=spawnSync(python,['-c',"import runpy; runpy.run_path('tests/web_codec_fixtures.py', run_name='__main__')"],{encoding:'utf8'});
  assert.equal(malformed.status,0,malformed.stderr);
  await page.evaluate(async fixtures=>{
   const {decodeMessage,validateServerBody}=await import(document.querySelector('script[type=module]').src);
   for(const [name,base64] of Object.entries(fixtures)) {
    let rejected=false;
    try{decodeMessage(Uint8Array.from(atob(base64),c=>c.charCodeAt(0)));}catch{rejected=true;}
    if(!rejected)throw new Error('Malformed frame accepted: '+name);
   }
   for(const [type,body] of [
    ['result',{reply_to:1,status:'processed',code:null}],
    ['render',{mode:'snapshot',base_rev:null,rev:1,processed_seq:1,roots:[],bindings:[],canvases:[]}],
    ['close',{reason:'done'}],
   ]) validateServerBody(type,body);
   for(const [type,body] of [
    ['result',{reply_to:true,status:'processed',code:null}],
    ['result',{reply_to:1,status:'unexpected',code:null}],
    ['result',{reply_to:1,status:'processed',code:'APP_ERROR'}],
    ['render',{mode:'patch',base_rev:2,rev:1,processed_seq:1,ops:[]}],
    ['render',{mode:'snapshot',base_rev:0,rev:1,processed_seq:1,roots:[],bindings:[],canvases:[]}],
    ['ready',{server_build:'test',capabilities:[],limits:{},resume_id:'test',resumed:false,session_ttl:900}],
    ['error',{code:'APP_ERROR',reply_to:1,fatal:1,message:'bad'}],
    ['close',{reason:1}], ['event',{}],
   ]) {
    let rejected=false;try{validateServerBody(type,body);}catch{rejected=true;}
    if(!rejected)throw new Error('Malformed body accepted: '+type);
   }
  },JSON.parse(malformed.stdout));
  assert.deepEqual(errors,[]);
  // Hold each connection's first snapshot to check that ready alone does not
  // hide loading/reconnection status. All frames still come from the server.
  const statusPage=await context.newPage();
  let connection, snapshotReady;
  const nextSnapshot=()=>new Promise((resolve,reject)=>{
   const timeout=setTimeout(()=>reject(new Error('Timed out waiting for a snapshot')),10000);
   snapshotReady=release=>{clearTimeout(timeout);resolve(release);};
  });
  let snapshot=nextSnapshot();
  await statusPage.routeWebSocket('**/pui/ws',route=>{
   const server=route.connectToServer();
   let received=0;
   connection={route,server};
   server.onMessage(message=>{
    if(++received===2)snapshotReady(()=>route.send(message));
    else route.send(message);
   });
  });
  await statusPage.goto(url);
  let release=await snapshot;
  const banner=statusPage.locator('#pui-status');
  await statusPage.getByText('Connected',{exact:true}).waitFor();
  assert.equal(await banner.isVisible(),true);
  assert.equal(await statusPage.getByText('Row 1',{exact:true}).count(),0);
  release();
  await statusPage.getByText('Row 1',{exact:true}).waitFor();
  await banner.waitFor({state:'hidden'});
  snapshot=nextSnapshot();
  connection.server.onClose(()=>{});
  await connection.server.close({code:3001});
  await connection.route.close({code:1012,reason:'Restart for reconnect test'});
  await statusPage.getByText('Disconnected · reconnecting without replaying pending actions…',{exact:true}).waitFor();
  release=await snapshot;
  await statusPage.getByText('Connected · session resumed',{exact:true}).waitFor();
  assert.equal(await banner.isVisible(),true);
  release();
  await banner.waitFor({state:'hidden'});
  assert.equal((await statusPage.locator('#pui-root').boundingBox()).y,0);
  connection.server.onClose(()=>{});
  await connection.server.close({code:3001});
  await connection.route.close({code:1008,reason:'Test connection refused'});
  await statusPage.getByText('Disconnected: Test connection refused',{exact:true}).waitFor();
  assert.equal(await banner.isVisible(),true);
  await statusPage.close();
  console.log('Web browser checks passed: prefix, codecs/malformed frames, body schemas, navigation, edits, callback ordering, resumption, tab isolation, connection banner visibility.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
