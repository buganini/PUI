const fs=require('fs');const {createRequire}=require('module');
const path=require('path');const root=path.resolve(__dirname,'..');const build=createRequire(root+'/env/web-client/package.json');
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[root+'/browser-client/shared/dom.js'],bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await (process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require)('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true});
 try{
 const page=await browser.newPage();await page.setContent('<main id="host" style="display:flex;width:100%;height:100%"></main>');
 await page.addStyleTag({content:fs.readFileSync(root+'/browser-client/shared/client.css','utf8')});await page.addScriptTag({content:bundle.outputFiles[0].text});
 const rows=[];
 for(const axis of ['HBox','VBox'])for(const [name,params,pair] of [['auto',{},false],['width',{width:160},false],['height',{height:100},false],['both',{width:160,height:100},false],['weight0',{weight:0},false],['weight1',{weight:1},false],['ratio',{weight:1},true],['minimum',{minWidth:160,minHeight:100},false],['desired-min',{width:120,height:80,minWidth:160,minHeight:100},false],['restore',{},false]]){
 for(const target of [[640,420],[880,560]]){
 await page.setViewportSize({width:target[0],height:target[1]});
 const measured=await page.evaluate(async({axis,params,pair})=>{
 const n=(id,type,layout={},children=[])=>({id,type,layout,children,props:{},style:{},bindings:{},events:{}});
 if(!window.renderer)window.renderer=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
 const r=window.renderer;const children=[n('canvas','Canvas',params)];if(pair)children.push(n('peer','Canvas',{weight:3}));
 r.apply({mode:'snapshot',base_rev:null,rev:window.rev=(window.rev||0)+1,processed_seq:0,roots:[n('window','Window',{},[n('box',axis,{padding:[0,0,0,0]},children)])],bindings:[],canvases:[]});
 await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
 const size=id=>{const b=r.elements.get(id).getBoundingClientRect();return [b.width,b.height]};
 return {box:size('box'),canvas:size('canvas'),peer:pair?size('peer'):null};
 },{axis,params,pair});rows.push({axis,case:name,target,...measured});
 }}
 const assert=require('node:assert/strict');
 for(const r of rows){
  const axis=r.axis==='HBox'?0:1;
  if(['auto','weight1','minimum','restore'].includes(r.case))assert.deepEqual(r.canvas,r.box);
  if(r.case==='width')assert.deepEqual(r.canvas,[160,r.box[1]]);
  if(r.case==='height')assert.deepEqual(r.canvas,[r.box[0],100]);
  if(['both','desired-min'].includes(r.case))assert.deepEqual(r.canvas,[160,100]);
  if(r.case==='weight0')assert.equal(r.canvas[axis],0);
  if(r.case==='ratio')assert(Math.abs(r.peer[axis]/r.canvas[axis]-3)<.03);
 }
 console.log('Canvas desired/minimum size, auto/zero/positive weights, ratios and retained resize: '+rows.length+' cases passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
