// Parent-axis expansion, sibling priorities and retained layout changes in Chrome.
const assert=require('node:assert/strict');
const path=require('node:path');
const {createRequire}=require('node:module');
const requireBrowser=process.env.PUI_BROWSER_MODULES
 ? createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')) : require;
const {chromium}=requireBrowser('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.PUI_CHROME || '/usr/bin/google-chrome',
  headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');
  await page.getByText('Row 1',{exact:true}).waitFor();
  for(const viewport of [{width:1440,height:900},{width:390,height:700}]) {
   await page.setViewportSize(viewport);
   await page.evaluate(async()=>{
    const {Renderer}=await import(document.querySelector('script[type=module]').src);
    const host=document.createElement('div');host.style.cssText='position:fixed;inset:0;display:flex;background:white';
    document.body.append(host);
    const r=new Renderer(host,()=>{}),check=(v,m)=>{if(!v)throw new Error(m);};
    const n=(id,type,children=[],layout={},props={})=>({id,type,props,children,layout,style:{},bindings:{},events:{}});
    const label=id=>n(id,'Label',[],{},{text:'Content',selectable:false});
    const root=n('root','Window',[],{},{title:'Sizing'});
    let rev=0;
    const render=()=>r.apply({mode:'snapshot',base_rev:null,rev:++rev,processed_seq:0,roots:[root],bindings:[],canvases:[]});
    const patch=ops=>r.apply({mode:'patch',base_rev:rev,rev:++rev,processed_seq:0,ops});
    const bounds=id=>r.elements.get(id).getBoundingClientRect();
    for(const type of ['HBox','VBox']) {
     const main=type==='HBox'?'width':'height',cross=type==='HBox'?'height':'width';
     const box=n('box',type,[],{weight:1});root.children=[box];
     // On its own axis a box outranks a perpendicular box; neither inherits
     // the priority of a nested weighted child.
     const along=n('along',type,[label('along-label')]);
     const across=n('across',type==='HBox'?'VBox':'HBox',[label('across-label')]);
     across.children[0].layout.weight=10;box.children=[along,across];render();
     check(bounds('along')[main]>bounds('box')[main]*.65,type+' lost axis priority');
     check(bounds('across')[main]<bounds('box')[main]*.3,'Nested weight escaped its container');
     // A cross-axis Canvas dimension leaves its main axis expandable.
     const canvas=n('canvas','Canvas',[],{[cross]:70});box.children=[along,canvas];render();
     check(bounds('canvas')[cross]===70,'Canvas cross dimension changed');
     check(bounds('canvas')[main]>bounds('box')[main]*.65,type+' Canvas lost main-axis expansion');
     check(bounds('along')[main]<bounds('box')[main]*.3,'Container competed with shrinkable Canvas');
     canvas.layout={[main]:75};render();
     check(bounds('canvas')[main]===75,'Canvas explicit main dimension grew');
     check(bounds('canvas')[cross]===bounds('box')[cross],'Canvas lost cross-axis expansion');
     const spacer=n('space','Spacer',[],{weight:1});box.children=[along,spacer];render();
     check(bounds('space')[main]>bounds('box')[main]*.65,type+' Spacer failed to take free space');
     check(bounds('along')[main]<bounds('box')[main]*.3,'Container competed with Spacer');
     // A patch on one sibling must also change the untouched sibling's policy.
     const untouched=r.elements.get('along');
     patch([{op:'patch_node',node_id:'space',field:'layout',set:{weight:0},unset:[]}]);
     check(r.elements.get('along')===untouched,'Sizing patch replaced its sibling');
     check(bounds('along')[main]>bounds('box')[main]*.9,'Zero weight did not release free space');
     // Explicit weights divide the main axis, preserving compact cross sizes.
     const first=label('first'),second=label('second');first.layout.weight=1;second.layout.weight=3;
     box.children=[first,second];render();
     check(Math.abs(bounds('second')[main]/bounds('first')[main]-3)<.02,'Weights lost their ratio');
     check(bounds('first')[cross]<bounds('box')[cross]*.4,'Weight expanded the wrong axis');
     patch([{op:'patch_node',node_id:'first',field:'layout',set:{weight:0},unset:[]}]);
     check(bounds('first')[main]>10,'Zero weight collapsed preferred content');
     check(bounds('first')[main]<bounds('box')[main]*.3,'Zero weight still expanded');
     patch([{op:'patch_node',node_id:'first',field:'layout',set:{weight:1},unset:[]}]);
     check(Math.abs(bounds('second')[main]/bounds('first')[main]-3)<.02,'Restored weight did not resize');
    }
    // Reparent without a property update, including leaving flex for CSS Grid.
    const moving=label('moving');moving.layout.weight=1;
    const row=n('row','HBox',[moving],{weight:1}),column=n('column','VBox',[],{weight:1});
    root.children=[row,column];render();const retained=r.elements.get('moving');
    check(bounds('moving').width===bounds('row').width && bounds('moving').height<50,'Row did not apply X weight');
    patch([{op:'place_node',node_id:'moving',parent_id:'column',before_id:null}]);
    check(r.elements.get('moving')===retained,'Reparent replaced the element');
    check(bounds('moving').height===bounds('column').height && bounds('moving').width<100,'Column retained X sizing');
    const grid=n('grid','Grid',[],{weight:1});
    const gridRecord={...grid,children:[]};
    patch([{op:'create_node',node:gridRecord},{op:'place_node',node_id:'grid',parent_id:'root',before_id:null},
     {op:'patch_node',node_id:'moving',field:'layout',set:{row:0,column:0},unset:[]},
     {op:'place_node',node_id:'moving',parent_id:'grid',before_id:null}]);
    check(retained.style.flex==='' && retained.style.alignSelf==='','Grid retained old linear sizing');
    // Inactive pages cannot consume space or outrank the selected page.
    const active=n('active','VBox',[label('active-label')]);
    const inactive=n('inactive','VBox',[label('inactive-label')],{weight:10});
    root.children=[n('views','Views',[active,inactive],{},{selected:'active'})];render();
    check(bounds('active').height===bounds('views').height,'Hidden page competed for free space');
    check(bounds('inactive').height===0,'Inactive page was displayed');
    r.destroy();host.remove();
   });
  }
  assert.deepEqual(errors,[]);
  console.log('HBox/VBox axes, priorities, nested weights, Spacer, Canvas single-axis sizing, weight zero/ratios/patches, retained reparenting and hidden pages passed at desktop/mobile sizes.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
