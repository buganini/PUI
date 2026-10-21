const login=require('./web_login.cjs');
const assert=require('node:assert/strict'),path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage({deviceScaleFactor:2}),errors=[];page.setDefaultTimeout(10000);
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
  await page.getByRole('button',{name:'Canvas',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.pui-Canvas canvas')?.width===200);
  const bitmap=page.locator('.pui-Canvas canvas');
  const first=await bitmap.evaluate(c=>c.toDataURL());
  await page.getByRole('button',{name:'+',exact:true}).click();
  await page.getByText('Rotate: 30',{exact:true}).waitFor();
  await page.waitForFunction(before=>document.querySelector('.pui-Canvas canvas').toDataURL()!==before,first);
  const sampled=await bitmap.evaluate(c=>[...c.getContext('2d').getImageData(28,28,1,1).data]);
  assert.deepEqual(sampled,[204,204,204,255]);
  await page.getByRole('button',{name:'DrawShapely',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.pui-Canvas canvas')?.width===1000);
  const geometry=await bitmap.evaluate(c=>{
   const ctx=c.getContext('2d');return [[90,90],[200,200],[150,30],[30,50]].map(([x,y])=>[...ctx.getImageData(x*2,y*2,1,1).data]);
  });
  assert.deepEqual(geometry,[[85,85,85,255],[0,0,0,255],[0,255,0,255],[0,255,0,255]]);
  await page.evaluate(async()=>{
   const {Renderer}=await import(document.querySelector('script[type=module]').src);
   const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;display:flex;';document.body.append(host);
   const controls=[],r=new Renderer(host,()=>{},(type,body)=>controls.push({type,body}));
   const check=(v,m)=>{if(!v)throw new Error(m);};
   const tick=()=>new Promise(resolve=>requestAnimationFrame(()=>setTimeout(resolve,0)));
   const node=(id,type,props={},children=[])=>({id,type,props,children,layout:{},style:{},events:{},bindings:{}});
   const canvas=node('canvas','Canvas');canvas.layout={width:100,height:80};
   const root=node('root','Window',{title:'Canvas pixels'},[canvas]);let rev=0;
   const commandFields={
    line:['op','x1','y1','x2','y2','color','width'],
    polyline:['op','points','color','width'],
    cubic:['op','start','control1','control2','end','color','width'],
    polygon:['op','points','fill','stroke','width'],
    rect:['op','x1','y1','x2','y2','fill','stroke','width'],
    ellipse:['op','x','y','rx','ry','fill','stroke','width'],
    text:['op','x','y','text','w','h','size','color','rotate','anchor'],
    path:['op','subpaths','fill_rule','fill','stroke','width'],
    image:['op','resource','transforms','x','y','width','height','src_x','src_y','src_width','src_height','opacity']};
   const wire=c=>commandFields[c?.op]?.map(key=>c[key]??null) ?? c;
   const apply=frames=>r.apply({mode:'snapshot',base_rev:null,rev:++rev,processed_seq:1,roots:[root],bindings:[],canvases:frames.map(f=>({...f,commands:f.commands.map(wire)}))});
   apply([]);await tick();
   let measure=controls.filter(c=>c.type==='measure').at(-1).body;
   check(measure.width===100 && measure.height===80 && measure.dpr===2,'Measured size/DPR mismatch');
   const rectangle={op:'rect',x1:20,y1:20,x2:5,y2:5,fill:'#ff0000',stroke:null,width:1};
   const frame={node_id:'canvas',frame_rev:1,measure_rev:measure.measure_rev,width:100,height:80,dpr:2,
     background:'#ffffff',continue:false,commands:[rectangle,
       {op:'ellipse',x:50,y:20,rx:10,ry:5,fill:'#0000ff',stroke:null,width:1},
       {op:'polygon',points:[[70,10],[90,10],[80,30]],fill:'#00ff00',stroke:null,width:1},
       {op:'polyline',points:[[95,35],[95,55],[95,75]],color:'#ff0000',width:4},
       {op:'cubic',start:[90,35],control1:[90,45],control2:[90,65],end:[90,75],color:'#0000ff',width:4},
       {op:'path',subpaths:[{points:[[5,40],[35,40],[35,70],[5,70]],closed:true},
         {points:[[10,45],[30,45],[30,65],[10,65]],closed:true}],fill_rule:'evenodd',fill:'#00ff00',stroke:null,width:1},
       {op:'text',x:50,y:50,text:'Anchor\ntext',w:20,h:20,size:12,color:'#000000',rotate:0,anchor:'LeftTop'}]};
   apply([frame]);check(!controls.some(c=>c.type==='canvas_ack'),'Canvas ACK happened before apply returned');await tick();
   const e=r.canvases.records.get('canvas').canvas,ctx=e.getContext('2d');
   const pixel=(x,y)=>[...ctx.getImageData(x*2,y*2,1,1).data].join(',');
   check(e.width===200 && e.height===160,'Backing bitmap ignored DPR');
   check(pixel(10,10)==='255,0,0,255','Rectangle endpoint semantics failed');
   check(pixel(50,20)==='0,0,255,255' && pixel(80,15)==='0,255,0,255','Ellipse/polygon fill failed');
   check(pixel(75,60)==='255,255,255,255','Text was not clipped');
   check(pixel(95,50)==='255,0,0,255' && pixel(90,50)==='0,0,255,255','Polyline/cubic array fields failed');
   check(pixel(7,50)==='0,255,0,255' && pixel(20,50)==='255,255,255,255','Compound path lost its polygon hole');
   check(controls.at(-1).body.status==='drawn','Frame was not acknowledged');
   const original=e.toDataURL();apply([frame]);await tick();
   check(e.toDataURL()===original && controls.at(-1).body.status==='unchanged','Replay changed an intact frame');
   const empty={...frame,frame_rev:2,commands:[]};apply([empty]);await tick();
   check(pixel(10,10)==='255,255,255,255','Full frame failed to clear old pixels');
   canvas.layout.width=120;apply([empty]);await tick();await tick();
   measure=controls.filter(c=>c.type==='measure').at(-1).body;
   check(measure.width===120 && e.width===0,'Resize stretched an obsolete bitmap');
   const resized={...frame,frame_rev:3,measure_rev:measure.measure_rev,width:120};apply([resized]);await tick();
   check(e.width===240 && pixel(10,10)==='255,0,0,255','Resize repaint failed');
   r.canvases.records.get('canvas').element.hidden=true;await tick();await tick();
   check(controls.filter(c=>c.type==='measure').at(-1).body.visible===false,'Hidden canvas was not reported');
   r.canvases.records.get('canvas').element.hidden=false;await tick();await tick();
   check(controls.filter(c=>c.type==='measure').at(-1).body.visible===true,'Visible canvas did not request repaint');
   const oldMeasure=controls.filter(c=>c.type==='measure').at(-1).body.measure_rev;
   // Recovery after partial DOM removal must not reuse a measurement revision.
   r.elements.get('canvas').remove();r.forget('canvas');apply([resized]);await tick();
   check(controls.filter(c=>c.type==='measure').at(-1).body.measure_rev>oldMeasure,'Recovery reused an obsolete measure revision');
   const measured=controls.filter(c=>c.type==='measure').at(-1).body;
   const warnings=[],warn=console.warn;
   console.warn=(...args)=>{warnings.push(args);};
   try {
    apply([{...resized,frame_rev:4,measure_rev:measured.measure_rev,commands:[
      {op:'javascript',source:'window.canvasInjected=true'},null,
      {op:'ellipse',x:40,y:40,rx:-1,ry:2},
      {op:'text',x:0,y:0,text:'bad',w:null,h:null,size:12,rotate:45,anchor:'missing'},
      {op:'line',x1:NaN,y1:Infinity,x2:0,y2:0,color:'#000000',width:1},
      {op:'image',resource:'https://example.invalid/forbidden',transforms:[]},
      rectangle]}]);await tick();await tick();
    const canvas=r.canvases.records.get('canvas').canvas;
    check([...canvas.getContext('2d').getImageData(20,20,1,1).data].join(',')==='255,0,0,255',
      'Bad commands prevented the following rectangle from painting');
    check(warnings.length===5 && warnings.every(w=>w[0].includes('skipped command')),'Bad commands were not logged individually');
    check(!window.canvasInjected,'Command data executed as JavaScript');
    check(controls.at(-1).body.status==='failed','Failed image did not release Canvas credit');
    check(r.canvases.images.items.size===0,'Invalid image resource was fetched');
    apply([r.state.canvases.get('canvas')]);await tick();await tick();
    check(controls.at(-1).body.status==='failed','Failed image replay granted continuous paint credit');
    apply([{...resized,frame_rev:5,measure_rev:measured.measure_rev,commands:[rectangle]}]);await tick();
    check(controls.at(-1).body.status==='drawn','Later valid frame did not recover');
   } finally {console.warn=warn;}
   let rejected=false;
   const commands=Array.from({length:300000},()=>({op:'polyline',points:[],color:'#000000',width:1}));
   const large={...resized,frame_rev:6,measure_rev:measured.measure_rev,commands};
   apply([large]);await tick();
   check(r.canvases.records.get('canvas').presented===6 && controls.at(-1).body.status==='drawn',
     '300000-command frame was not drawn and acknowledged');
   const accepted=r.rev;rejected=false;
   try{apply([{...large,frame_rev:7,commands:[...commands,commands[0]]}]);}catch{rejected=true;}
   check(rejected && r.rev===accepted,'300001-command frame was accepted or mutated canonical state');
   // Invalid native style assignments are ignored, not exceptions. They must
   // still fall back to frame defaults instead of inheriting a previous shape.
   const styles=[
    {op:'rect',x1:5,y1:5,x2:20,y2:20,fill:'#ff0000',stroke:null,width:1},
    {op:'rect',x1:25,y1:5,x2:40,y2:20,fill:'invalid-color',stroke:null,width:1},
    {op:'rect',x1:45,y1:5,x2:60,y2:20,fill:'#0000ff',stroke:null,width:1},
    {op:'rect',x1:65,y1:5,x2:80,y2:20,fill:'invalid-color',stroke:null,width:1},
    {op:'line',x1:5,y1:40,x2:30,y2:40,color:'#ff0000',width:8},
    {op:'line',x1:40,y1:40,x2:65,y2:40,color:'invalid-color',width:-2},
    {op:'line',x1:75,y1:40,x2:100,y2:40,color:'invalid-color',width:-2}];
   apply([{...resized,frame_rev:7,measure_rev:measured.measure_rev,commands:styles}]);await tick();
   const expected=document.createElement('canvas');expected.width=240;expected.height=160;
   const reference=expected.getContext('2d');reference.scale(2,2);
   reference.fillStyle='#ffffff';reference.fillRect(0,0,120,80);
   for(const c of styles){
    reference.save();reference.beginPath();reference.lineCap='square';reference.lineJoin='bevel';
    reference.lineWidth=c.width;
    if(c.op==='rect'){reference.rect(c.x1,c.y1,c.x2-c.x1,c.y2-c.y1);reference.fillStyle=c.fill;reference.fill('evenodd');}
    else{reference.moveTo(c.x1,c.y1);reference.lineTo(c.x2,c.y2);reference.strokeStyle=c.color;reference.stroke();}
    reference.restore();
   }
   check(r.canvases.records.get('canvas').canvas.toDataURL()===expected.toDataURL(),
     'Cached geometry styles changed native fallback behavior');
   root.children=[];apply([]);check(r.canvases.records.size===0,'Removed canvas retained observers/bitmap');
   r.destroy();host.remove();
  });
  assert.deepEqual(errors,[]);console.log('Canvas: cookbook drawing/text/Shapely, DPR, measured geometry, polygon holes, pixels, text clipping, immutable replay, resize, visibility, malformed commands, 300000-command boundary and cleanup passed.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
