// Static prefix, unavailable CDN, mixed build, restart and independent interpreters.
const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const browser=await req('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext(),page=await context.newPage();page.setDefaultTimeout(180000);
  const url=process.env.PUI_PYODIDE_URL || 'http://localhost:8869/pyodide/cookbook/cookbook.html';
  const cdn='https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs';
  await context.route(cdn,route=>route.abort());
  await page.goto(url);
  await page.getByRole('status').filter({hasText:'Unable to run cookbook'}).waitFor();
  await context.unroute(cdn);
  await context.route('**/app.zip?*',route=>route.fulfill({status:200,body:'incorrect cached build'}));
  await page.getByRole('button',{name:'Restart Python',exact:true}).click();
  await page.getByRole('status').filter({hasText:'archive version mismatch'}).waitFor();
  await context.unroute('**/app.zip?*');
  await page.getByRole('button',{name:'Restart Python',exact:true}).click();
  await page.getByText('Row 1',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Button',exact:true}).click();
  await page.getByRole('button',{name:'B',exact:true}).click();
  await page.locator('.pui-Label').getByText('B',{exact:true}).waitFor();
  const second=await context.newPage();second.setDefaultTimeout(180000);await second.goto(url);
  await second.getByRole('button',{name:'Button',exact:true}).click();
  await second.locator('.pui-Label').getByText('A',{exact:true}).waitFor();
  assert.equal(await page.locator('.pui-Label').getByText('B',{exact:true}).count(),1);
  await page.reload();await page.getByRole('button',{name:'Button',exact:true}).click();
  await page.locator('.pui-Label').getByText('A',{exact:true}).waitFor();
  assert.equal(await page.locator('#pui-status').isVisible(),false);
  assert.equal(await second.locator('#pui-status').isVisible(),false);
  console.log('Pyodide bootstrap: URL prefix, CDN failure, archive mismatch, retry, fresh reload and independent tabs passed.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
