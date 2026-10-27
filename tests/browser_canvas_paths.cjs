const fs=require('fs'),path=require('path'),{createRequire}=require('module');
const root=path.resolve(__dirname,'..'),build=createRequire(root+'/env/web-client/package.json');
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[root+'/browser-client/shared/canvas.js'],bundle:true,write:false,format:'iife',globalName:'Drawing'});
 const browser=await (process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require)('playwright').chromium.launch({executablePath:process.env.PUI_CHROME||'/usr/bin/google-chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1000,height:750}});
  await page.setContent('<canvas id="plot"></canvas>');await page.addScriptTag({content:bundle.outputFiles[0].text});
  const result=await page.evaluate(()=>{
   const canvas=document.getElementById('plot');
   const rect=(x,y,w,h)=>[['M',x,y],['L',x+w,y],['L',x+w,y+h],['L',x,y+h],['Z']];
   const f={width:200,height:150,dpr:1,background:'#ffffff',commands:[
    ['vector',[...rect(0,0,100,100),...rect(25,25,50,50)],'evenodd','#ff00007f',null,1],
    ['push'],['clipRect',110,10,20,20],['vector',rect(100,0,80,60),'nonzero','#000000',null,1],
    ['push'],['clipPath',rect(120,0,20,50),'nonzero'],['vector',rect(100,0,80,60),'nonzero','#0000ff',null,1],['pop'],['pop'],
    ['vector',rect(150,70,10,10),'nonzero','#00ff00',null,1],
    ['rgba',1,2,'/wAA/wAA//8=',110,100,20,40,0,0,null,null,1]]};
   Drawing.drawFrame(canvas,f,{color:'#000',fontSize:'12px',fontWeight:'400',fontFamily:'sans-serif'});
   const ctx=canvas.getContext('2d'),pixel=(x,y)=>Array.from(ctx.getImageData(x,y,1,1).data);
   return [pixel(10,10),pixel(50,50),pixel(105,20),pixel(115,20),pixel(125,20),pixel(155,75),pixel(115,105),pixel(115,135)];
  });
  const assert=require('node:assert/strict');
  assert.deepEqual(result,[[255,128,128,255],[255,255,255,255],[255,255,255,255],[0,0,0,255],[0,0,255,255],[0,255,0,255],[255,0,0,255],[0,0,255,255]]);
  if(process.env.PUI_MPL_FRAME){
   const frame=JSON.parse(fs.readFileSync(process.env.PUI_MPL_FRAME,'utf8'));
   await page.evaluate(f=>Drawing.drawFrame(document.getElementById('plot'),f,{color:'#000',fontSize:'12px',fontWeight:'400',fontFamily:'sans-serif'}),frame);
   await page.screenshot({path:'/tmp/pui-matplotlib-browser.png'});
  }
  console.log('Path, compound fill, alpha, nested native clipping, state restore and RGBA orientation passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
