const assert=require('node:assert/strict');
const path=require('node:path'),{createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=requireBrowser('playwright');
const login=require('./web_login.cjs');
(async()=>{const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});try{
 const page=await browser.newPage({viewport:{width:1024,height:768}}), errors=[];
 page.setDefaultTimeout(10000);
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.PUI_WEB_URL || 'http://127.0.0.1:18870/');await login(page);await page.waitForTimeout(300);const resume=page.getByRole('button',{name:'Resume session',exact:true});if(await resume.count())await resume.click();
 await page.getByRole('button',{name:'Adaptive Grid',exact:true}).click();
 const grid=page.locator('.pui-Grid'),editor=grid.locator('input');
 await page.getByRole('radio',{name:'Dense (True)',exact:true}).check();
 await page.getByRole('checkbox',{name:'Show C',exact:true}).check();
 await grid.locator('.pui-Label').filter({hasText:/^C\s/}).waitFor();
 if((await grid.locator('.pui-Label').first().innerText()).startsWith('G'))await page.getByRole('button',{name:'Reverse tiles',exact:true}).click();
 const columns=async n=>page.waitForFunction(n=>{
  const grid=document.querySelector('.pui-Grid');return grid && getComputedStyle(grid).gridTemplateColumns.split(' ').length===n;
 },n);
 await columns(4);
 const f=grid.locator('.pui-Label').filter({hasText:/^F\s/}),positions={};
 for(const [mode,row] of [['Ordered (None)',4],['Dense (True)',3],['Forward (False)',5]]){
  await page.getByRole('radio',{name:mode,exact:true}).check();
  await page.waitForFunction(row=>{
   const f=[...document.querySelectorAll('.pui-Grid > .pui-Label')].find(e=>/^F\s/.test(e.textContent));
   return f && f.style.gridRowStart===String(row);
  },row);
  positions[row]=(await f.boundingBox()).y;
  assert.equal(await f.evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(54, 108, 145)','Delft blue was lost');
  await page.screenshot({path:`/tmp/pui-adaptive-grid-row-${row}.png`});
 }
 assert.ok(positions[3]<positions[4] && positions[4]<positions[5],'All three modes must visibly move the gap-filling F card');
 await editor.fill('draft survives resize');
 await editor.evaluate(e=>{window.gridEditor=e;});
 for(const width of [390,650,850,2000]){
  await page.setViewportSize({width,height:1100});
  await page.waitForFunction(()=>{
   const grid=document.querySelector('.pui-Grid'),width=grid.parentElement.clientWidth;
   return getComputedStyle(grid).gridTemplateColumns.split(' ').length===(width>=240?4:width>=180?3:width>=120?2:1);
  });
  assert.equal(await editor.inputValue(),'draft survives resize');
  assert.equal(await editor.evaluate(e=>e===window.gridEditor),true);
  assert.equal(await editor.evaluate(e=>document.activeElement===e),true);
 }
 await columns(4);
 await page.getByRole('checkbox',{name:'Show C',exact:true}).uncheck();
 await page.getByRole('button',{name:'Reverse tiles',exact:true}).click();
 assert.equal(await editor.evaluate(e=>e===window.gridEditor),true);
 assert.equal(await editor.inputValue(),'draft survives resize');
 assert.deepEqual(errors,[]);
 await page.getByRole('checkbox',{name:'Show C',exact:true}).check();
 await page.getByRole('button',{name:'Reverse tiles',exact:true}).click();
 await page.getByRole('radio',{name:'Ordered (None)',exact:true}).check();
 await page.waitForTimeout(150);
 await page.screenshot({path:'/tmp/pui-adaptive-grid-web.png'});
 console.log('Adaptive Grid: dense, resizing, draft/focus retention, visibility and reordering passed');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
