// Real worker startup, string options, State refs, reload and interpreter restart.
const assert = require('node:assert/strict');
const path = require('node:path');
const {createRequire} = require('node:module');
const req = process.env.PUI_BROWSER_MODULES ? createRequire(path.join(process.env.PUI_BROWSER_MODULES, 'package.json')) : require;
(async () => {
  const browser = await req('playwright').chromium.launch({executablePath: process.env.PUI_CHROME || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox']});
  try {
    const page = await browser.newPage();
    page.setDefaultTimeout(180000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const url = process.env.PUI_PYODIDE_URL || 'http://localhost:8868/cookbook/cookbook.html';
    await page.goto(url + '#cookbook.page=Button#unrelated=00123');
    await page.getByRole('button', {name: 'B', exact: true}).waitFor();
    const length = await page.evaluate(() => history.length);
    await page.getByRole('button', {name: 'Label', exact: true}).click();
    await page.waitForFunction(() => location.hash.includes('cookbook.page=Label'));
    assert.equal(await page.evaluate(() => history.length), length);
    assert.match(new URL(page.url()).hash, /unrelated=00123/);
    await page.reload();
    await page.waitForFunction(() => document.querySelector('#pui-status').hidden);
    assert.match(new URL(page.url()).hash, /cookbook.page=Label/);
    await page.evaluate(async()=>{const client=await import(document.querySelector('script[type=module]').src);client.start();});
    await page.waitForFunction(() => document.querySelector('#pui-status').hidden);
    assert.match(new URL(page.url()).hash, /cookbook.page=Label/);
    assert.deepEqual(errors, []);
    console.log('Pyodide URL options and State refs: startup, replaceState, reload and restart passed.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
