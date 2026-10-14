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
  assert.equal(await page.locator('#pui-status').innerText(),'Connected');
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
  assert.equal(await page.locator('#pui-status').innerText(),'Connected · session resumed');
  assert.equal(await page.evaluate(()=>sessionStorage.getItem('pui:resume:'+location.pathname)),resume);
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
  assert.deepEqual(errors,[]);
  console.log('Web browser checks passed: prefix, codecs, navigation, edits, callback ordering, resumption, tab isolation.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
