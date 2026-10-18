const assert=require('node:assert/strict'),path=require('node:path');
const req=process.env.PUI_BROWSER_MODULES?require('node:module').createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[],alerts=[];
  page.on('pageerror',e=>errors.push(e.message));
  page.on('dialog',async d=>{alerts.push(d.message());console.log('alert:',d.message());await d.accept();});
  await page.goto(process.env.PUI_WEB_URL||'http://localhost:8879/drop-test/');
  await page.getByText('Waiting',{exact:true}).waitFor();
  let uploads=0;page.on('request',r=>{if(r.url().endsWith('/pui/upload'))uploads++;});
  async function drop(target,files,text=''){
   await page.getByText(target,{exact:true}).evaluate((e,{files,text})=>{
    const dt=new DataTransfer();Object.defineProperty(dt,'effectAllowed',{value:'copy'});for(const [name,value] of files)dt.items.add(new File([value],name,{type:'text/plain'}));
    if(text)dt.setData('text/plain',text);
    e.dispatchEvent(new DragEvent('dragenter',{bubbles:true,cancelable:true,dataTransfer:dt}));
    e.dispatchEvent(new DragEvent('dragover',{bubbles:true,cancelable:true,dataTransfer:dt}));
    e.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));
   },{files,text});
  }
  await drop('Accept',[['sample.TXT','browser uploaded']]);
  await page.getByText('browser uploaded',{exact:true}).waitFor();
  assert.equal(uploads,1);
  await drop('Accept',[['bad.exe','bad']]);
  await page.waitForFunction(()=>true); // dialog handler runs in the same input turn
  assert(alerts.some(a=>a.includes('Unsupported file extension')));
  assert.equal(uploads,1,'Invalid extension must not upload');
  await drop('Reject',[['reject.txt','reject']]);
  for(let n=0;n<100&&!alerts.includes('Rejected by application');n++)await page.waitForTimeout(20);
  assert(alerts.includes('Rejected by application'));
  await drop('Accept',[],'dropped text');
  await page.getByText('dropped text',{exact:true}).waitFor();
  assert.deepEqual(errors,[]);
  console.log('Browser drop: multipart upload, case-insensitive preflight, reject alert and text passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
