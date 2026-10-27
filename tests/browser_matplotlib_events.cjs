const path=require('path'),{createRequire}=require('module'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),build=createRequire(root+'/env/web-client/package.json');
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[root+'/browser-client/shared/canvas.js'],bundle:true,write:false,format:'iife',globalName:'Drawing'});
 const browser=await (process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require)('playwright').chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:800,height:600},deviceScaleFactor:2});
  await page.setContent('<input id="editor"><div id="plot" style="width:400px;height:300px"></div>');
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   window.actions=[];window.errors=[];
   const node={id:'plot',props:{},events:Object.fromEntries(Drawing.canvasEvents.map(n=>[n,n]))};
   const renderer={resources:{url:x=>x,valid:()=>true},state:{nodes:new Map([['plot',node]])},rev:1,
     actions:(kind,body)=>actions.push(body),focusedEditor:()=>null};
   window.drawings=new Drawing.Canvases(renderer,()=>{},e=>errors.push(String(e)));
   drawings.add('plot',document.getElementById('plot'));drawings.update(node);
  });
  await page.locator('#plot').click({position:{x:120,y:90}});
  assert.equal(await page.evaluate(()=>document.activeElement.id),'plot');
  await page.keyboard.press('Control+ArrowLeft');
  await page.mouse.wheel(0,100);
  await page.waitForFunction(()=>actions.some(e=>e.event==='wheel'));
  await page.locator('#plot').dblclick({position:{x:100,y:80}});
  await page.mouse.move(150,150);await page.mouse.down();await page.keyboard.down('Shift');
  await page.locator('#editor').focus();
  const result=await page.evaluate(()=>({actions,errors}));
  assert.deepEqual(result.errors,[]);
  const press=result.actions.find(e=>e.event==='mousedown');
  assert.equal(press.data.x,120);assert.equal(press.data.y,90);
  assert(result.actions.some(e=>e.event==='mousedown' && e.data.dblclick));
  assert(result.actions.some(e=>e.event==='keydown' && e.data.key==='ArrowLeft' && e.data.modifiers===2));
  assert(result.actions.some(e=>e.event==='keyup' && e.data.key==='ArrowLeft'));
  assert(result.actions.some(e=>e.event==='wheel' && e.data.delta_y>0));
  assert(result.actions.some(e=>e.event==='mouseup' && e.data.cancelled));
  assert(result.actions.some(e=>e.event==='blur'));
  const before=await page.evaluate(()=>actions.length);
  await page.keyboard.press('a');
  assert.equal(await page.evaluate(()=>actions.length),before);
  await page.evaluate(()=>drawings.destroy());
  console.log('Canvas focus, logical coordinates, double click, keys, wheel, capture cancellation and input isolation passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
