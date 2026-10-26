// Actual browser Python: no application server, WebSocket or codec runtime.
const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES?
  createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=requireBrowser('playwright');
const url=process.env.PUI_PYODIDE_URL || 'http://localhost:8868/cookbook/cookbook.html';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const context=await browser.newContext({viewport:{width:1600,height:1050}}),page=await context.newPage();
  page.setDefaultTimeout(45000);
  const errors=[],requests=[];let sockets=0;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'){errors.push(m.text());console.error(m.text());}});
  page.on('request',r=>requests.push(r.url()));page.on('websocket',()=>sockets++);
  await page.addInitScript(()=>{
   window.bridge=[];window.workers=[];window.blobs=new Set();
   const W=Worker,create=URL.createObjectURL,revoke=URL.revokeObjectURL;
   URL.createObjectURL=function(...args){const url=create.apply(this,args);window.blobs.add(url);return url;};
   URL.revokeObjectURL=function(url){window.blobs.delete(url);return revoke.call(this,url);};
   window.Worker=class extends W {
    constructor(...args){super(...args);window.workers.push(this);this.addEventListener('message',({data:m})=>{
     window.bridge.push({type:m.type,epoch:m.epoch,seq:m.seq,mode:m.body?.mode,
       ops:m.body?.ops?.filter(o=>o.op.includes('canvas')).map(o=>({op:o.op,start:o.start,count:o.frame?.commands.length}))});
    });}
    postMessage(m,...rest){window.lastSent=m;super.postMessage(m,...rest);}
   };
  });
  const started=Date.now();await page.goto(url);
  await page.getByRole('button',{name:'Vbox',exact:true}).waitFor({timeout:180000});
  console.log(`First interactive: ${Date.now()-started} ms`);
  const select=async name=>{
   const offset=await page.evaluate(()=>window.bridge.length);
   await page.getByRole('button',{name,exact:true}).click();
   await page.waitForFunction(offset=>window.bridge.slice(offset).some(m=>m.type==='render'),offset);
  };
  // All advertised pages must construct successfully in the worker.
  for(const name of ['Vbox','HBox','Stack','Grid','Label','Button','Checkbox','RadioButton','Combobox',
    'ProgressBar','TextField','MaskedField','Scroll','Canvas','Image','Tab','Views','Table','Table(Adapter)','State & Binding']){
   await select(name);
   await page.waitForFunction(()=>document.querySelector('#pui-root')?.inert===false && document.querySelector('#pui-status').hidden);
  }
  await select('Button');await page.getByRole('button',{name:'B',exact:true}).click();
  await page.locator('.pui-Label').getByText('B',{exact:true}).waitFor();
  await select('Combobox');const input=page.locator('input[list]').last();
  await input.fill('Taipei Taoyuan (TPE)');await input.press('Enter');
  await page.getByText('Autocomplete value: TPE',{exact:true}).waitFor();
  await input.fill('Free text');await input.press('Tab');
  await page.getByText('Autocomplete value: Free text',{exact:true}).waitFor();
  await select('Table');await page.locator('td select').first().selectOption({label:'8'});
  await page.getByText('Sides: 8',{exact:true}).waitFor();
  await page.locator('td').getByText('A1: A1',{exact:true}).dblclick();
  await page.locator('td input').fill('browser');await page.locator('td input').press('Enter');
  await page.locator('.pui-Label').getByText('A1: browser',{exact:true}).waitFor();
  await select('Views');await page.getByRole('button',{name:'Editor',exact:true}).click();
  await page.getByRole('button',{name:'Change text',exact:true}).first().click();
  await page.getByText('Saved text: retained draft',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Settings',exact:true}).click();
  await page.getByRole('button',{name:'Editor',exact:true}).click();
  assert.equal(await page.locator('input:visible').first().inputValue(),'retained draft');
  await select('TimelineView');
  const stamp=page.locator('.pui-Label').filter({hasText:/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/});
  await stamp.waitFor();const before=await stamp.textContent();
  await page.waitForFunction(old=>![...document.querySelectorAll('.pui-Label')].some(e=>e.textContent===old),before);
  await select('Image');await page.waitForFunction(()=>document.querySelector('.pui-Image')?.naturalWidth>0);
  assert.match(await page.locator('.pui-Image').getAttribute('src'),/^blob:/);
  await select('HeavyCanvas');const bitmap=page.locator('.pui-Canvas canvas');
  await page.waitForFunction(()=>document.querySelector('.pui-Canvas canvas')?.width>0);
  for(const count of ['1000','3000','5000','7500','10000','15000','20000','25000','30000']) {
   await page.getByRole('combobox').selectOption({label:count});
   await page.getByText(new RegExp(Number(count).toLocaleString('en-US')+' sessions \\| Seed 42')).waitFor();
   const box=await bitmap.boundingBox();let old=await bitmap.evaluate(c=>c.toDataURL());
   await page.mouse.move(box.x+box.width*.4,box.y+100);
   await page.waitForFunction(old=>document.querySelector('.pui-Canvas canvas').toDataURL()!==old,old);
   old=await bitmap.evaluate(c=>c.toDataURL());
   await page.mouse.move(box.x+box.width*.6,box.y+110);
   await page.waitForFunction(old=>document.querySelector('.pui-Canvas canvas').toDataURL()!==old,old);
  }
  await page.mouse.wheel(0,-400);
  await page.waitForFunction(()=>[...document.querySelectorAll('.pui-Label')].some(e=>
    e.textContent.startsWith('Visible:') && !e.textContent.endsWith('Zoom 1.00x')));
  await page.getByRole('button',{name:'Reset zoom',exact:true}).click();
  const ops=await page.evaluate(()=>window.bridge.flatMap(m=>m.ops||[]));
  assert(ops.some(o=>o.op==='put_canvas' && o.count>50000));
  assert(ops.some(o=>o.op==='patch_canvas' && o.start>50000 && o.count<30));
  assert.equal(sockets,0);assert(!requests.some(u=>/zstd|msgpack/.test(u)));
  assert.deepEqual(errors.filter(e=>!e.includes('404')),[]);
  const firstEpoch=await page.evaluate(()=>window.bridge.find(m=>m.type==='ready').epoch);
  await page.getByRole('button',{name:'Restart Python',exact:true}).click();
  await page.getByText('Row 1',{exact:true}).waitFor({timeout:180000});
  assert.notEqual(await page.evaluate(()=>window.bridge.filter(m=>m.type==='ready').at(-1).epoch),firstEpoch);
  assert.equal(await page.evaluate(()=>window.blobs.size),0);
  await select('Button');await page.locator('.pui-Label').getByText('A',{exact:true}).waitFor();
  // Retired/duplicate input must fail visibly rather than dispatch a second callback.
  await page.evaluate(()=>window.workers.at(-1).postMessage(window.lastSent));
  await page.getByRole('status').filter({hasText:'Invalid worker epoch or sequence'}).waitFor();
  await page.getByRole('button',{name:'Restart Python',exact:true}).click();
  await page.getByText('Row 1',{exact:true}).waitFor({timeout:180000});
  await page.screenshot({path:process.env.PUI_SCREENSHOT || '/tmp/pui-pyodide-cookbook.png'});
  console.log('Pyodide: controls, tables, Views, timers, Blob images, 1,000–30,000-session HeavyCanvas, zoom, deltas, restart and duplicate rejection passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
