const assert=require('node:assert/strict');
const path=require('node:path');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const build=createRequire(path.join(root,'env/web-client/package.json'));
const modules=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[path.join(root,'browser-client/shared/open-url.js')],bundle:true,write:false,format:'iife',globalName:'PUIURL'});
 const browser=await modules('playwright').chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext();
  await context.route('https://example.com/**',r=>r.fulfill({body:'URL destination'}));
  const page=await context.newPage();await page.setContent('<button id="open">Website</button>');
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>document.getElementById('open').onclick=()=>PUIURL.openURL('https://example.com/target'));
  const pending=page.waitForEvent('popup');await page.click('#open');const popup=await pending;
  await popup.waitForURL('https://example.com/target');
  assert.equal(await popup.evaluate(()=>window.opener),null);await popup.close();
  await page.evaluate(()=>{window.open=()=>null;PUIURL.openURL('https://example.com/blocked');});
  const link=page.locator('dialog a');assert.equal(await link.getAttribute('rel'),'noopener noreferrer');
  const fallback=page.waitForEvent('popup');await link.click();const second=await fallback;
  await second.waitForURL('https://example.com/blocked');assert.equal(await second.evaluate(()=>window.opener),null);
  await second.close();await page.waitForFunction(()=>!document.querySelector('dialog'));
  await page.evaluate(()=>{PUIURL.openURL('https://example.com/cancel');PUIURL.dismissOpenURLs();});
  assert.equal(await page.locator('dialog').count(),0);
  for(const url of ['javascript:alert(1)','/relative','data:text/html,x']) {
    assert.equal(await page.evaluate(url=>{try{PUIURL.openURL(url);return false;}catch{return true;}},url),true);
  }
  console.log('OpenURL: real popup, opener isolation, blocked-popup link, cleanup and URL validation passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
