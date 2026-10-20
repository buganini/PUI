// Run against: PYTHONPATH=tests:. env/bin/python -m PUI.web web_dialog_fixture:App --bind 127.0.0.1:18866
const assert=require('node:assert/strict');
const path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
  ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=requireBrowser('playwright');
(async()=>{
  const browser=await chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
  try {
    const page=await browser.newPage(), errors=[], dialogs=[];
    page.on('pageerror',error=>errors.push(error.message));
    let confirm=true, text='browser answer';
    page.on('dialog',async dialog=>{
      dialogs.push(dialog.type());
      if(dialog.type()==='confirm'){
        assert.equal(dialog.message(),'Test\n\nContinue?');
        if(confirm)await dialog.accept();else await dialog.dismiss();
      }else if(dialog.type()==='prompt'){
        assert.equal(dialog.defaultValue(),'initial');
        if(text===null)await dialog.dismiss();else await dialog.accept(text);
      }else await dialog.accept();
    });
    await page.goto(process.env.PUI_WEB_URL||'http://127.0.0.1:18866/');
    await page.getByRole('button',{name:'Ask',exact:true}).click();
    await page.getByText("(True, 'browser answer')",{exact:true}).waitFor();
    confirm=false;text=null;
    await page.getByRole('button',{name:'Ask',exact:true}).click();
    await page.getByText('(False, None)',{exact:true}).waitFor();
    confirm=true;text='';
    await page.getByRole('button',{name:'Ask',exact:true}).click();
    await page.getByText("(True, '')",{exact:true}).waitFor();
    assert.deepEqual(dialogs,['confirm','prompt','alert','confirm','prompt','alert','confirm','prompt','alert']);
    assert.deepEqual(errors,[]);
    console.log('Native browser dialogs: sync callback results, accept, cancel and empty prompt passed.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
