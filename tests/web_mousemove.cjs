const login=require('./web_login.cjs');
// Run against: PYTHONPATH=tests env/bin/python -m PUI.web web_fixture:CanvasInputApp --bind 127.0.0.1:8872 --mount-path /pui
const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');

(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(),errors=[],sent=[],held=[];
  let stall=false,downstream,upstream,connections=0;
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.routeWebSocket('**/pui/ws',route=>{
   connections++;downstream=route;
   const server=upstream=route.connectToServer();
   route.onMessage(frame=>{sent.push(Buffer.from(frame).toString('base64'));server.send(frame);});
   server.onMessage(frame=>{if(stall)held.push(frame);else route.send(frame);});
  });
  const waitFor=async predicate=>{
   const deadline=Date.now()+10000;
   while(!await predicate()){
    if(errors.length)throw new Error(errors.join('\n'));
    if(Date.now()>deadline)throw new Error('Timed out waiting for Canvas actions');
    await new Promise(resolve=>setTimeout(resolve,10));
   }
  };
  const actions=()=>page.evaluate(async frames=>{
   const {decodeMessage}=await import(document.querySelector('script[type=module]').src);
   return frames.map(frame=>decodeMessage(Uint8Array.from(atob(frame),c=>c.charCodeAt(0))))
    .filter(m=>m.type==='event');
  },sent);
  const emit=specs=>page.evaluate(specs=>{
   const canvases=[...document.querySelectorAll('.pui-Canvas')];
   for(const spec of specs){
    const element=canvases[spec.canvas || 0],rect=element.getBoundingClientRect();
    const init={bubbles:true,cancelable:true,clientX:rect.left+spec.x,clientY:rect.top+10,
     pointerId:spec.pointer || 1,button:-1,buttons:spec.buttons || 0,ctrlKey:!!spec.ctrl};
    const event=spec.event || 'pointermove';
    element.dispatchEvent(event==='wheel'?new WheelEvent(event,{...init,deltaY:1}):new PointerEvent(event,init));
   }
  },specs);
  const moves=(first,last,extra={})=>Array.from({length:last-first+1},(_,i)=>({x:first+i,...extra}));
  const ready=()=>page.waitForFunction(()=>document.querySelectorAll('.pui-Canvas canvas').length===2 &&
   [...document.querySelectorAll('.pui-Canvas canvas')].every(c=>c.width>0) && document.querySelector('#pui-status').hidden);
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8872/pui/');await login(page);await ready();
  stall=true;
  const specs=[...moves(1,100),{event:'pointerup',x:101},{event:'wheel',x:102},
   ...moves(103,110,{pointer:2,ctrl:true}),...moves(111,120,{canvas:1})];
  await emit(specs);
  await waitFor(async()=>(await actions()).length===64 && held.length>0);
  assert.deepEqual((await actions()).map(m=>m.body.data.x),moves(1,64).map(s=>s.x));
  // Results release ordinary action credits; no queued position is replaced.
  stall=false;for(const frame of held.splice(0))downstream.send(frame);
  await waitFor(async()=>(await actions()).length===specs.length);
  const received=await actions();
  assert.deepEqual(received.map(m=>m.body.data.x),specs.map(s=>s.x));
  assert.equal(received[100].body.event,'mouseup');
  assert.equal(received[101].body.event,'wheel');
  assert.equal(received[102].body.data.pointer_id,2);
  assert.equal(received[102].body.data.modifiers,2);
  const expected=specs.map(s=>`${s.canvas?'b':'a'}-${s.event==='pointerup'?'up':s.event==='wheel'?'wheel':'move'}:${s.x}|`).join('');
  await page.getByText(expected,{exact:true}).waitFor();
  // Disconnected moves are discarded; a resumed connection gets a fresh credit.
  stall=true;await emit(moves(30,100));
  await waitFor(()=>held.length>0);
  await waitFor(async()=>(await actions()).at(-1).body.data.x===93);
  held.length=0;
  upstream.onClose(()=>{});
  await upstream.close({code:3001,reason:'Test reconnect'});
  await downstream.close({code:1013,reason:'Test reconnect'});
  held.length=0;stall=false;
  await page.getByRole('button',{name:'Resume session',exact:true}).click();
  await waitFor(()=>connections===2);
  try {await ready();} catch(error) {throw Error(error.message+'\nStatus: '+await page.locator('#pui-status').innerText()+'\nErrors: '+errors.join('\n'));}
  await emit(moves(40,41));
  await waitFor(async()=>(await actions()).at(-1).body.data.x===41);
  assert.deepEqual((await actions()).slice(received.length).map(m=>m.body.data.x),[...moves(30,93).map(s=>s.x),40,41]);
  await page.waitForFunction(()=>document.querySelector('.pui-Label')?.textContent.endsWith('a-move:40|a-move:41|'));
  assert.deepEqual(errors,[]);
  console.log('Canvas mousemove: all samples retained, ordinary action credits, 120-event burst, intervening actions, pointer/target/modifier/button boundaries and reconnect reset passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
