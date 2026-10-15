const assert=require('node:assert/strict');
const path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');
const login=require('./web_login.cjs');

(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage({viewport:{width:1200,height:800}}),errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
  await page.getByRole('button',{name:'MaskedField',exact:true}).click();
  const fields=page.locator('.pui-MaskedField');
  await fields.first().waitFor();
  assert.equal(await fields.count(),2);
  assert.deepEqual(await fields.evaluateAll(es=>es.map(e=>e.type)),['password','password']);
  await fields.first().fill('abc123');
  assert.deepEqual(await page.locator('.pui-Label').filter({hasText:/^Committed length:/}).allTextContents(),
   ['Committed length: 0','Committed length: 0']);
  await fields.first().press('Enter');
  await page.getByText('Committed length: 6',{exact:true}).waitFor();
  await fields.nth(1).fill('draft');
  await page.getByText('Editing length: 5',{exact:true}).waitFor();
  await fields.nth(1).press('Tab');
  await page.getByText('Committed length: 5',{exact:true}).waitFor();
  assert.equal((await page.locator('#pui-root').innerText()).includes('abc123'),false);
  assert.equal((await page.locator('#pui-root').innerText()).includes('draft'),false);
  await page.reload();
  await page.getByRole('button',{name:'Resume session',exact:true}).click();
  await page.getByText('Committed length: 6',{exact:true}).waitFor();
  assert.equal(await fields.first().inputValue(),'abc123');
  assert.equal(await fields.first().getAttribute('type'),'password');
  await fields.first().fill('another draft');
  await page.getByRole('button',{name:'Clear passwords',exact:true}).click();
  await page.waitForFunction(()=>[...document.querySelectorAll('.pui-MaskedField')].every(e=>e.value===''));
  assert.deepEqual(await page.locator('.pui-Label').filter({hasText:/^Committed length:/}).allTextContents(),
   ['Committed length: 0','Committed length: 0']);
  if(process.env.PUI_SCREENSHOT)await page.screenshot({path:process.env.PUI_SCREENSHOT});
  assert.deepEqual(errors,[]);
  console.log('MaskedField cookbook passed: password inputs, local drafts, editing buffer, Enter/blur, resume and clear.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
