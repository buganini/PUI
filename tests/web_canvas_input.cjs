const login=require('./web_login.cjs');
const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
  await page.getByRole('button',{name:'Button',exact:true}).click();
  await page.evaluate(async()=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const host=document.createElement('div');host.id='canvas-input-test';host.style.cssText='position:fixed;inset:0;display:flex;background:white;';document.body.append(host);
   const events=[],r=new Renderer(host,(kind,body,sent)=>{events.push({kind,body});sent?.(events.length);});
   const node=(id,type,props={},children=[])=>({id,type,props,children,layout:{},style:{},events:{},bindings:{}});
   const ref={object_id:'42',kind:'attr',key:'text'},slot={ref,token:'slot',value_rev:1,value:''};
   const editor=node('input','TextField',{text:'',placeholder:''});editor.bindings.model={ref,slot_token:'slot',token:'editor',writable:true};
   const canvas=node('canvas','Canvas');canvas.layout={width:100,height:100};
   for(const event of ['click','dblclick','mousedown','mouseup','mousemove','mouseenter','mouseleave','wheel'])canvas.events[event]=event;
   const root=node('root','Window',{title:'Canvas input'},[editor,canvas]);let rev=0;
   const apply=()=>r.apply({mode:'snapshot',base_rev:null,rev:++rev,processed_seq:0,roots:[root],bindings:[slot],canvases:[]});apply();
   window.canvasTest={events,r,canvas,root,apply};
  });
  const canvas=page.locator('#canvas-input-test .pui-Canvas'),editor=page.locator('#canvas-input-test input');
  await editor.fill('uncommitted');
  const box=await canvas.boundingBox();
  await page.mouse.move(box.x+10,box.y+10);
  assert.equal(await page.evaluate(()=>canvasTest.events.filter(e=>e.kind==='binding_write').length),0);
  await page.keyboard.down('Control');await page.mouse.down();
  await page.mouse.move(box.x+150,box.y+20,{steps:8});await page.mouse.up();await page.keyboard.up('Control');
  const actions=await page.evaluate(()=>canvasTest.events);
  const down=actions.findIndex(e=>e.body.event==='mousedown'),commit=actions.findIndex(e=>e.kind==='binding_write');
  assert.ok(commit>=0 && commit<down);assert.equal(actions[commit].body.value,'uncommitted');
  assert.equal(actions[down].body.data.button,1);assert.equal(actions[down].body.data.modifiers,2);
  const moves=actions.filter(e=>e.body.event==='mousemove' && e.body.data.buttons===1);
  assert.ok(moves.length>=8);assert.ok(moves.some(e=>e.body.data.x>100));
  const up=actions.find(e=>e.body.event==='mouseup');assert.ok(up.body.data.x>100);assert.equal(up.body.data.cancelled,false);
  await page.mouse.move(box.x+20,box.y+20);await page.mouse.down();
  await page.mouse.move(box.x+25,box.y+25); // activate the pending pointer capture
  await page.evaluate(()=>{
   const r=canvasTest.r.canvases.records.get('canvas'),id=[...r.pointers.keys()][0];r.element.releasePointerCapture(id);
  });
  await page.mouse.move(box.x+150,box.y+20);await page.mouse.up();
  await page.waitForFunction(()=>canvasTest.events.some(e=>e.body.event==='mouseup' && e.body.data.cancelled));
  const clicksBefore=await page.evaluate(()=>canvasTest.events.filter(e=>e.body.event==='click').length);
  await canvas.dblclick({position:{x:30,y:30}});
  const clicked=await page.evaluate(()=>canvasTest.events.filter(e=>['click','dblclick'].includes(e.body.event)));
  assert.equal(clicked.filter(e=>e.body.event==='click').length,clicksBefore+2);
  assert.equal(clicked.filter(e=>e.body.event==='dblclick').length,1);
  assert.ok(clicked.every(e=>Number.isFinite(e.body.data.x) && Number.isFinite(e.body.data.y)));
  const results=await page.evaluate(()=>{
   const e=canvasTest.r.elements.get('canvas'),results=[];
   for(let mode=0;mode<3;mode++)results.push(e.dispatchEvent(new WheelEvent('wheel',{
    deltaX:2,deltaY:-3,deltaMode:mode,clientX:20,clientY:30,altKey:true,cancelable:true,bubbles:true})));
   const modes=canvasTest.events.filter(e=>e.body.event==='wheel').map(e=>e.body.data);
   const touch=e.style.touchAction;
   const context=e.dispatchEvent(new MouseEvent('contextmenu',{bubbles:true,cancelable:true}));
   canvasTest.canvas.events={};canvasTest.apply();
   const count=canvasTest.events.length;
   e.dispatchEvent(new PointerEvent('pointerdown',{pointerId:777,button:0,buttons:1,bubbles:true}));
   const allowed=e.dispatchEvent(new WheelEvent('wheel',{deltaY:2,cancelable:true}));
   const after=canvasTest.events.length;
   const restored=e.style.touchAction;
   canvasTest.r.destroy();document.querySelector('#canvas-input-test').remove();
   return {results,modes,touch,context,allowed,count,after,restored};
  });
  assert.deepEqual(results.results,[false,false,false]);
  assert.deepEqual(results.modes.map(e=>e.delta_mode),['pixel','line','page']);
  assert.ok(results.modes.every(e=>e.delta_x===2 && e.delta_y===-3 && e.modifiers===4));
  assert.equal(results.touch,'none');assert.equal(results.context,true);
  assert.equal(results.allowed,true);assert.equal(results.count,results.after);assert.equal(results.restored,'');
  assert.deepEqual(errors,[]);console.log('Canvas input: real captured drag/release outside, commit ordering, ordered samples, modifiers, capture cancellation, raw wheel units/defaults and handler removal passed.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
