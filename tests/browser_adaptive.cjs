// Native ResizeObserver measurements shared by Web and Pyodide.
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const build=createRequire(path.join(root,'env/web-client/package.json'));
const modules=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[path.join(root,'browser-client/shared/dom.js')],bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await modules('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  await page.setContent('<main id="host"></main>');
  await page.addStyleTag({content:fs.readFileSync(path.join(root,'browser-client/shared/client.css'),'utf8')});
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   window.measures=[];
   window.renderer=new PUIRenderer.Renderer(document.getElementById('host'),()=>{},(type,body)=>measures.push({type,...body}));
   const node=(id,type,layout={},children=[])=>({id,type,props:type==='Window'?{title:'Adaptive'}:{},children,layout,style:{},bindings:{},events:{}});
   const box=node('box','VBox',{observe_size:true,width:800,height:300,padding:[10,20,10,20]},[node('a','Button'),node('b','Button')]);
   box.props.direction='column';
   renderer.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[node('window','Window',{},[box])],bindings:[],canvases:[]});
  });
  await page.waitForFunction(()=>measures.length>0);
  let first=await page.evaluate(()=>measures.at(-1));
  assert.equal(first.type,'container_size');assert.equal(first.width,760);assert.equal(first.height,280);
  await page.evaluate(()=>{
   const e=renderer.elements.get('box');e.style.width='500px';e.style.minWidth='500px';
  });
  await page.waitForFunction(()=>measures.at(-1)?.width===460);
  const retained=await page.evaluate(()=>{
   const a=renderer.elements.get('a'), b=renderer.elements.get('b');a.focus();
   let rev=1;
   for(const direction of ['row','column','row','column']) {
    renderer.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,ops:[
     {op:'patch_node',node_id:'box',field:'props',set:{direction},unset:[]}]});
    if(renderer.elements.get('a')!==a || document.activeElement!==a) return false;
    const ar=a.getBoundingClientRect(),br=b.getBoundingClientRect();
    if(direction==='row' ? br.left<=ar.left : br.top<=ar.top)return false;
   }
   return true;
  });
  assert.equal(retained,true);
  await page.evaluate(()=>renderer.destroy());
  assert.equal(await page.evaluate(()=>renderer.sizes.size),0);
  const reversed=await page.evaluate(()=>{
   const check=(ok,message)=>{if(!ok)throw new Error(message);};
   const node=(id,type,props={},children=[])=>({id,type,props,children,layout:{},style:{},bindings:{},events:{}});
   for(const type of ['HBox','VBox']) {
    const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
    const children=['a','b','c'].map(id=>node(id,'TextField',{text:id,placeholder:''}));
    const bindings=children.map(child=>{
     const ref={object_id:'123',kind:'attr',key:child.id};
     child.layout={width:80,height:30};
     child.bindings.model={ref,token:'a-'+child.id,slot_token:'s-'+child.id,writable:true};
     return {ref,token:'s-'+child.id,value_rev:1,value:child.id};
    });
    const box=node('box',type,{},children);box.layout={width:500,height:240};
    r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,
             roots:[node('window','Window',{title:'Inverse'},[box])],bindings,canvases:[]});
    const elements=children.map(child=>r.elements.get(child.id)), input=elements[1];
    input.focus();input.value='local draft';
    input.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText'}));
    input.setSelectionRange(1,5);
    let rev=1;
    for(const direction of (type==='HBox'?['row']:['column','row','column'])) {
     for(const inverse of [true,false,true,false]) {
      const set=type==='HBox'?{inverse}:{direction,inverse};
      r.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,
               ops:[{op:'patch_node',node_id:'box',field:'props',set,unset:[]}]});
      check(elements.every((e,i)=>r.elements.get(children[i].id)===e),'Replaced editor');
      check([...r.elements.get('box').children].every((e,i)=>e===elements[i]),'Changed DOM order');
      check(document.activeElement===input && input.value==='local draft' &&
            input.selectionStart===1 && input.selectionEnd===5,'Lost draft/focus/selection');
      const a=elements[0].getBoundingClientRect(),c=elements[2].getBoundingClientRect();
      check((direction==='row'?a.left>c.left:a.top>c.top)===inverse,'Wrong visual order');
     }
    }
    r.destroy();
   }
   return true;
  });
  assert.equal(reversed,true);
  console.log('Container size, resize, reverse flow, retained draft/focus/selection and cleanup pass.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
