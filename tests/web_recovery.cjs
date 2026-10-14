// Real gateway/client recovery, with test-only DOM failure and delayed frames.
const assert=require('node:assert/strict');
const path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');

(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(), errors=[], sent=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  let heldPatch=null, heldSnapshot=null, holdPatch=false, holdSnapshot=false;
  let forwarded=Promise.resolve();
  await page.routeWebSocket('**/pui/ws',route=>{
   const server=route.connectToServer();
   route.onMessage(frame=>{sent.push(Buffer.from(frame).toString('base64'));server.send(frame);});
   server.onMessage(frame=>{
    forwarded=forwarded.then(async()=>{
     const message=await page.evaluate(async base64=>{
      const {decodeMessage}=await import(document.querySelector('script[type=module]').src);
      return decodeMessage(Uint8Array.from(atob(base64),c=>c.charCodeAt(0)));
     },Buffer.from(frame).toString('base64'));
     if(message.type==='render' && message.body.mode==='patch' && holdPatch){
      holdPatch=false;
      await new Promise(resolve=>{heldPatch={message,release:()=>{route.send(frame);resolve();}};});
     }else if(message.type==='render' && message.body.mode==='snapshot' && holdSnapshot){
      holdSnapshot=false;
      await new Promise(resolve=>{heldSnapshot={message,release:()=>{route.send(frame);resolve();}};});
     }else route.send(frame);
    }).catch(error=>errors.push(error.message));
   });
  });
  const waitFor=async predicate=>{
   const deadline=Date.now()+10000;
   while(!predicate()){
    if(errors.length)throw new Error(errors.join('\n'));
    if(Date.now()>deadline)throw new Error('Timed out waiting for an intercepted render');
    await new Promise(resolve=>setTimeout(resolve,10));
   }
  };
  const messages=()=>page.evaluate(async frames=>{
   const {decodeMessage}=await import(document.querySelector('script[type=module]').src);
   return frames.map(frame=>decodeMessage(Uint8Array.from(atob(frame),c=>c.charCodeAt(0))));
  },sent);
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await page.getByText('Row 1',{exact:true}).waitFor();
  await page.getByRole('button',{name:'TextField',exact:true}).click();
  await page.locator('input').first().waitFor();
  await page.evaluate(()=>{
   const labels=[...document.querySelectorAll('.pui-Label')].filter(e=>e.textContent==='State:1.23');
   if(labels.length!==2)throw new Error('Missing fixture labels');
   const target=labels[1], descriptor=Object.getOwnPropertyDescriptor(Node.prototype,'textContent');
   window.recoveryInput=document.querySelector('input');
   Object.defineProperty(target,'textContent',{configurable:true,
    get(){return descriptor.get.call(this);},set(value){
     delete this.textContent;window.recoveryFaultFired=true;
     throw new Error('Injected partial DOM failure');
    }});
  });
  holdPatch=holdSnapshot=true;
  await page.getByRole('button',{name:'Set something',exact:true}).click();
  await waitFor(()=>heldPatch!==null);
  // Typing ahead of the delayed patch must survive recovery. Only input is
  // sent here, so the server's committed model remains "something".
  const input=page.locator('input').first();
  await input.fill('surviving draft');
  await input.evaluate(e=>e.setSelectionRange(2,5));
  heldPatch.release();
  await waitFor(()=>heldSnapshot!==null);
  await page.getByText('Recovering view…',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>window.recoveryFaultFired),true);
  assert.equal(await page.locator('.pui-Label').filter({hasText:/^State:something$/}).count(),1);
  const before=await messages();
  const discard=before.findIndex(m=>m.type==='ack' && m.body.render_rev===heldPatch.message.body.rev);
  assert.ok(discard>=0);
  assert.deepEqual(before[discard].body,{render_rev:heldPatch.message.body.rev,
   applied_rev:heldPatch.message.body.base_rev,status:'discarded'});
  assert.equal(before[discard+1].type,'resync');
  assert.equal(before[discard+1].body.last_applied_rev,heldPatch.message.body.base_rev);
  assert.equal(heldSnapshot.message.session,heldPatch.message.session);
  assert.ok(heldSnapshot.message.body.rev>heldPatch.message.body.rev);
  const clicks=before.filter(m=>m.type==='event' && m.body.event==='click').length;
  await page.getByRole('button',{name:'Clear',exact:true}).dispatchEvent('click');
  assert.equal((await messages()).filter(m=>m.type==='event' && m.body.event==='click').length,clicks);
  heldSnapshot.release();
  await page.locator('#pui-status').waitFor({state:'hidden'});
  assert.equal(await page.locator('.pui-Label').filter({hasText:/^State:something$/}).count(),2);
  assert.equal(await input.inputValue(),'surviving draft');
  assert.equal(await input.evaluate(e=>e===window.recoveryInput && document.activeElement===e &&
   e.selectionStart===2 && e.selectionEnd===5),true);
  const recovered=await messages();
  assert.ok(recovered.some(m=>m.type==='ack' && m.body.render_rev===heldSnapshot.message.body.rev && m.body.status==='applied'));
  await input.press('Enter');
  await page.waitForFunction(()=>[...document.querySelectorAll('.pui-Label')]
   .filter(e=>e.textContent==='State:surviving draft').length===2);
  assert.deepEqual(errors,[]);
  // An invalid binary frame must end the connection visibly, without throwing
  // another exception from the browser's restricted WebSocket.close() API.
  const broken=await browser.newPage(), fatalErrors=[], fatalLogs=[];
  let clientRoute, closedCode=null, connections=0;
  broken.on('pageerror',error=>fatalErrors.push(error.message));
  broken.on('console',message=>{if(message.type()==='error')fatalLogs.push(message.text());});
  await broken.routeWebSocket('**/pui/ws',route=>{
   connections++;clientRoute=route;
   const server=route.connectToServer();
   route.onClose((code,reason)=>{if(closedCode===null)closedCode=code;server.close({code,reason});});
  });
  await broken.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await broken.getByText('Row 1',{exact:true}).waitFor();
  await broken.locator('#pui-status').waitFor({state:'hidden'});
  clientRoute.send(Buffer.from([0]));
  await waitFor(()=>closedCode!==null);
  assert.equal(closedCode,4002);
  await broken.getByText(/^Connection error:/).waitFor();
  // Cover the first automatic retry interval; fatal errors require a reload.
  await new Promise(resolve=>setTimeout(resolve,750));
  assert.equal(connections,1);
  assert.deepEqual(fatalErrors,[]);
  assert.equal(fatalLogs.length,1);
  console.log('Web transport recovery passed: discarded ACK/resync ordering, same-session snapshot, paused actions, retained draft/focus, resumed editing and visible fatal shutdown.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
