const assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const path=require('node:path');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://127.0.0.1:8868/pui/');
  await page.getByRole('button',{name:'Table',exact:true}).click();
  const table=page.locator('.pui-Table');await table.locator('tbody tr').first().waitFor();
  const cell=table.locator('tbody tr').first().locator('td').first();
  await cell.click();await cell.locator('input').fill('changed');await cell.locator('input').press('Enter');
  await page.getByText('A1: changed',{exact:true}).first().waitFor();
  await cell.locator('input').waitFor({state:'detached'});
  await cell.click();await cell.locator('input').fill('discard');await cell.locator('input').press('Escape');
  assert.equal(await cell.innerText(),'A1: changed');
  const choice=table.locator('tbody tr').first().locator('td').nth(3);
  await choice.click();await choice.locator('select').selectOption({value:'3'});
  await page.getByText('Sides: 6',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Table(Adapter)',exact:true}).click();
  await page.locator('.pui-Table').nth(1).waitFor();
  const number=page.locator('.pui-Table').first().locator('td').first();
  await number.click();await number.locator('input').fill('bad');await number.locator('input').press('Enter');
  await number.locator('[aria-invalid=true]').waitFor();
  await number.locator('input').fill('91');await number.locator('input').press('Tab');
  await page.waitForFunction(()=>[...document.querySelectorAll('.pui-Table')].every(t=>t.querySelector('td').textContent==='91'));
  await page.reload();await page.locator('.pui-Table').nth(1).waitFor();
  assert.equal(await page.locator('.pui-Table').first().locator('td').first().innerText(),'91');
  assert.deepEqual(errors,[]);
  console.log('Table browser checks passed: inline edits, display, cancel, choices, validation, shared adapter, reconnect.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
