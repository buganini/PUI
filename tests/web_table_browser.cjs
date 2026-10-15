const login=require('./web_login.cjs');
const assert=require('node:assert/strict');
const {createRequire}=require('node:module');
const path=require('node:path');
const req=process.env.PUI_BROWSER_MODULES?createRequire(path.join(process.env.PUI_BROWSER_MODULES,'package.json')):require;
const {chromium}=req('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.PUI_WEB_URL || 'http://127.0.0.1:8868/pui/');await login(page);
  await page.getByRole('button',{name:'Table',exact:true}).click();
  const table=page.locator('.pui-Table');await table.locator('tbody tr').first().waitFor();
  // Choices are native controls immediately, without entering edit mode first.
  assert.equal(await table.locator('select').count(),2);
  const flat=async control=>assert.deepEqual(await control.evaluate(e=>{
    const s=getComputedStyle(e);return [s.outlineStyle,s.borderTopWidth,s.marginTop,s.marginRight,s.marginBottom,s.marginLeft,
      s.paddingTop,s.paddingRight,s.paddingBottom,s.paddingLeft];
  }),['none','0px','0px','0px','0px','0px','0px','0px','0px','0px']);
  const geometry=()=>table.evaluate(e=>[...e.querySelectorAll('table,tr,th,td')].map(cell=>{
    const r=cell.getBoundingClientRect();return [r.x,r.y,r.width,r.height];
  }));
  const choice=table.locator('tbody tr').first().locator('td').nth(3);
  await flat(choice.locator('select'));
  const cell=table.locator('tbody tr').first().locator('td').first();
  const before=await geometry();
  await cell.click();await flat(cell.locator('input'));
  assert.deepEqual(await geometry(),before,'Entering edit mode resized the table');
  await cell.locator('input').fill('A much longer draft that must scroll inside the existing cell');
  assert.deepEqual(await geometry(),before,'Typing resized the table');
  await cell.locator('input').press('Escape');
  assert.deepEqual(await geometry(),before,'Canceling changed the table size');
  const decorated=table.locator('tbody tr').nth(2).locator('td').first();
  await decorated.click();await flat(decorated.locator('input'));
  assert.equal(await decorated.locator('input').getAttribute('placeholder'),'Enter price');
  assert.deepEqual(await geometry(),before,'Decorations or placeholder resized the table');
  await decorated.locator('input').press('Escape');
  await cell.click();
  await cell.locator('input').fill('changed');await cell.locator('input').press('Enter');
  await page.getByText('A1: changed',{exact:true}).first().waitFor();
  await cell.locator('input').waitFor({state:'detached'});
  await cell.click();await cell.locator('input').fill('discard');await cell.locator('input').press('Escape');
  assert.equal(await cell.innerText(),'A1: changed');
  await choice.locator('select').selectOption({value:'3'});
  await page.getByText('Sides: 6',{exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('.pui-Table select')?.disabled===false);
  assert.equal(await choice.locator('select').inputValue(),'3');
  assert.equal(await choice.locator('select').evaluate(e=>e===document.activeElement),true);
  await flat(choice.locator('select'));
  await choice.locator('select').press('ArrowUp');
  await page.getByText('Sides: 5',{exact:true}).waitFor();
  const direction=table.locator('tbody tr').nth(1).locator('select');
  await direction.selectOption({label:'Counterclockwise'});
  await page.getByText('Direction: CCW',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Table(Adapter)',exact:true}).click();
  await page.locator('.pui-Table').nth(1).waitFor();
  const number=page.locator('.pui-Table').first().locator('td').first();
  await number.click();await number.locator('input').fill('bad');await number.locator('input').press('Enter');
  await number.locator('[aria-invalid=true]').waitFor();
  await number.locator('input').fill('91');await number.locator('input').press('Tab');
  await page.waitForFunction(()=>[...document.querySelectorAll('.pui-Table')].every(t=>t.querySelector('td').textContent==='91'));
  await page.reload();await page.getByRole('button',{name:'Resume session',exact:true}).click();
  await page.locator('.pui-Table').nth(1).waitFor();
  assert.equal(await page.locator('.pui-Table').first().locator('td').first().innerText(),'91');
  await page.evaluate(async()=>{
    const {Renderer}=await import(document.querySelector('script[type=module]').src);
    const host=document.createElement('section');document.body.append(host);
    const actions=[];let sequence=10;
    const r=new Renderer(host,(type,body,done)=>{actions.push(body.data);done?.(sequence++);});
    const check=(value,message)=>{if(!value)throw Error(message);};
    const cell={token:'cell1',text:'One',editor:'choice',value:0,choices:['One','Two'],error:'',prefix:'',suffix:'',placeholder:''};
    const props={rows:[{id:'row1',cells:[cell]}],columns:['Choice'],column_header:true,row_headers:null,autofit:true};
    const node={id:'table',type:'Table',props,children:[],layout:{},style:{},bindings:{},events:{table:'event1'}};
    const root={id:'window',type:'Window',props:{title:'Choice tests'},children:[node],layout:{},style:{},bindings:{},events:{}};
    r.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:1,roots:[root],bindings:[],canvases:[]});
    const update=processed=>r.apply({mode:'patch',base_rev:r.rev,rev:r.rev+1,processed_seq:processed,
      ops:[{op:'patch_node',node_id:'table',field:'props',set:props,unset:[]}]});
    const select=host.querySelector('select');select.focus();
    select.dispatchEvent(new MouseEvent('click',{bubbles:true}));
    check(actions.at(-1).action==='click','Native select lost cell click callback');
    select.value='1';select.dispatchEvent(new Event('change',{bubbles:true}));
    check(actions.at(-1).action==='commit' && actions.at(-1).value===1,'Choice commit must send an index');
    check(select.disabled,'Pending choice was not disabled');
    update(1);
    check(select.value==='1' && select.disabled,'Unrelated update overwrote pending selection');
    cell.error='Rejected';update(sequence-1);
    check(!select.disabled && select.getAttribute('aria-invalid')==='true','Rejected choice cannot be corrected');
    select.value='0';select.dispatchEvent(new Event('change',{bubbles:true}));
    cell.error='';update(sequence-1);
    check(host.querySelector('select')===select && !select.disabled && document.activeElement===select,
      'Acknowledgement replaced select or lost keyboard focus');
    const sent=actions.length;
    cell.token='cell2';cell.choices=['New label','Other'];cell.value=1;update(sequence-1);
    check(select.value==='1' && select.options[1].textContent==='New label','Source update did not replace stale choices');
    check(actions.length===sent,'Rendering emitted a choice edit');
    cell.token='cell3';cell.editor=null;cell.value=null;cell.text='Read only';update(sequence-1);
    check(!host.querySelector('select') && host.querySelector('td').textContent==='Read only','Read-only cell kept an editor');
    r.canvases.destroy();host.remove();

    for(const autofit of [true,false])for(const [text,value,prefix,suffix] of [
      ['Price: $12345.67 USD','12345.67','Price: $',' USD'],
      ['A formatted display value','raw','',''],
      ['Two\nlines','raw','',''],
      ['','','',''],
    ]) {
      const host=document.createElement('section');document.body.append(host);
      const renderer=new Renderer(host,()=>{});
      const data={token:'value',text,value,editor:'text',choices:[],error:'',prefix,suffix,placeholder:'A long placeholder'};
      const node={id:'table',type:'Table',props:{rows:[{id:'row',cells:[data]}],columns:[''],
        column_header:false,row_headers:null,autofit},children:[],layout:{},style:{font_size_pt:18},bindings:{},events:{table:'event'}};
      const root={...node,id:'window',type:'Window',props:{title:'Size tests'},children:[node],events:{}};
      renderer.apply({mode:'snapshot',base_rev:null,rev:1,processed_seq:0,roots:[root],bindings:[],canvases:[]});
      const td=host.querySelector('td'),size=()=>{const r=td.getBoundingClientRect();return [r.width,r.height].join(',');};
      const before=size();renderer.tables.start('table',td);
      check(size()===before,`Editing resized ${JSON.stringify(text)} (autofit=${autofit})`);
      const input=td.querySelector('input');input.value='A very long replacement draft';
      input.dispatchEvent(new Event('input',{bubbles:true}));
      check(size()===before,'Long draft resized cell');
      renderer.tables.finish('table');
      check(size()===before,'Cancel resized cell');
      renderer.canvases.destroy();host.remove();
    }
  });
  assert.deepEqual(errors,[]);
  console.log('Table browser checks passed: permanent flat choices, keyboard selection/focus, padding-free shrinkable inputs, stable cell sizes, edits, cancel, validation, shared adapter, reconnect.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
