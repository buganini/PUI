const assert=require('node:assert/strict'),path=require('node:path');
const req=process.env.PUI_BROWSER_MODULES?require('node:module').createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const browser=await req('playwright').chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[],alerts=[];page.setDefaultTimeout(90000);
  page.on('pageerror',e=>{errors.push(e.message);console.log('error:',e.message);});
  page.on('console',m=>{if(m.type()==='error')console.log(m.text());});
  page.on('dialog',async d=>{alerts.push(d.message());console.log('alert:',d.message());await d.accept();});
  await page.goto(process.env.PUI_PYODIDE_URL||'http://127.0.0.1:8880/cookbook/cookbook.html');
  await page.getByRole('button',{name:'Drop',exact:true}).click();
  await page.getByText('DROP HERE',{exact:true}).waitFor();
  async function drop(name){await page.getByText('DROP HERE',{exact:true}).evaluate((e,name)=>{
    const dt=new DataTransfer();Object.defineProperty(dt,'effectAllowed',{value:'copy'});
    dt.items.add(new File(['hello'],name,{type:'text/plain'}));
    e.dispatchEvent(new DragEvent('drop',{bubbles:true,cancelable:true,dataTransfer:dt}));
  },name);}
  await drop('browser.txt');
  await page.getByText('browser.txt: 5 bytes (temporary=True)',{exact:false}).waitFor();
  await page.getByRole('checkbox',{name:'Reject this drop'}).check();
  await drop('rejected.txt');
  for(let n=0;n<200&&!alerts.includes('Rejected by the example');n++)await page.waitForTimeout(20);
  assert(alerts.includes('Rejected by the example'));
  assert.deepEqual(errors,[]);console.log('Pyodide drop: File stream to virtual FS, callback and reject alert passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
