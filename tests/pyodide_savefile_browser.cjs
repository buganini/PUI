// Run against the built static Pyodide cookbook (no application server).
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
const {createRequire}=require('node:module');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[];
  page.setDefaultTimeout(45000);
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error'){errors.push(m.text());console.error(m.text());}});
  await page.addInitScript(()=>{
   window.sizePolls=0;window.blobs=new Set();
   const W=Worker,create=URL.createObjectURL,revoke=URL.revokeObjectURL;
   URL.createObjectURL=function(...args){const url=create.apply(this,args);window.blobs.add(url);return url;};
   URL.revokeObjectURL=function(url){window.blobs.delete(url);return revoke.call(this,url);};
   window.Worker=class extends W {postMessage(m,...args){if(m.type==='downloads' && m.action==='list' && m.keys!==null)window.sizePolls++;super.postMessage(m,...args);}};
  });
  await page.goto(process.env.PUI_PYODIDE_URL||'http://127.0.0.1:8868/cookbook/cookbook.html');
  await page.getByRole('button',{name:'Imperative',exact:true}).waitFor({timeout:180000});
  await page.getByRole('button',{name:'Imperative',exact:true}).click();
  const open=()=>page.getByRole('button',{name:'Save File',exact:true}).click();
  const dialog=page.getByRole('dialog');
  for(const kind of ['Information','Warning','Critical']){
    await page.getByRole('button',{name:kind,exact:true}).click();
    await dialog.getByRole('heading').waitFor();
    if(kind==='Warning')await page.keyboard.press('Escape');
    else await dialog.getByRole('button',{name:'OK',exact:true}).click();
    await dialog.waitFor({state:'detached'});
  }
  await page.getByRole('button',{name:'Confirm',exact:true}).click();
  await dialog.getByRole('button',{name:'Cancel',exact:true}).click();
  await page.getByText('Confirm: False',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Confirm',exact:true}).click();
  await dialog.getByRole('button',{name:'OK',exact:true}).click();
  await page.getByText('Confirm: True',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Prompt',exact:true}).click();
  assert.equal(await dialog.getByRole('textbox').inputValue(),'default');
  await dialog.getByRole('textbox').fill('');
  await page.keyboard.press('Enter');
  await page.getByText('Prompt:',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Prompt',exact:true}).click();
  await dialog.getByRole('textbox').waitFor();await page.keyboard.press('Escape');
  await page.getByText('Prompt: None',{exact:true}).waitFor();

  await open();
  await dialog.getByLabel('File name').waitFor();
  assert.equal(await dialog.getByRole('button',{name:'Save to Server'}).count(),0);
  await page.keyboard.press('Escape');
  await dialog.waitFor({state:'detached'});
  await open();
  await dialog.getByLabel('File name').fill('../bad');
  await dialog.getByRole('button',{name:'Download',exact:true}).click();
  await dialog.getByRole('alert').waitFor();
  await dialog.getByLabel('File name').fill('pyodide-report.txt');
  await dialog.getByRole('button',{name:'Download',exact:true}).click();
  const shelf=page.getByRole('complementary',{name:'Downloads'});
  await shelf.getByText('22 bytes',{exact:true}).waitFor();
  const downloaded=page.waitForEvent('download');
  await shelf.getByRole('link',{name:'Download',exact:true}).click();
  const artifact=await downloaded;
  assert.equal(artifact.suggestedFilename(),'pyodide-report.txt');
  assert.equal(fs.readFileSync(await artifact.path(),'utf8'),'PUI cookbook download\n');
  await shelf.getByRole('button',{name:'Dismiss pyodide-report.txt',exact:true}).click();
  const count=await page.evaluate(()=>window.sizePolls);
  await page.waitForTimeout(1500);
  assert.equal(await page.evaluate(()=>window.sizePolls),count);
  assert.equal(await page.evaluate(()=>window.blobs.size),0);
  assert.deepEqual(errors,[]);
  console.log('Pyodide generic dialogs and SaveFile: sync cancellation, validation, virtual file, Blob download, polling stop and URL cleanup passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
