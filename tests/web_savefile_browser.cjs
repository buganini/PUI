// Starts isolated and passthru servers and exercises the actual SaveFile modal.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const os=require('node:os');
const {spawn}=require('node:child_process');
const {createRequire}=require('node:module');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
(async()=>{
  const root=fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(),'pui-savefile-browser-')));
  fs.mkdirSync(path.join(root,'folder'));
  fs.writeFileSync(path.join(root,'folder','existing.txt'),'keep');
  const browser=await chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
  try {
    for(const passthru of [false,true]){
      const port=passthru?18869:18868;
      const server=spawn('env/bin/python',['-m','PUI.web','web_savefile_fixture:App','--bind',`127.0.0.1:${port}`,'--webroot',root,...(passthru?['--passthru']:[])],{env:{...process.env,PYTHONPATH:'tests:.'},stdio:['ignore','pipe','pipe']});
      let logs='';server.stdout.on('data',b=>logs+=b);server.stderr.on('data',b=>logs+=b);
      const page=await browser.newPage(),errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      try {
        const url=`http://127.0.0.1:${port}/`;
        let started=false;
        for(let i=0;i<100;i++){
          try{await fetch(url);started=true;break;}catch{await new Promise(r=>setTimeout(r,50));}
        }
        assert.ok(started,logs);
        await page.goto(url);
        const dialog=page.getByRole('dialog');
        const open=()=>page.getByRole('button',{name:'Save File',exact:true}).click();
        await open();
        await dialog.getByRole('heading',{name:'Save report'}).waitFor();
        assert.deepEqual(await dialog.getByRole('button').allTextContents(),['Download','Save to Server','Cancel']);
        await page.screenshot({path:`/tmp/pui-savefile-${passthru?'passthru':'isolated'}.png`});
        await dialog.getByRole('button',{name:'Cancel',exact:true}).click();
        await page.getByText('None',{exact:true}).waitFor();
        await open();await dialog.getByRole('button',{name:'Download',exact:true}).click();
        await dialog.getByLabel('File name').fill('../bad.txt');
        await dialog.getByRole('button',{name:'Download',exact:true}).click();
        await dialog.getByRole('alert').waitFor();
        await dialog.getByLabel('File name').fill('download.txt');
        await dialog.getByRole('button',{name:'Download',exact:true}).click();
        await page.locator('.pui-Label').filter({hasText:/pui-download-.*download.txt/}).waitFor();
        await open();await dialog.getByRole('button',{name:'Save to Server',exact:true}).click();
        assert.equal(await dialog.getByRole('button',{name:'Up',exact:true}).isDisabled(),true);
        await dialog.getByLabel('File name').fill('draft.txt');
        await dialog.getByRole('button',{name:'▸ folder',exact:true}).click();
        assert.equal(await dialog.getByLabel('File name').inputValue(),'draft.txt');
        await dialog.getByRole('button',{name:'existing.txt',exact:true}).click();
        await dialog.getByRole('button',{name:'Save',exact:true}).click();
        await dialog.getByRole('button',{name:'Replace',exact:true}).waitFor();
        await page.keyboard.press('Escape');
        await page.getByText('None',{exact:true}).waitFor();
        assert.equal(fs.readFileSync(path.join(root,'folder','existing.txt'),'utf8'),'keep');
        await open();await dialog.getByRole('button',{name:'Save to Server',exact:true}).click();
        await dialog.getByLabel('File name').fill('new.txt');
        await dialog.getByRole('button',{name:'Save',exact:true}).click();
        await page.getByText(path.join(root,'new.txt'),{exact:true}).waitFor();
        assert.equal(fs.existsSync(path.join(root,'new.txt')),false);
        assert.deepEqual(errors,[]);
        console.log(`${passthru?'Passthru':'Isolated'} SaveFile: choices, download staging, browsing, overwrite cancellation and server path passed.`);
      }finally{
        await page.close();
        server.kill('SIGTERM');
        await new Promise(resolve=>{if(server.exitCode!==null)return resolve();server.once('exit',resolve);});
        if(errors.length)console.error(logs);
      }
    }
  }finally{await browser.close();fs.rmSync(root,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
