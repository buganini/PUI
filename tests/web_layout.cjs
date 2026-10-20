const login=require('./web_login.cjs');
// Native Grid/ProgressBar and nested scroll geometry at desktop/mobile sizes.
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
  const page=await browser.newPage(),errors=[];
  page.setDefaultTimeout(10000);
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
  await page.getByRole('button',{name:'Vbox',exact:true}).click();
  await page.getByText('Row 1',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Stack',exact:true}).click();
  await page.getByText('Top',{exact:true}).waitFor();
  assert.equal(await page.locator('.pui-Stack').evaluate(e=>{
   const [bottom,top]=e.children,a=bottom.getBoundingClientRect(),b=top.getBoundingClientRect();
   return a.x===b.x && a.y===b.y && document.elementFromPoint(b.x+5,b.y+5)===top;
  }),true);
  await page.getByRole('button',{name:'TimelineView',exact:true}).click();
  const timestamp=page.getByText(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
  await timestamp.waitFor();const time=await timestamp.textContent();
  await page.waitForFunction(before=>[...document.querySelectorAll('.pui-Label')].some(e=>
    /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(e.textContent) && e.textContent!==before),time);
  await page.getByRole('button',{name:'ProgressBar',exact:true}).click();
  await page.locator('progress').waitFor();
  const progressBefore=await page.locator('progress').evaluate(e=>e.value);
  await page.getByRole('button',{name:'+5',exact:true}).click();
  await page.waitForFunction(value=>document.querySelector('progress')?.value===value,Math.min(100,progressBefore+5));
  await page.getByRole('button',{name:'-5',exact:true}).click();
  await page.waitForFunction(value=>document.querySelector('progress')?.value===value,progressBefore);
  await page.getByRole('button',{name:'Grid',exact:true}).click();
  const tiles=page.locator('.pui-Grid > .pui-Label');
  await tiles.nth(4).waitFor();
  const a=await tiles.nth(0).boundingBox(),b=await tiles.nth(1).boundingBox(),c=await tiles.nth(2).boundingBox();
  assert.equal(a.y,b.y);assert.ok(b.x>a.x && c.y>a.y && a.height>=c.height*1.9);
  await page.getByRole('button',{name:'Scroll',exact:true}).click();
  await page.getByText('Row 100',{exact:true}).waitFor();
  await page.waitForFunction(()=>{const e=[...document.querySelectorAll('.pui-Scroll')].at(-1);
   return e.clientHeight>100 && e.clientHeight<innerHeight && e.scrollTop===e.scrollHeight-e.clientHeight;});
  await page.getByRole('button',{name:'+',exact:true}).click();
  await page.getByText('Row 101',{exact:true}).waitFor();
  await page.waitForFunction(()=>{const e=[...document.querySelectorAll('.pui-Scroll')].at(-1);
   return e.scrollTop===e.scrollHeight-e.clientHeight;});
  for(const viewport of [{width:1440,height:900},{width:390,height:700}]) {
   await page.setViewportSize(viewport);
   await page.evaluate(async()=>{
    const {Renderer}=await import(document.querySelector('script[type=module]').src);
    const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;display:flex;background:white;';
    document.body.append(host);
    const r=new Renderer(host,()=>{}),check=(v,m)=>{if(!v)throw new Error(m);};
    const n=(id,type,props={},children=[],layout={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
    const label=i=>n('label'+i,'Label',{text:'Row '+i,selectable:false});
    const content=n('content','VBox',{},Array.from({length:80},(_,i)=>label(i)));
    const scroll=n('scroll','Scroll',{vertical:'auto',horizontal:'auto'},[content],{weight:1});
    const nested=n('nested','VBox',{},[scroll],{weight:1});
    const outer=n('outer','VBox',{},[label('header'),nested],{weight:1});
    const root=n('root','Window',{title:'Layout'},[outer]);
    const snapshot=rev=>({mode:'snapshot',base_rev:null,rev,processed_seq:1,roots:[root],bindings:[],canvases:[]});
    r.apply(snapshot(1));
    const e=r.elements.get('scroll');
    check(e.clientHeight>100 && e.clientHeight<innerHeight,'Nested scroller escaped viewport');
    check(e.scrollHeight>e.clientHeight,'Nested content has no scroll range');
    e.scrollTop=140;check(e.scrollTop===140,'Native scroll failed');
    r.apply(snapshot(2));check(r.elements.get('scroll')===e && e.scrollTop===140,'Redraw lost native scroll');
    scroll.props.scroll_y=['end',12,1];r.apply(snapshot(3));
    check(Math.abs(e.scrollHeight-e.clientHeight-e.scrollTop-12)<1,'End-relative offset failed');
    content.children.push(label('new'));r.apply(snapshot(4));
    check(Math.abs(e.scrollHeight-e.clientHeight-e.scrollTop-12)<1,'Content growth lost end-relative offset');
    scroll.props.scroll_y=['start',0,2];r.apply(snapshot(5));check(e.scrollTop===0,'Scroll-to-start failed');
    scroll.props.scroll_y=['end',0,3];r.apply(snapshot(6));
    check(e.scrollTop===e.scrollHeight-e.clientHeight,'Scroll.END failed');
    host.style.height='360px';
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    check(e.scrollTop===e.scrollHeight-e.clientHeight,'Resize lost end anchoring');
    content.layout.width=2000;scroll.props.scroll_x=['end',20,1];r.apply(snapshot(7));
    check(Math.abs(e.scrollWidth-e.clientWidth-e.scrollLeft-20)<1,'Horizontal end offset failed');
    const progress=n('progress','ProgressBar',{progress:0,maximum:0});
    root.children=[progress];r.apply(snapshot(8));check(r.scrolls.size===0,'Removed scroller retained observers');
    const bar=r.elements.get('progress');check(!bar.hasAttribute('value'),'Busy progress is determinate');
    progress.props={progress:4,maximum:10};r.apply(snapshot(9));
    check(bar.value===4 && bar.max===10,'Progress range did not update');
    const events=[];r.actions=(type,body)=>events.push(body);
    const bottom=n('bottom','Label',{text:'Bottom',selectable:false});bottom.events.click='bottom-click';
    const top=n('top','Label',{text:'Top',selectable:false});top.events.click='top-click';
    const stack=n('stack','Stack',{},[bottom,top],{width:200,height:100});root.children=[stack];r.apply(snapshot(10));
    const lower=r.elements.get('bottom'),upper=r.elements.get('top');
    const hit=()=>{const b=r.elements.get('stack').getBoundingClientRect();return document.elementFromPoint(b.x+5,b.y+5);};
    check(hit()===upper,'Later Stack child did not paint on top');hit().click();check(events.at(-1).node_id==='top','Stack hit-testing ignored top child');
    stack.children.reverse();r.apply(snapshot(11));
    check(r.elements.get('bottom')===lower && r.elements.get('top')===upper,'Stack reorder replaced keyed children');
    check(hit()===lower,'Stack reorder did not change paint order');hit().click();check(events.at(-1).node_id==='bottom','Stack reorder hit-testing failed');
    stack.children=[top];r.apply(snapshot(12));check(!lower.isConnected && hit()===upper,'Stack removal retained an obsolete overlay');
    r.destroy();host.remove();
   });
  }
  assert.deepEqual(errors,[]);console.log('Stack overlap/order/hit-testing/retention, TimelineView updates, Grid, ProgressBar and Scroll cookbook, nested scroll, resize/end anchoring and both axes passed at desktop/mobile viewport sizes.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
