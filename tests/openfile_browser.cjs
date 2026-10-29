// End-to-end file pickers: HTTP uploads, server browsing and Pyodide's virtual FS.
const assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs'),os=require('node:os');
const {spawn}=require('node:child_process'),{createRequire}=require('node:module');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
(async()=>{
 const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'pui-openfile-')));
 fs.mkdirSync(path.join(root,'dataset/sub'),{recursive:true});fs.writeFileSync(path.join(root,'dataset/sub/data.txt'),'nested');
 fs.writeFileSync(path.join(root,'one.txt'),'one');fs.writeFileSync(path.join(root,'two.txt'),'two');
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  for(const backend of process.env.PUI_TEST_BACKEND?[process.env.PUI_TEST_BACKEND]:['web','passthru','pyodide']){
   const isPython=backend==='pyodide',port=backend==='web'?18872:18873;
   let logs='',server;
   if(!isPython){server=spawn('env/bin/python',['-m','PUI.web','web_openfile_fixture:App','--bind',`127.0.0.1:${port}`,'--webroot',root,...(backend==='passthru'?['--passthru']:[])],{env:{...process.env,PYTHONPATH:'tests:.'}});server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);}
   const page=await browser.newPage(),errors=[];page.setDefaultTimeout(15000);page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')logs+=m.text()+'\n';});
   try{
    const url=isPython?(process.env.PUI_PYODIDE_URL||'http://127.0.0.1:8868/cookbook/cookbook.html'):`http://127.0.0.1:${port}/`;
    if(!isPython){let ready=false;for(let i=0;i<100;i++){try{await fetch(url);ready=true;break}catch{await new Promise(r=>setTimeout(r,50))}}assert.ok(ready,logs);}
    await page.goto(url);
    if(isPython){await page.getByRole('button',{name:'Dialog',exact:true}).waitFor({timeout:180000});await page.getByRole('button',{name:'Dialog',exact:true}).click();}
    const dialog=page.getByRole('dialog');
    const open=async name=>{await page.getByRole('button',{name,exact:true}).click();await dialog.waitFor();if(process.env.PUI_SCREENSHOTS)await page.screenshot({path:path.join(process.env.PUI_SCREENSHOTS,backend+'-'+name.replaceAll(' ','-')+'.png')})};
    const selected=async text=>{await dialog.waitFor({state:'detached'});await page.locator('.pui-Label').filter({hasText:text}).first().waitFor()};
    await open('Open File');
    await dialog.locator('input[type=file]').setInputFiles({name:'device.txt',mimeType:'text/plain',buffer:Buffer.from('device')});
    await selected(/content\/device.txt/);
    if(!isPython){const result=await page.locator('.pui-Label').filter({hasText:/content\/device.txt/}).textContent();assert.equal(fs.readFileSync(result,'utf8'),'device');}
    await open('Open Files');
    // A synthetic DataTransfer exercises the real drop handler and upload transport.
    await dialog.locator('.pui-openfile-device').evaluate(e=>{const dt=new DataTransfer();dt.items.add(new File(['a'],'first.txt'));dt.items.add(new File(['b'],'second.txt'));e.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}));});
    await selected(/content\/second.txt/);
    await open('Open Directory');
    await dialog.getByText('Folder drag & drop is not supported.',{exact:true}).waitFor();
    await dialog.locator('.pui-openfile-device').evaluate(e=>{const dt=new DataTransfer();dt.items.add(new File(['a'],'not-a-folder.txt'));e.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true}));});
    await dialog.getByRole('alert').waitFor();assert.equal(await dialog.isVisible(),true);
    await dialog.locator('input[type=file]').setInputFiles(path.join(root,'dataset'));
    await selected(/content\/dataset/);
    if(!isPython){const result=await page.locator('.pui-Label').filter({hasText:/content\/dataset/}).textContent();assert.equal(fs.readFileSync(path.join(result,'sub/data.txt'),'utf8'),'nested');}
    if(!isPython){
      await open('Open Files');
      await dialog.getByRole('button',{name:'one.txt File',exact:true}).click();
      await dialog.getByRole('button',{name:'two.txt File',exact:true}).click();
      await dialog.getByText('2 files selected',{exact:true}).waitFor();
      await dialog.getByRole('button',{name:'dataset Folder',exact:true}).click();
      await dialog.getByRole('button',{name:'sub Folder',exact:true}).click();
      await dialog.getByRole('button',{name:'data.txt File',exact:true}).click();
      await dialog.getByText('3 files selected',{exact:true}).waitFor();
      await dialog.getByRole('button',{name:'Up',exact:true}).click();
      await dialog.getByRole('button',{name:'sub Folder',exact:true}).waitFor();
      await dialog.getByRole('button',{name:'Up',exact:true}).click();
      const one=dialog.getByRole('button',{name:'one.txt File',exact:true});await one.waitFor();
      assert.equal(await one.getAttribute('aria-pressed'),'true');
      await one.click();await dialog.getByText('2 files selected',{exact:true}).waitFor();
      await dialog.getByRole('button',{name:'Open',exact:true}).click();await selected(/two.txt/);
      const combined=await page.locator('.pui-Label').filter({hasText:/two.txt/}).textContent();
      assert.ok(combined.includes(path.join(root,'dataset/sub/data.txt')));assert.ok(!combined.includes('one.txt'));
      await open('Open Directory');
      await page.evaluate(()=>window.pickerNode=document.querySelector('dialog'));
      await dialog.getByRole('button',{name:'dataset Folder',exact:true}).click();
      const directory=dialog.getByRole('textbox',{name:'Directory',exact:true});
      const waitPath=value=>page.waitForFunction(value=>document.querySelector('dialog input[aria-label="Directory"]')?.value===value,value);
      await waitPath(path.join(root,'dataset'));
      await dialog.getByRole('button',{name:'Up',exact:true}).click();await waitPath(root);
      await directory.fill(path.dirname(root));await dialog.getByRole('button',{name:'Go',exact:true}).click();
      await dialog.getByRole('alert').filter({hasText:'outside webroot'}).waitFor();await waitPath(root);
      await directory.fill(path.join(root,'dataset'));await directory.press('Enter');await waitPath(path.join(root,'dataset'));
      await dialog.getByRole('button',{name:'Up',exact:true}).click();await waitPath(root);
      await directory.fill(path.join(root,'dataset'));await dialog.getByRole('button',{name:'Go',exact:true}).click();await waitPath(path.join(root,'dataset'));
      assert.ok(await page.evaluate(()=>window.pickerNode===document.querySelector('dialog')));
      await dialog.getByRole('button',{name:'Open this folder',exact:true}).click();await selected(path.join(root,'dataset'));
    }
    await open('Open File');await page.keyboard.press('Escape');await selected(/None/);
    assert.deepEqual(errors,[]);console.log(backend+': file, multiple/drop, directory selection, cancellation'+(!isPython?', server selection and retained modal':'')+' passed');
   }catch(e){console.error(logs);throw e}finally{await page.close();if(server){server.kill('SIGTERM');await new Promise(resolve=>{server.once('exit',resolve);setTimeout(resolve,3000)})}}
  }
 }finally{await browser.close();fs.rmSync(root,{recursive:true,force:true})}
})().catch(e=>{console.error(e);process.exitCode=1});
