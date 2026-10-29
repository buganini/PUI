const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
const login=require('./web_login.cjs');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  for(const url of process.argv.slice(2)) {
   const page=await browser.newPage({viewport:{width:1500,height:1000}}),errors=[];
   page.setDefaultTimeout(30000);page.on('pageerror',e=>errors.push(e.message));
   await page.goto(url);await login(page);
   await page.getByRole('button',{name:'Tree',exact:true}).waitFor({timeout:180000});
   await page.getByRole('button',{name:'Tree',exact:true}).click();
   const tree=page.getByRole('tree');await tree.waitFor();
   const row=text=>tree.getByRole('treeitem').filter({has:page.locator('.pui-tree-label',{hasText:new RegExp('^'+text+'$')})});
   for(let i=0;i<16;i++) {
    const item=row(i%2?'Sub 3':'Sub 1');const before=await item.getAttribute('aria-expanded');
    await item.locator('.pui-tree-arrow').click();
    await page.waitForFunction(({text,before})=>[...document.querySelectorAll('[role=treeitem]')].find(e=>e.lastChild.textContent===text)?.getAttribute('aria-expanded')!==before,{text:i%2?'Sub 3':'Sub 1',before});
   }
   await row('Root').click();await row('Root').press('ArrowLeft');
   await page.waitForFunction(()=>document.querySelector('[role=treeitem]')?.getAttribute('aria-expanded')==='false');
   await row('Root').press('ArrowRight');await row('Root').press('ArrowDown');
   assert.equal(await page.locator('[role=treeitem]:focus .pui-tree-label').textContent(),'Sub 1');
   await page.getByRole('button',{name:'Add item',exact:true}).click();
   await tree.getByText('New item',{exact:true}).waitFor();
   await page.getByRole('button',{name:'Tree(Adapter)',exact:true}).click();
   await page.waitForFunction(()=>document.querySelectorAll('[role=tree]').length===2);
   const trees=page.getByRole('tree');
   for(let i=0;i<24;i++) {
    const item=trees.nth(i%2).getByRole('treeitem').filter({has:page.locator('.pui-tree-label',{hasText:i%4<2?/^Sub1$/:/^Sub3$/})});
    const before=await item.getAttribute('aria-expanded');if(i%3){await item.locator('.pui-tree-label').click();assert.equal(await item.getAttribute('aria-expanded'),before);await item.locator('.pui-tree-label').dblclick();}else await item.locator('.pui-tree-arrow').click();
    assert.notEqual(await item.getAttribute('aria-expanded'),before);
   }
   await page.getByRole('button',{name:'Add item',exact:true}).click();
   await trees.nth(1).getByText('New item',{exact:true}).waitFor();
   assert.deepEqual(errors,[]);console.log(url,'Tree/adapter cross clicks, keyboard, additions passed');
   await page.close();
  }
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
