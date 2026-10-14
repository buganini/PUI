// Delayed recovery snapshots and duplicate renders over a real gateway session.
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
  const decode=frames=>page.evaluate(async values=>{
   const {decodeMessage}=await import(document.querySelector('script[type=module]').src);
   return values.map(value=>decodeMessage(Uint8Array.from(atob(value),c=>c.charCodeAt(0))));
  },frames);
  let sequence=0, original=null, failed=null, recovery=null, deliver;
  let forwarding=Promise.resolve();
  await page.routeWebSocket('**/pui/ws',route=>{
   const server=route.connectToServer();
   // Insert test retries under fresh envelope sequences without changing the
   // immutable render bodies. Later real server messages keep their order.
   deliver=async message=>{
    const frame=await page.evaluate(async value=>{
     const {encodeMessage}=await import(document.querySelector('script[type=module]').src);
     return btoa(String.fromCharCode(...encodeMessage(value)));
    },{...message,seq:++sequence});
    route.send(Buffer.from(frame,'base64'));
   };
   route.onMessage(frame=>{sent.push(Buffer.from(frame).toString('base64'));server.send(frame);});
   server.onMessage(frame=>{
    forwarding=forwarding.then(async()=>{
     const [message]=await decode([Buffer.from(frame).toString('base64')]);
     if(message.type==='render'){
      if(message.body.mode==='snapshot'){
       if(original===null)original=message;
       else {
        await new Promise(resolve=>{recovery={message,release:async()=>{await deliver(message);resolve();}};});
        return;
       }
      }else if(failed===null)failed=message;
     }
     await deliver(message);
    }).catch(error=>errors.push(error.message));
   });
  });
  const waitFor=async predicate=>{
   const deadline=Date.now()+10000;
   while(!predicate()){
    if(errors.length)throw new Error(errors.join('\n'));
    if(Date.now()>deadline)throw new Error('Timed out waiting for recovery');
    await new Promise(resolve=>setTimeout(resolve,10));
   }
  };
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await page.getByText('Row 1',{exact:true}).waitFor();
  await page.evaluate(()=>{
   const descriptor=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');
   Object.defineProperty(HTMLInputElement.prototype,'value',{...descriptor,set(value){
    Object.defineProperty(HTMLInputElement.prototype,'value',descriptor);
    throw new Error('Injected editor readback failure');
   }});
  });
  await page.getByRole('button',{name:'TextField',exact:true}).click();
  await waitFor(()=>recovery!==null);
  await page.getByText('Recovering view…',{exact:true}).waitFor();
  const before=sent.length;
  for(let i=0;i<4;i++){
   await deliver(original);
   await deliver(failed);
  }
  await waitFor(()=>sent.length>=before+8);
  const replies=await decode(sent);
  const retries=replies.slice(before);
  assert.equal(retries.length,8);
  for(const reply of retries){
   assert.equal(reply.type,'ack');
   assert.equal(reply.body.status,'discarded');
   assert.equal(reply.body.applied_rev,original.body.rev);
  }
  assert.equal(replies.filter(m=>m.type==='resync').length,1);
  await page.getByText('Recovering view…',{exact:true}).waitFor();
  await recovery.release();
  await page.locator('#pui-status').waitFor({state:'hidden'});
  await page.locator('input').first().fill('2.5');
  await page.locator('input').first().press('Enter');
  await page.waitForFunction(()=>document.querySelector('#pui-root').innerText.includes('State:2.5'));
  assert.deepEqual(errors,[]);
  // A genuinely failing recovery must still exhaust its bounded attempts.
  // This page uses the browser's native WebSocket without interception.
  const persistent=await browser.newPage(), pageErrors=[], logs=[], frames=[];
  let closed=false;
  persistent.on('pageerror',error=>pageErrors.push(error.message));
  persistent.on('console',message=>{if(message.type()==='error')logs.push(message.text());});
  persistent.on('websocket',socket=>{
   socket.on('framesent',frame=>frames.push(Buffer.from(frame.payload).toString('base64')));
   socket.on('close',()=>{closed=true;});
  });
  await persistent.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await persistent.getByText('Row 1',{exact:true}).waitFor();
  await persistent.evaluate(()=>{
   const descriptor=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value');
   window.recoveryAttempts=0;
   Object.defineProperty(HTMLInputElement.prototype,'value',{...descriptor,set(){
    window.recoveryAttempts++;
    throw new Error('Injected persistent readback failure');
   }});
  });
  await persistent.getByRole('button',{name:'TextField',exact:true}).click();
  await persistent.getByText('Connection error: Injected persistent readback failure',{exact:true}).waitFor();
  await waitFor(()=>closed);
  assert.equal(await persistent.evaluate(()=>window.recoveryAttempts),4);
  const terminal=await persistent.evaluate(async values=>{
   const {decodeMessage}=await import(document.querySelector('script[type=module]').src);
   return values.map(value=>decodeMessage(Uint8Array.from(atob(value),c=>c.charCodeAt(0))));
  },frames);
  assert.equal(terminal.filter(m=>m.type==='resync').length,3);
  assert.equal(terminal.filter(m=>m.type==='ack' && m.body.status==='discarded').length,4);
  assert.deepEqual(pageErrors,[]);
  assert.equal(logs.length,1);
  console.log('Web recovery ordering passed: obsolete snapshots/patches are discarded, recovery retains its retry budget, and persistent DOM failures stop visibly after three recovery attempts.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
