// Model/effort controls retain drafts while streamed conversation state updates.
const assert=require('node:assert/strict'),path=require('node:path');
const req=process.env.PUI_BROWSER_MODULES?require('node:module').createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
const {buildSync}=require('../env/web-client/node_modules/esbuild');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://pui.test/**',r=>r.fulfill({contentType:'text/html',body:'<main data-ai="/ai" data-resume-owner="test"></main>'}));
  await page.goto('http://pui.test/');
  await page.evaluate(()=>{
   window.sent=[];
   window.WebSocket=class {static OPEN=1;readyState=1;constructor(){window.socket=this;}send(data){sent.push(JSON.parse(data));}};
  });
  const code=buildSync({entryPoints:[path.join(__dirname,'../browser-client/web/ai.js')],bundle:true,format:'iife',globalName:'AI',write:false}).outputFiles[0].text;
  await page.addScriptTag({content:code});
  await page.evaluate(()=>{
   AI.startAI(document.querySelector('main'),{resumeId:()=> 'worker',renew:()=>{}});
   window.state={type:'state',conversation:'chat',providers:['codex','claude'],cwd:'/test',busy:false,messages:[],approvals:[],renew:0,
    selections:{codex:{model:'configured',effort:'high'},claude:{model:'',effort:''}},
    models:{codex:[{model:'configured',efforts:['low','high']},{model:'other',efforts:['medium']}]},effort_levels:{claude:['low','medium','high']}};
   socket.onmessage({data:JSON.stringify(state)});
  });
  assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'configured');
  await page.getByLabel('Model',{exact:true}).fill('other');
  assert.deepEqual(await page.getByLabel('Effort',{exact:true}).locator('option').evaluateAll(es=>es.map(e=>e.value)),['','medium']);
  await page.getByLabel('Effort',{exact:true}).selectOption('medium');
  await page.evaluate(()=>socket.onmessage({data:JSON.stringify(state)}));
  assert.equal(await page.getByLabel('Model',{exact:true}).inputValue(),'other');
  await page.getByLabel('AI provider').selectOption('claude');
  await page.getByLabel('AI provider').selectOption('codex');
  assert.equal(await page.getByLabel('Effort',{exact:true}).inputValue(),'medium');
  await page.getByLabel('Prompt',{exact:true}).fill('test');await page.getByRole('button',{name:'Send',exact:true}).click();
  assert.deepEqual(await page.evaluate(()=>sent.at(-1).settings),{model:'other',effort:'medium'});
  await page.evaluate(()=>socket.onmessage({data:JSON.stringify(state)}));
  await page.getByLabel('Model',{exact:true}).fill('');await page.getByLabel('Effort',{exact:true}).selectOption('');
  await page.getByLabel('Prompt',{exact:true}).fill('default');await page.getByRole('button',{name:'Send',exact:true}).click();
  assert.deepEqual(await page.evaluate(()=>sent.at(-1).settings),{model:'',effort:''});
  assert.deepEqual(errors,[]);console.log('AI model/effort browser controls passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
