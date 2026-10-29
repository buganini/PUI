const path=require('node:path'),{createRequire}=require('node:module');
const buildRequire=createRequire(path.resolve('env/web-client/package.json'));
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const bundle=await buildRequire('esbuild').build({entryPoints:['browser-client/shared/tree.js'],bundle:true,write:false,format:'iife',globalName:'TreeTest'});
 const browser=await req('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();await page.setContent('<main></main>');await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   const check=(value,message)=>{if(!value)throw Error(message);};
   const p={nodes:[{id:1,parent:0,text:'<b>literal</b>'},{id:2,parent:1,text:'child'},{id:3,parent:0,text:'other'}],expanded:[],selected:null,expandable:true};
   TreeTest.validateTree(p);
   for(const bad of [{...p,nodes:[p.nodes[0],p.nodes[0]]},{...p,expanded:[2]},{...p,nodes:[{id:1,parent:1,text:'cycle'}]}]){
    let rejected=false;try{TreeTest.validateTree(bad);}catch{rejected=true;}check(rejected,'Invalid tree accepted');
   }
   let seq=0;const n={id:'tree',events:{tree:'token'},props:p};
   const r={state:{nodes:new Map([['tree',n]])},rev:1,applying:false,dirty:false,focusedEditor:()=>null,
    actions:(_kind,_body,sent)=>sent(++seq)};
   const trees=new TreeTest.Trees(r),el=document.querySelector('main');trees.add('tree',el);trees.sync(n,0);
   const s=trees.records.get('tree'),row=s.rows.get(1);
   check(!el.querySelector('b'),'Label interpreted as HTML');
   row.lastChild.click();
   check(row.getAttribute('aria-expanded')==='true','Single label click did not expand');
   row.dispatchEvent(new MouseEvent('dblclick',{bubbles:true}));
   check(row.getAttribute('aria-expanded')==='true','Double-click notification toggled again');
   row.dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}));
   check(row.getAttribute('aria-expanded')==='false','Enter did not collapse');
   row.dispatchEvent(new KeyboardEvent('keydown',{key:' ',bubbles:true}));
   check(row.getAttribute('aria-expanded')==='true','Space did not expand');
   row.lastChild.click();
   check(row.getAttribute('aria-expanded')==='false','Single label click did not collapse');
   trees.reset();trees.sync(n,seq);
   seq=0;
   trees.send('tree',1,'expanded');trees.send('tree',1,'collapsed');
   check(row.getAttribute('aria-expanded')==='false','Local collapse lost');
   trees.sync({...n,props:{...p,expanded:[1]}},1);
   check(row.getAttribute('aria-expanded')==='false','Delayed expand reply overwrote newer collapse');
   trees.sync(n,2);check(s.pending.length===0,'Acknowledged actions retained');
   trees.send('tree',3,'selected');trees.focus(s,3);
   const selected=s.rows.get(3);
   trees.sync({...n,props:{...p,nodes:[p.nodes[2],p.nodes[0],p.nodes[1]],selected:3}},3);
   check(s.rows.get(3)===selected && document.activeElement===selected,'Reorder lost node/focus');
   trees.sync({...n,props:{...p,nodes:p.nodes.slice(0,2)}},3);
   check(document.activeElement===row,'Removed focus was not restored');
   trees.send('tree',1,'expanded');trees.reset();trees.sync(n,0);
   check(row.getAttribute('aria-expanded')==='false','Reconnect retained stale local actions');
  });console.log('Tree validation, delayed acknowledgements, literal labels, retained DOM/focus and reconnect passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
