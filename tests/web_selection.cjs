const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(),errors=[];page.setDefaultTimeout(10000);
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await page.getByRole('button',{name:'Views',exact:true}).click();
  const views=page.locator('.pui-Views');await views.nth(1).waitFor();
  assert.equal(await views.first().locator(':scope > :visible').count(),0);
  await page.getByRole('button',{name:'Editor',exact:true}).click();
  const editor=views.first().locator('input');await editor.waitFor();
  const id=await editor.getAttribute('data-pui-id');
  await editor.fill('browser retained value');await editor.press('Enter');
  await page.getByText('Saved text: browser retained value',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Settings',exact:true}).click();await editor.waitFor({state:'hidden'});
  await page.getByRole('button',{name:'Editor',exact:true}).click();await editor.waitFor();
  assert.equal(await editor.getAttribute('data-pui-id'),id);assert.equal(await editor.inputValue(),'browser retained value');
  await page.getByRole('button',{name:'Clear',exact:true}).click();await editor.waitFor({state:'hidden'});
  await page.getByRole('button',{name:'Settings (state)',exact:true}).click();
  await page.getByText('Select by state: settings',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Editor (state)',exact:true}).click();await views.nth(1).locator('input').waitFor();
  await page.getByRole('button',{name:'Tab',exact:true}).click();
  const tabs=page.locator('.pui-Tabs');await tabs.nth(1).waitFor();
  await tabs.first().getByRole('tab',{name:'Tab 2',exact:true}).click();
  await tabs.first().getByText('Selected by fallback ID: Tab 2',{exact:true}).waitFor();
  await tabs.first().getByRole('tab',{name:'Tab 2',exact:true}).press('ArrowLeft');
  await tabs.first().getByText('Selected by explicit ID: first',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Tab 2',exact:true}).first().click();
  await tabs.first().getByText('Selected by fallback ID: Tab 2',{exact:true}).waitFor();
  await tabs.nth(1).getByRole('tab',{name:'Tab 2',exact:true}).click();
  await page.getByText("Select by state: 'Tab 2'",{exact:true}).waitFor();
  await page.getByRole('button',{name:'Tab 1',exact:true}).nth(1).click();
  await page.getByText("Select by state: 'first'",{exact:true}).waitFor();
  const links=await tabs.evaluateAll(elements=>elements.every(e=>[...e.querySelectorAll('[role=tab]')].every(t=>{
   const panel=document.getElementById(t.getAttribute('aria-controls'));
   return panel && panel.getAttribute('aria-labelledby')===t.id && panel.hidden===(t.getAttribute('aria-selected')!=='true');
  })));assert.ok(links);
  await page.evaluate(async()=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;display:flex;';document.body.append(host);
   const r=new Renderer(host,()=>{}),check=(v,m)=>{if(!v)throw new Error(m);};
   const node=(id,type,props={},children=[])=>({id,type,props,children,layout:{},style:{},events:{},bindings:{}});
   const ref={object_id:'42',kind:'attr',key:'text'},slot={ref,token:'slot',value_rev:1,value:'saved'};
   const input=node('editor','TextField',{text:'saved',placeholder:''});
   input.bindings.model={ref,slot_token:'slot',token:'attachment',writable:true};
   const tall=node('tall','VBox',{},Array.from({length:80},(_,i)=>node('row'+i,'Label',{text:'Row '+i,selectable:false})));
   const scroll=node('scroll','Scroll',{vertical:'auto',horizontal:'hidden'},[tall]);scroll.layout.weight=1;
   const first=node('first','VBox',{},[input,scroll]),second=node('second','VBox',{},[node('other','Label',{text:'Other',selectable:false})]);
   const views=node('views','Views',{selected:'first'},[first,second]);
   const root=node('root','Window',{title:'Retained views'},[views]);
   const snapshot=rev=>({mode:'snapshot',base_rev:null,rev,processed_seq:1,roots:[root],bindings:[slot],canvases:[]});
   r.apply(snapshot(1));const e=r.elements.get('editor'),s=r.elements.get('scroll');
   e.focus();e.value='unsaved local draft';e.dispatchEvent(new InputEvent('input',{bubbles:true}));e.setSelectionRange(2,5);
   s.scrollTop=100;views.props.selected='second';r.apply(snapshot(2));
   check(e.isConnected && first.id==='first' && r.elements.get('first').hidden,'Inactive page was destroyed');
   views.children.reverse();views.props.selected='first';r.apply(snapshot(3));
   check(r.elements.get('editor')===e && e.value==='unsaved local draft','Switch/reorder lost uncommitted editor');
   check(e.selectionStart===2 && e.selectionEnd===5 && s.scrollTop===100,'Switch lost cursor/scroll position');
   views.props.selected=null;r.apply(snapshot(4));check([...r.elements.get('views').children].every(e=>e.hidden),'Clear did not hide all pages');
   r.destroy();host.remove();
  });
  assert.deepEqual(errors,[]);console.log('Views/Tabs: optional models, .select(), native/State selection, keyboard/ARIA and retained drafts/cursors/scroll through hiding/reorder passed.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
