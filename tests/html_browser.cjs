// HTML fragments use the same retained renderer in Web and Pyodide.
const path=require('node:path');
const fs=require('node:fs');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const build=createRequire(path.join(root,'env/web-client/package.json'));
const modules=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
(async()=>{
 const bundle=await build('esbuild').build({entryPoints:[path.join(root,'browser-client/shared/dom.js')],bundle:true,write:false,format:'iife',globalName:'PUIRenderer'});
 const browser=await modules('playwright').chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',headless:true});
 try {
  const page=await browser.newPage();
  await page.setContent('<main id="host"></main>');
  await page.addStyleTag({content:fs.readFileSync(path.join(root,'browser-client/shared/client.css'),'utf8')});
  await page.addScriptTag({content:bundle.outputFiles[0].text});
  await page.evaluate(()=>{
   const check=(ok,message)=>{if(!ok)throw Error(message);};
   const node=(id,type,props,children=[])=>({id,type,props,children,layout:{},style:{},bindings:{},events:{}});
   const markup='<style>span { color: rgb(12, 34, 56) } #host { display:none }</style><p><b>Bold</b> &amp; <i>italic</i> 中文</p><ul><li>Item</li></ul><table><tr><td>Cell</td></tr></table><span>Styled</span>';
   const html=node('html','Html',{text:markup,selectable:true});
   html.style={color:'#102030',background:'#fff7e6'};
   const literal=node('literal','Label',{text:'<b>literal</b>',selectable:false});
   const r=new PUIRenderer.Renderer(document.getElementById('host'),()=>{});
   let rev=1;
   r.apply({mode:'snapshot',base_rev:null,rev,processed_seq:0,roots:[node('window','Window',{title:'HTML'},[html,literal])],bindings:[],canvases:[]});
   const e=r.elements.get('html'),shadow=e.shadowRoot,bold=shadow.querySelector('b');
   check(bold.textContent==='Bold' && shadow.querySelector('li').textContent==='Item' && shadow.querySelector('td').textContent==='Cell','HTML structure not rendered');
   check(getComputedStyle(bold).fontWeight==='700' && getComputedStyle(shadow.querySelector('i')).fontStyle==='italic','Rich text styles missing');
   check(getComputedStyle(shadow.querySelector('span')).color==='rgb(12, 34, 56)','Fragment CSS not applied');
   check(getComputedStyle(bold).color==='rgb(16, 32, 48)' && getComputedStyle(e).backgroundColor==='rgb(255, 247, 230)','PUI styles not inherited');
   check(getComputedStyle(document.getElementById('host')).display!=='none' && getComputedStyle(r.elements.get('literal')).color!=='rgb(12, 34, 56)','Fragment CSS escaped its scope');
   check(r.elements.get('literal').textContent==='<b>literal</b>' && !r.elements.get('literal').querySelector('b'),'Literal text interpreted as markup');
   check(getComputedStyle(e).userSelect==='text' && e.getBoundingClientRect().height>100,'Selection or expansion missing');
   const patch=(field,set)=>r.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,ops:[{op:'patch_node',node_id:'html',field,set,unset:[]}]});
   patch('style',{color:'#223344'});
   check(shadow.querySelector('b')===bold,'Unchanged markup replaced during style update');
   patch('props',{selectable:false});
   check(shadow.querySelector('b')===bold && getComputedStyle(e).userSelect==='none','Selection toggle rebuilt HTML');
   patch('props',{text:'<h2>Updated</h2><p>New content</p>'});
   check(r.elements.get('html')===e && !shadow.querySelector('b') && shadow.querySelector('h2').textContent==='Updated','Retained HTML update failed');
   patch('props',{text:''});
   check(!shadow.childNodes.length,'Empty HTML did not clear content');
   r.destroy();
  });
  console.log('Browser Html: rich fragments, scoped CSS, style inheritance, retained updates, selection and literal-text isolation passed.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
