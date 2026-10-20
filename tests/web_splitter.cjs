// Retained panes, native pointer/keyboard resizing, and Cookbook integration.
const assert=require('node:assert/strict');
const path=require('node:path'),{createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=requireBrowser('playwright');
const login=require('./web_login.cjs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];
  page.setDefaultTimeout(10000);
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://127.0.0.1:18870/');await login(page);
  const splitter=page.locator('.pui-Splitter').first(),panes=splitter.locator(':scope > [data-pui-id]');
  await splitter.waitFor();
  const handle=splitter.locator(':scope > [role=separator]'),before=await panes.first().boundingBox();
  const drag=async(locator,dx,dy)=>{
   const b=await locator.boundingBox();await page.mouse.move(b.x+b.width/2,b.y+b.height/2);
   await page.mouse.down();await page.mouse.move(b.x+b.width/2+dx,b.y+b.height/2+dy,{steps:8});await page.mouse.up();
  };
  await drag(handle,-130,0);
  const resized=await panes.first().boundingBox();assert.ok(resized.width<before.width-120);
  await panes.evaluateAll(es=>{window.cookbookPanes=es;});
  for(const name of ['TextField','Button','Adaptive Grid']){
   await page.getByRole('button',{name,exact:true}).click();
   await page.waitForFunction(name=>location.hash.includes(encodeURIComponent(name)),name);
   assert.ok(Math.abs((await panes.first().boundingBox()).width-resized.width)<2,'Page switch changed pane ratio');
   assert.equal(await panes.evaluateAll(es=>es.every((e,i)=>e===window.cookbookPanes[i])),true);
  }
  // Dragging the containing pane must also drive adaptive size observations.
  const grid=page.locator('.pui-Grid');await grid.waitFor();
  await drag(handle,750,0);
  await page.waitForFunction(()=>getComputedStyle(document.querySelector('.pui-Grid')).gridTemplateColumns.split(' ').length===1);
  await handle.focus();const narrow=await panes.first().boundingBox();
  await page.keyboard.press('ArrowLeft');
  assert.ok((await panes.first().boundingBox()).width<narrow.width-8);
  await page.screenshot({path:'/tmp/pui-cookbook-splitter-web.png'});

  await page.evaluate(async()=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;width:900px;height:600px;display:flex;background:white;z-index:1000';
   document.body.append(host);
   const actions=[],r=new Renderer(host,(...args)=>actions.push(args));
   const n=(id,type,props={},children=[],layout={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
   const labels=['a','b','c'].map(id=>n(id,'Label',{text:id,selectable:false}));
   const split=n('split','Splitter',{vertical:false},labels,{weight:1});
   const root=n('window','Window',{title:'Splitter test'},[split]);
   const apply=()=>r.apply({mode:'snapshot',base_rev:null,rev:r.rev+1,processed_seq:0,roots:[structuredClone(root)],bindings:[],canvases:[]});
   const check=(v,m)=>{if(!v)throw new Error(m);};apply();
   window.splitterFixture={r,root,split,labels,apply,check,host,actions};
  });
  const fixture=page.locator('[data-pui-id=split]'),sash=fixture.locator(':scope > [role=separator]');
  const widths=await fixture.locator(':scope > [data-pui-id]').evaluateAll(es=>es.map(e=>e.getBoundingClientRect().width));
  await drag(sash.first(),80,0);
  await page.evaluate(widths=>{
   const {r,apply,check,actions}=window.splitterFixture;
   const a=r.elements.get('a'),c=r.elements.get('c'),size=a.getBoundingClientRect().width;
   check(size>widths[0]+70,'Pointer resize did not grow first pane');
   check(Math.abs(c.getBoundingClientRect().width-widths[2])<1,'Resize moved an unrelated pane');
   const handle=r.elements.get('split').querySelector('[role=separator]');apply();
   check(r.elements.get('a')===a && Math.abs(a.getBoundingClientRect().width-size)<1,'Snapshot lost pane or ratio');
   check(a.nextSibling===handle && handle.nextSibling===r.elements.get('b'),'Snapshot misplaced local separators');
   check(!actions.length,'Local resize sent application actions');
  },widths);
  await sash.first().focus();await page.keyboard.press('Home');
  assert.ok((await page.locator('[data-pui-id=a]').boundingBox()).width<2);
  await page.keyboard.press('End');
  assert.ok((await page.locator('[data-pui-id=b]').boundingBox()).width<2);
  await page.evaluate(()=>{
   const {r,split,apply,check}=window.splitterFixture;split.props.vertical=true;apply();
   const bounds=['a','b','c'].map(id=>r.elements.get(id).getBoundingClientRect());
   check(bounds[0].y<bounds[1].y && bounds[1].y<bounds[2].y,'Vertical panes did not stack');
  });
  const oldHeight=(await page.locator('[data-pui-id=a]').boundingBox()).height;
  await drag(sash.first(),0,60);
  assert.ok((await page.locator('[data-pui-id=a]').boundingBox()).height>oldHeight+50);
  await page.evaluate(()=>{
   const {r,root,split,labels,apply,check,host}=window.splitterFixture;
   const a=r.elements.get('a');split.children=[labels[2],labels[0]];apply();
   check(r.elements.get('a')===a && !r.elements.has('b'),'Keyed reorder/removal failed');
   labels[0].layout.visible=false;apply();
   check(!r.elements.get('split').querySelector('[role=separator]'),'Hidden pane retained a separator');
   labels[0].layout.visible=true;
   const nested={...split,id:'nested',props:{vertical:false},children:[labels[0],labels[1]]};
   split.children=[nested,labels[2]];apply();
   check(host.querySelectorAll('[role=separator]').length===2,'Nested splitter handles missing');
   split.children=[labels[2]];apply();check(!host.querySelector('[role=separator]'),'Single pane retained separator');
   split.children=[];apply();check(!r.elements.get('split').children.length,'Empty splitter retained DOM');
   root.children=[];apply();check(!r.splitters.size,'Removed splitters retained managers');
   r.destroy();host.remove();
  });
  assert.deepEqual(errors,[]);
  console.log('Splitter: Cookbook/page retention, adaptive resizing, pointer/keyboard, snapshots, adjacent panes, vertical/nested/hidden/empty panes passed.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
