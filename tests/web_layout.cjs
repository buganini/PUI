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
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await page.getByText('Row 1',{exact:true}).waitFor();
  await page.getByRole('button',{name:'ProgressBar',exact:true}).click();
  await page.locator('progress[value="50"]').waitFor();
  await page.getByRole('button',{name:'+5',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('progress')?.value===55);
  await page.getByRole('button',{name:'Grid',exact:true}).click();
  const left=page.getByText('R=0 C=0',{exact:true}),span=page.getByText('R=0 C=1, rowspan=2',{exact:true});
  await span.waitFor();
  const a=await left.boundingBox(),b=await span.boundingBox(),c=await page.getByText('R=1 C=0',{exact:true}).boundingBox();
  assert.equal(a.y,b.y);assert.ok(b.x>a.x && b.height>=c.y+c.height-a.y);
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
    const outer=n('outer','VBox',{},[label('header'),scroll],{weight:1});
    const root=n('root','Window',{title:'Layout'},[outer]);
    const snapshot=rev=>({mode:'snapshot',base_rev:null,rev,processed_seq:1,roots:[root],bindings:[],canvases:[]});
    r.apply(snapshot(1));
    const e=r.elements.get('scroll');
    check(e.clientHeight>100 && e.clientHeight<innerHeight,'Nested scroller escaped viewport');
    check(e.scrollHeight>e.clientHeight,'Nested content has no scroll range');
    e.scrollTop=140;check(e.scrollTop===140,'Native scroll failed');
    r.apply(snapshot(2));check(r.elements.get('scroll')===e && e.scrollTop===140,'Redraw lost native scroll');
    const progress=n('progress','ProgressBar',{progress:0,maximum:0});
    root.children=[progress];r.apply(snapshot(3));
    const bar=r.elements.get('progress');check(!bar.hasAttribute('value'),'Busy progress is determinate');
    progress.props={progress:4,maximum:10};r.apply(snapshot(4));
    check(bar.value===4 && bar.max===10,'Progress range did not update');
    host.remove();
   });
  }
  assert.deepEqual(errors,[]);console.log('Grid, ProgressBar and nested scroll checks passed at desktop/mobile viewport sizes.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
