const assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const path=require('node:path');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(),errors=[],packets=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('websocket',ws=>ws.on('framereceived',f=>packets.push(Buffer.from(f.payload).toString('base64'))));
  await page.goto(process.env.PUI_IMAGE_URL || 'http://127.0.0.1:8869/pui/');
  await page.waitForFunction(()=>document.querySelector('.pui-Image')?.naturalWidth===4);
  const src=await page.locator('.pui-Image').getAttribute('src');assert.match(src,/\?mtime=\d+$/);
  await page.waitForFunction(()=>{
    const c=document.querySelector('canvas');return c && c.width>60 && c.getContext('2d').getImageData(60,10,1,1).data[2]===255;
  });
  const pixels=await page.locator('canvas').evaluate(c=>[ [10,10],[30,10],[60,10],[85,5] ].map(([x,y])=>[...c.getContext('2d').getImageData(x,y,1,1).data]));
  assert.deepEqual(pixels.slice(0,3),[[255,0,0,255],[0,0,255,255],[0,0,255,255]]);
  assert.equal(pixels[3][0],255);assert.ok(Math.abs(pixels[3][3]-128)<=1);
  await page.getByRole('button',{name:'Repaint',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('canvas').getContext('2d').getImageData(115,65,1,1).data[1]===255);
  assert.deepEqual(await page.locator('canvas').evaluate(c=>[[10,10],[30,10],[60,10]].map(([x,y])=>[...c.getContext('2d').getImageData(x,y,1,1).data])),pixels.slice(0,3));
  const splices=await page.evaluate(async packets=>{
   const {StreamDecoder}=await import(document.querySelector('script[type=module]').src),decoder=new StreamDecoder();
   const result=[];
   for(const packet of packets){
    const m=decoder.decode(Uint8Array.from(atob(packet),c=>c.charCodeAt(0)));
    for(const op of m.body.ops || [])if(op.op==='patch_canvas')result.push(op.frame.commands.map(c=>c.op));
   }
   decoder.close();return result;
  },packets);
  assert.deepEqual(splices,[['rect']]);
  const first=await page.request.get(new URL(src,page.url()).href);assert.equal(first.status(),200);
  const cached=await page.request.get(new URL(src,page.url()).href,{headers:{'If-None-Match':first.headers().etag}});
  assert.equal(cached.status(),304);
  const foreign=await browser.newContext();
  assert.equal((await foreign.request.get(new URL(src,page.url()).href)).status(),404);await foreign.close();
  await page.getByRole('button',{name:'Toggle images'}).click();await page.locator('.pui-Image').waitFor({state:'detached'});
  await page.waitForFunction(async src=>(await fetch(src)).status===404,src);
  await page.getByRole('button',{name:'Toggle images'}).click();await page.locator('.pui-Image').waitFor();
  await page.reload();await page.getByRole('button',{name:'Resume session',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.pui-Image')?.naturalWidth===4);
  const resumedSrc=await page.locator('.pui-Image').getAttribute('src');
  await page.getByRole('button',{name:'Toggle images'}).click();await page.locator('.pui-Image').waitFor({state:'detached'});
  await page.waitForFunction(async src=>(await fetch(src)).status===404,resumedSrc);
  let release,seen;
  const held=new Promise(resolve=>{release=resolve;}), requested=new Promise(resolve=>{seen=resolve;});
  await page.route('**/pui/images/**',async route=>{seen();await held;await route.fulfill({status:404,body:'removed'});});
  await page.getByRole('button',{name:'Toggle images'}).click();await requested;
  const heldSrc=await page.locator('.pui-Image').getAttribute('src');
  // A pending image decode must not hold DOM acknowledgements or button events.
  await page.getByRole('button',{name:'Toggle images'}).click();await page.locator('.pui-Image').waitFor({state:'detached'});
  release();await page.unrouteAll({behavior:'wait'});
  await page.waitForFunction(async src=>(await fetch(src)).status===404,heldSrc);
  await page.route('**/pui/images/**',route=>route.fulfill({status:404,body:'missing'}));
  await page.getByRole('button',{name:'Toggle images'}).click();
  try {await page.locator('.pui-image-error').waitFor({timeout:5000});}
  catch(error){throw Error(error.message+'\nDOM: '+await page.locator('#pui-root').innerHTML()+'\nStatus: '+await page.locator('#pui-status').innerText());}
  await page.getByRole('button',{name:'Toggle images'}).click();await page.locator('.pui-image-error').waitFor({state:'detached'});
  assert.deepEqual(errors,[]);
  console.log('Image browser checks passed: original HTTP image, Canvas crop/scale/opacity pixels, images retained through command splices, 304, ownership, cleanup, reconnect, slow/failed loads without blocking controls.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
