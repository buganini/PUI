const login=require('./web_login.cjs');
// Python-produced splices, browser pixels/atomicity/budgets and live transport.
const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module'),{spawnSync}=require('node:child_process');
const requireBrowser=process.env.PUI_BROWSER_MODULES?
  createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=requireBrowser('playwright');
const result=spawnSync(process.env.PUI_PYTHON || 'env/bin/python',['tests/web_canvas_diff.py','--fixtures'],
  {encoding:'utf8',env:{...process.env,PYTHONPATH:'.:tests'}});
assert.equal(result.status,0,result.stderr);
const fixtures=JSON.parse(result.stdout);
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1600,height:1050}}),errors=[],packets=[];
  page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));
  page.on('websocket',ws=>ws.on('framereceived',f=>packets.push(Buffer.from(f.payload).toString('base64'))));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
  await page.getByRole('button',{name:'HeavyCanvas',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.pui-Canvas canvas')?.width>0);
  const bitmap=page.locator('.pui-Canvas canvas');
  for(const count of ['500','6000']){
   if(count!=='500'){
    await page.getByRole('combobox').selectOption({label:count});
    await page.getByText('6,000 sessions | Seed 42 | ~54,000 draw calls',{exact:true}).waitFor();
   }
   let before=await bitmap.evaluate(c=>c.toDataURL());
   const box=await bitmap.boundingBox();
   for(const x of [.45,.65]){
    await page.mouse.move(box.x+box.width*x,box.y+120);
    await page.waitForFunction(old=>document.querySelector('.pui-Canvas canvas').toDataURL()!==old,before);
    before=await bitmap.evaluate(c=>c.toDataURL());
   }
   await page.mouse.move(0,0);
  }
  // Corrupt one Canvas base at the renderer boundary. The real client must
  // request a full snapshot, recover, and accept subsequent splices.
  await page.evaluate(async()=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const original=Renderer.prototype.apply;
   window.canvasDeltaRecovery={rejected:false,recovered:false};
   Renderer.prototype.apply=function(body){
    const progress=window.canvasDeltaRecovery;
    if(!progress.rejected && body.ops?.some(op=>op.op==='patch_canvas')){
     const changed=structuredClone(body);
     changed.ops.find(op=>op.op==='patch_canvas').base_frame_rev=0;
     progress.rejected=true;
     return original.call(this,changed);
    }
    const result=original.call(this,body);
    if(progress.rejected && body.mode==='snapshot'){
     progress.recovered=true;Renderer.prototype.apply=original;
    }
    return result;
   };
  });
  let box=await bitmap.boundingBox();
  await page.mouse.move(box.x+box.width*.55,box.y+120);
  await page.waitForFunction(()=>window.canvasDeltaRecovery.recovered);
  let before=await bitmap.evaluate(c=>c.toDataURL());
  await page.mouse.move(box.x+box.width*.75,box.y+140);
  await page.waitForFunction(old=>document.querySelector('.pui-Canvas canvas').toDataURL()!==old,before);
  assert.equal(await page.locator('#pui-status').isVisible(),false);
  const updates=await page.evaluate(async packets=>{
   const {StreamDecoder}=await import(document.querySelector('script[type=module]').src);
   const decoder=new StreamDecoder(),updates=[];
   for(const packet of packets){
    const m=decoder.decode(Uint8Array.from(atob(packet),c=>c.charCodeAt(0)));
    for(const op of m.body.ops || [])if(['put_canvas','patch_canvas'].includes(op.op))
     updates.push({op:op.op,count:op.frame.commands.length,start:op.start,bytes:packet.length*3/4});
   }
   decoder.close();return updates;
  },packets);
  assert(updates.some(op=>op.op==='put_canvas' && op.count>4500));
  assert(updates.some(op=>op.op==='patch_canvas' && op.start>54000 && op.count<20));
  // A resumed connection starts with a complete display list and then resumes
  // deltas; its compression stream has fresh history as well.
  packets.length=0;
  await page.reload();
  await page.getByRole('button',{name:'Resume session',exact:true}).click();
  await page.getByText('6,000 sessions | Seed 42 | ~54,000 draw calls',{exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('.pui-Canvas canvas')?.width>0);
  box=await bitmap.boundingBox();before=await bitmap.evaluate(c=>c.toDataURL());
  await page.mouse.move(box.x+box.width*.3,box.y+120);
  await page.waitForFunction(old=>document.querySelector('.pui-Canvas canvas').toDataURL()!==old,before);
  const resumed=await page.evaluate(async packets=>{
   const {StreamDecoder}=await import(document.querySelector('script[type=module]').src),decoder=new StreamDecoder();
   const frames=[];
   for(const packet of packets){
    const m=decoder.decode(Uint8Array.from(atob(packet),c=>c.charCodeAt(0)));
    for(const frame of m.body.canvases || [])frames.push('snapshot');
    for(const op of m.body.ops || [])if(['put_canvas','patch_canvas'].includes(op.op))frames.push(op.op);
   }
   decoder.close();return frames;
  },packets);
  assert(['snapshot','put_canvas'].includes(resumed[0]));
  assert(resumed.includes('patch_canvas'));

  await page.evaluate(async fixtures=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const check=(v,m)=>{if(!v)throw new Error(m);};
   const tick=()=>new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
   const hosts=[0,1].map(i=>{const e=document.createElement('div');e.style.cssText=`position:fixed;top:0;left:${i*140}px;width:120px;height:90px;display:flex`;document.body.append(e);return e;});
   const controls=[],r=new Renderer(hosts[0],()=>{},(type,body)=>controls.push({type,body})),full=new Renderer(hosts[1],()=>{});
   const snapshot=(target,rev)=>({mode:'snapshot',base_rev:null,rev,processed_seq:0,...structuredClone(target)});
   const image=renderer=>renderer.canvases.records.get('canvas').canvas.toDataURL();
   const frozen=JSON.stringify(fixtures);
   for(const {body,target} of fixtures){
    const previous=r.state.canvases.get('canvas'),saved=previous && JSON.stringify(previous);
    r.apply(body);full.apply(snapshot(target,body.rev));await tick();await tick();
    check(JSON.stringify(r.state.canvases.get('canvas'))===JSON.stringify(target.canvases[0]),'Reconstructed frame differs from Python target');
    check(image(r)===image(full),'Delta pixels differ from a full repaint');
    if(previous)check(JSON.stringify(previous)===saved,'Previous display list mutated');
    if(body.ops?.some(op=>op.op==='patch_canvas')){
     const current=r.state.canvases.get('canvas');
     check(current.commands[0]===previous.commands[0],'Retained command was copied');
     check(controls.some(c=>c.type==='canvas_ack' && c.body.frame_rev===current.frame_rev),'Delta frame was not acknowledged');
    }
   }
   check(JSON.stringify(fixtures)===frozen,'Wire input was mutated');
   let current=r.state.canvases.get('canvas');
   const splice=(overrides={})=>({op:'patch_canvas',base_frame_rev:current.frame_rev,start:0,delete_count:0,
     frame:{...current,frame_rev:current.frame_rev+1,commands:[]},...overrides});
   const patch=ops=>({mode:'patch',base_rev:r.rev,rev:r.rev+1,processed_seq:0,ops});
   function reject(op){
    const old=r.state,revision=r.rev,display=image(r),saved=JSON.stringify(current);
    let error;try{r.apply(patch([op]));}catch(e){error=e;}
    check(error && r.state===old && r.rev===revision,'Invalid delta promoted canonical state');
    check(image(r)===display && JSON.stringify(current)===saved,'Invalid delta changed the bitmap/baseline');
   }
   for(const op of [splice({base_frame_rev:current.frame_rev-1}),splice({base_frame_rev:true}),
     splice({start:-1}),splice({start:0.5}),splice({delete_count:1000}),splice({start:current.commands.length+1}),
     splice({frame:{...current,frame_rev:current.frame_rev+1,measure_rev:current.measure_rev+1,commands:[]}}),
     splice({frame:{...current,commands:[]}}),
     splice({frame:{...current,frame_rev:current.frame_rev+1,commands:[{op:'invalid'}]}}),
     splice({frame:{...current,frame_rev:current.frame_rev+1,commands:Array(100000).fill(current.commands[0])}})])reject(op);
   // A small wire delta cannot grow the retained state past aggregate budgets.
   const compact={op:'polyline',points:[],color:'#000000',width:1};
   let target=structuredClone(fixtures[0].target);
   target.canvases[0]={...current,frame_rev:current.frame_rev+1,commands:Array.from({length:90000},()=>({...compact}))};
   target.roots[0].children[0].layout.width=current.width;
   r.apply(snapshot(target,r.rev+1));await tick();current=r.state.canvases.get('canvas');
   reject(splice({frame:{...current,frame_rev:current.frame_rev+1,commands:
     Array.from({length:10000},()=>({...compact,points:[[1,2],[3,4],[5,6],[7,8],[9,10]]}))}}));
   // Below the item cap, text additions must still respect the byte budget.
   const text={op:'text',x:1,y:1,text:'x'.repeat(60000),w:null,h:null,size:9,color:'#000000',rotate:0,anchor:'LEFT_TOP'};
   target.canvases[0]={...current,frame_rev:current.frame_rev+1,commands:Array.from({length:250},()=>({...text}))};
   r.apply(snapshot(target,r.rev+1));current=r.state.canvases.get('canvas');
   reject(splice({frame:{...current,frame_rev:current.frame_rev+1,commands:Array.from({length:50},()=>({...text}))}}));
   // Recovery snapshots replace even a missing/corrupt local base. A later
   // splice is prepared successfully against the new canonical full frame.
   r.dirty=true;r.apply(snapshot(fixtures[0].target,r.rev+2));await tick();
   r.apply({...fixtures[1].body,base_rev:r.rev,rev:r.rev+1});await tick();
   check(r.state.canvases.get('canvas').commands[12].fill==='#0000ff','Recovery could not resume deltas');
   r.destroy();full.destroy();hosts.forEach(e=>e.remove());
  },fixtures);
  assert.deepEqual(errors,[]);
  console.log('Canvas deltas: Python/JS equivalence, full-frame pixels, ACKs, immutable sharing, malformed bases/splices, reconstructed item/byte limits, recovery and 6000-session live transport passed.');
  console.log(JSON.stringify(updates));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
