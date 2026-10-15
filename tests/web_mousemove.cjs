// Run against: PYTHONPATH=tests env/bin/python -m PUI.web web_fixture:CanvasInputApp --bind 127.0.0.1:8872 --base-url /pui
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
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8872/pui/');await ready();
  stall=true;
  await emit(moves(1,600));
  await waitFor(()=>held.length>0);
  assert.deepEqual((await actions()).map(m=>m.body.data.x),[1]);
  // Only a result for the in-flight move allows the latest queued move through.
  downstream.send(held.shift());
  await waitFor(async()=>(await actions()).length===2);
  assert.deepEqual((await actions()).map(m=>m.body.data.x),[1,600]);
  await emit([...moves(601,620),{event:'pointerup',x:621},...moves(622,640),
   {event:'wheel',x:641},{event:'wheel',x:642},...moves(643,660),
   ...moves(661,680,{pointer:2}),...moves(681,700,{pointer:2,ctrl:true}),
   ...moves(701,720,{pointer:2,ctrl:true,buttons:1}),...moves(721,740,{canvas:1})]);
  assert.equal((await actions()).length,2);
  stall=false;for(const frame of held.splice(0))downstream.send(frame);
  await page.getByText('a-move:1|a-move:600|a-move:620|a-up:621|a-move:640|a-wheel:641|a-wheel:642|a-move:660|a-move:680|a-move:700|a-move:720|b-move:740|',{exact:true}).waitFor();
  const received=await actions();
  assert.deepEqual(received.map(m=>[m.body.event,m.body.data.x]),[
   ['mousemove',1],['mousemove',600],['mousemove',620],['mouseup',621],['mousemove',640],
   ['wheel',641],['wheel',642],['mousemove',660],['mousemove',680],['mousemove',700],['mousemove',720],['mousemove',740]]);
  assert.equal(received[8].body.data.pointer_id,2);
  assert.equal(received[9].body.data.modifiers,2);
  assert.equal(received[10].body.data.buttons,1);
  assert.notEqual(received[10].body.node_id,received[11].body.node_id);
  // Disconnected moves are discarded; a resumed connection gets a fresh credit.
  stall=true;await emit(moves(30,32));
  await waitFor(()=>held.length>0);
  assert.equal((await actions()).at(-1).body.data.x,30);
  held.length=0;stall=false;
  upstream.onClose(()=>{});
  await upstream.close({code:3001,reason:'Test reconnect'});
  await downstream.close({code:1013,reason:'Test reconnect'});
  await page.getByRole('button',{name:'Resume session',exact:true}).click();
  await waitFor(()=>connections===2);
  try {await ready();} catch(error) {throw Error(error.message+'\nStatus: '+await page.locator('#pui-status').innerText()+'\nErrors: '+errors.join('\n'));}
  await emit(moves(40,41));
  await waitFor(async()=>(await actions()).at(-1).body.data.x===41);
  assert.deepEqual((await actions()).slice(received.length).map(m=>m.body.data.x),[30,40,41]);
  await page.waitForFunction(()=>document.querySelector('.pui-Label')?.textContent.endsWith('a-move:40|a-move:41|'));
  assert.deepEqual(errors,[]);
  console.log('Canvas mousemove: result-gated latest position, 600-event burst, intervening actions, pointer/target/modifier/button boundaries and reconnect reset passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
