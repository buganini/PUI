const login=require('./web_login.cjs');
// Cross-language streaming validation using the packaged browser decoder.
const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const {spawnSync}=require('node:child_process');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');
const python=process.env.PUI_PYTHON || 'env/bin/python';
const run=source=>{
 const result=spawnSync(python,['-c',source],{encoding:'utf8',env:{...process.env,PYTHONPATH:'tests'}});
 assert.equal(result.status,0,result.stderr);return JSON.parse(result.stdout);
};
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[],frames=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('console',message=>{if(message.type()==='error')errors.push(message.text());});
  page.on('websocket',socket=>socket.on('framereceived',frame=>frames.push(Buffer.from(frame.payload).toString('base64'))));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
  await page.getByRole('button',{name:'Canvas',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.pui-Canvas canvas')?.width>0);
  await page.getByRole('button',{name:'+',exact:true}).click();
  await page.getByText('Rotate: 30',{exact:true}).waitFor();
  const rendered=await page.evaluate(async values=>{
   const {StreamDecoder}=await import(document.querySelector('script[type=module]').src);
   const decoder=new StreamDecoder();
   const messages=values.map(value=>decoder.decode(Uint8Array.from(atob(value),c=>c.charCodeAt(0))));
   decoder.close();return messages;
  },frames);
  assert.equal(rendered[0].type,'ready');
  assert(rendered.some(m=>m.type==='render' && m.body.ops?.some(op=>op.op==='put_canvas' && op.frame.commands.length)));
  const fixtures=run("import runpy,sys; sys.argv=['web_stream.py','--fixtures']; runpy.run_path('tests/web_stream.py',run_name='__main__')");
  const packets=run(`
import base64,json
from PUI.web.protocol import StreamCodec,Limits
codec=StreamCodec()
values=[{'v':1,'type':'render','session':'test','seq':i+1,'body':{'data':[['line',j,j*.3,str(j)] for j in range(4000)],'unicode':'中文','binary':b'\\x00\\xff'}} for i in range(4)]
values.append({'v':1,'type':'render','session':'test','seq':5,'body':{'items':[0]*(Limits().max_items-13)}})
values.append({'v':1,'type':'render','session':'test','seq':6,'body':{'args':[float('nan'),float('inf'),2**60]}})
print(json.dumps([base64.b64encode(codec.encode(v)).decode('ascii') for v in values]))
`);
  await page.evaluate(async({fixtures,packets})=>{
   const {StreamDecoder}=await import(document.querySelector('script[type=module]').src);
   const bytes=v=>Uint8Array.from(atob(v),c=>c.charCodeAt(0));
   const check=(v,m)=>{if(!v)throw new Error(m);};
   // Interleaving independent streams must not share history or decoder storage.
   const decoders=[new StreamDecoder(),new StreamDecoder()];
   for(let i=0;i<packets.length;i++)for(const decoder of decoders){
    const value=decoder.decode(bytes(packets[i]));
    check(value.seq===i+1,'Sequence changed');
    if(i<4)check(value.body.unicode==='中文' && value.body.binary[1]===255 && value.body.data.length===4000,'Incomplete batch');
    else if(i===4)check(value.body.items.length===1000000-13,'Aggregate limit mismatch');
    else check(Number.isNaN(value.body.args[0]) && value.body.args[1]===Infinity && value.body.args[2]===2**60,'Render arguments rejected by decoder');
   }
   check(packets[3].length<packets[0].length/10,'Stream did not retain history');
   for(const decoder of decoders)decoder.close();
   for(const [name,packet] of Object.entries(fixtures)){
    const decoder=new StreamDecoder();let error;
    try{decoder.decode(bytes(packet));}catch(e){error=e;}
    check(error,'Malformed stream accepted: '+name);
    error=null;try{decoder.decode(bytes(packets[0]));}catch(e){error=e;}
    check(error && /closed/.test(error.message),'Failed stream reused: '+name);
   }
   // A reconnect starts from a fresh header, not from a previous flush chunk.
   let error;try{new StreamDecoder().decode(bytes(packets[1]));}catch(e){error=e;}
   check(error,'Continuation accepted without history');
   check(new StreamDecoder().decode(bytes(packets[0])).seq===1,'Fresh connection failed');
  },{fixtures,packets});
  assert.deepEqual(errors,[]);
  console.log('Downstream stream: full DOM/Canvas batches, history reuse, isolated contexts, Unicode/binary, million-item boundary and malformed/oversized batches passed in Chrome.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
