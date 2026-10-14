// Block server replies while keeping the real browser/server connection alive.
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
  const page=await browser.newPage(), errors=[], held=[], sent=[];
  let stall=false, routeToPage, connections=0, closedCode=null;
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  await page.routeWebSocket('**/pui/ws',route=>{
   connections++;routeToPage=route;
   const server=route.connectToServer();
   route.onMessage(frame=>{sent.push(Buffer.from(frame).toString('base64'));server.send(frame);});
   server.onMessage(frame=>{if(stall)held.push(frame);else route.send(frame);});
   route.onClose((code,reason)=>{
    if(closedCode===null)closedCode=code;
    // Deliberately flush replies that were already in flight after the client
    // stops. They must not drain queued callbacks or overwrite the error.
    for(const frame of held)route.send(frame);
    held.length=0;server.close({code,reason});
   });
  });
  const waitFor=async predicate=>{
   const deadline=Date.now()+10000;
   while(!predicate()){
    if(Date.now()>deadline)throw new Error('Timed out waiting for backpressure');
    await new Promise(resolve=>setTimeout(resolve,10));
   }
  };
  const actions=()=>page.evaluate(async values=>{
   const {decodeMessage}=await import(document.querySelector('script[type=module]').src);
   return values.map(value=>decodeMessage(Uint8Array.from(atob(value),c=>c.charCodeAt(0))))
    .filter(m=>m.type==='event' || m.type==='binding_write');
  },sent);
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await page.getByText('Row 1',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Button',exact:true}).click();
  const button=page.getByRole('button',{name:'B',exact:true});await button.waitFor();
  const baseline=(await actions()).length;
  stall=true;
  await button.evaluate(element=>{for(let i=0;i<320;i++)element.click();});
  await waitFor(()=>held.length>=64);
  assert.equal((await actions()).length-baseline,64);
  assert.equal(closedCode,null);
  // Release one action result, granting exactly one additional action credit.
  routeToPage.send(held.shift());
  await waitFor(()=>held.length>=65);
  assert.equal((await actions()).length-baseline,65);
  // One queued slot was freed. The second click now exceeds the 256-slot cap.
  await button.evaluate(element=>{element.click();element.click();element.click();});
  await waitFor(()=>closedCode!==null);
  assert.equal(closedCode,4008);
  await page.getByText('Input queue is full; reload to continue.',{exact:true}).waitFor();
  await new Promise(resolve=>setTimeout(resolve,750));
  assert.equal((await actions()).length-baseline,65);
  assert.equal(connections,1);
  assert.deepEqual(errors,[]);
  console.log('Web backpressure passed: 64 pending actions, one-credit drain, bounded local queue, no late-reply drain and visible non-retrying shutdown.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
