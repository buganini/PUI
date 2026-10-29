const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),{createRequire}=require('module');
const root=path.resolve(__dirname,'..'),build=createRequire(root+'/env/web-client/package.json');
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[root+'/browser-client/shared/dom.js'],bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await (process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require)('playwright').chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:500,height:300}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
  await page.setContent('<main id="pui-root"></main>');
  await page.addStyleTag({content:fs.readFileSync(root+'/browser-client/shared/client.css','utf8')});
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   window.actions=[];window.r=new PUIRenderer.Renderer(document.getElementById('pui-root'),(kind,body)=>actions.push(body));
   window.render=(reverse=false,remove=false,label='One',hidden=false)=>{
    const n=(id,type,props={},children=[],events={},layout={})=>({id,type,props,children,events,layout,style:{},bindings:{}});
    const action=(id,text)=>n(id,'MenuAction',{text,disabled:false},[],{click:'token-'+id});
    const children=[action('one',label),n('nested','Menu',{text:'Nested'},[action('deep','Deep')])];
    if(reverse)children.reverse();
    r.apply({mode:'snapshot',base_rev:null,rev:r.rev+1,processed_seq:0,roots:[n('window','Window',{title:'Menus'},[
     ...remove?[]:[n('bar','MenuBar',{},[n('file','Menu',{text:'File'},children),n('edit','Menu',{text:'Edit'},[action('copy','Copy')])],{},{visible:!hidden})],
     n('body','VBox',{},[n('outside','Button',{text:'Outside',disabled:false})],{},{weight:1})])],bindings:[],canvases:[]});
   };render();
  });
  const file=page.getByRole('menuitem',{name:'File',exact:true}),nested=page.getByRole('menuitem',{name:'Nested',exact:true});
  const menu=page.locator('#pui-menu-file'),sub=page.locator('#pui-menu-nested');
  const box=await page.locator('[data-pui-id="bar"]').boundingBox(),body=await page.locator('[data-pui-id="body"]').boundingBox();
  assert(box.height>20 && box.height<80);assert(body.y>=box.y+box.height && body.height>100);
  assert.equal(box.x,0);assert.equal(box.y,0);assert.equal(box.width,500);assert.equal(body.x,12);
  await page.evaluate(()=>r.apply({mode:'patch',base_rev:r.rev,rev:r.rev+1,processed_seq:0,ops:[
   {op:'patch_node',node_id:'window',field:'layout',set:{padding:[20,24,16,32]},unset:[]}
  ]}));
  const padded=await page.locator('[data-pui-id="bar"]').boundingBox();
  assert.equal(padded.x,0);assert.equal(padded.y,0);assert.equal(padded.width,500);
  assert.equal((await page.locator('[data-pui-id="body"]').boundingBox()).x,32);
  await page.evaluate(()=>render());
  await file.click();assert(await menu.isVisible());assert.equal(await file.getAttribute('aria-expanded'),'true');
  await nested.click();assert(await sub.isVisible());
  await page.getByRole('menuitem',{name:'Deep',exact:true}).click();
  assert.equal(await page.evaluate(()=>actions.at(-1).node_id),'deep');assert(!await menu.isVisible());
  await file.focus();await page.keyboard.press('ArrowDown');assert.equal(await page.evaluate(()=>document.activeElement.dataset.puiId),'one');
  await page.keyboard.press('ArrowDown');await page.keyboard.press('ArrowRight');assert(await sub.isVisible());
  await page.keyboard.press('Escape');assert(!await sub.isVisible());assert(await menu.isVisible());
  await page.keyboard.press('ArrowLeft');assert(!await menu.isVisible());
  await page.keyboard.press('ArrowRight');assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Edit');
  await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>actions.at(-1).node_id),'copy');
  await file.click();await page.mouse.click(450,250);assert(!await menu.isVisible());
  await file.click();await page.keyboard.press('Tab');assert(!await menu.isVisible());assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Outside');
  await page.evaluate(()=>render(true,false,'Renamed'));
  await file.click();assert.equal(await menu.locator(':scope > :first-child').getAttribute('data-pui-id'),'nested');
  await page.getByRole('menuitem',{name:'Renamed'}).click();assert.equal(await page.evaluate(()=>actions.at(-1).node_id),'one');
  await page.evaluate(()=>r.apply({mode:'patch',base_rev:r.rev,rev:r.rev+1,processed_seq:0,ops:[
   {op:'patch_node',node_id:'one',field:'props',set:{text:'Patched'},unset:[]},
   {op:'patch_node',node_id:'one',field:'events',set:{click:'new-token'},unset:[]}
  ]}));
  await file.click();await page.getByRole('menuitem',{name:'Patched'}).click();
  assert.equal(await page.evaluate(()=>actions.at(-1).token),'new-token');
  await page.locator('[data-pui-id="bar"]').evaluate(e=>e.style.justifyContent='flex-end');
  await file.click();await nested.click();
  const subbox=await sub.boundingBox();assert(subbox.x>=0 && subbox.x+subbox.width<=500 && subbox.y+subbox.height<=300);
  await page.keyboard.press('Escape');await page.keyboard.press('Escape');
  await file.click();await page.evaluate(()=>render(false,false,'One',true));assert(!await menu.isVisible());
  await page.evaluate(()=>render(false,false,'One'));await file.click();await page.evaluate(()=>render(false,true));
  assert.equal(await page.locator(':popover-open').count(),0);
  assert.equal((await page.locator('[data-pui-id="body"]').boundingBox()).x,12);
  assert.equal((await page.locator('[data-pui-id="body"]').boundingBox()).y,12);
  await page.evaluate(()=>r.destroy());assert.deepEqual(errors,[]);
  console.log('Menus: sizing, clicks, nested popovers, arrows/Escape/Tab, outside dismissal, update/reorder/hide/removal passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
