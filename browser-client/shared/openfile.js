import { icon } from './savefile.js';
// One modal for device files and optional server browsing. Data transfer is injected.
const el=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
export function showOpenFile(body, reply, upload, retained=null) {
  const o=body.options,folder=o.mode==='directory',multi=o.mode==='files';
  const dialog=retained||el('dialog',undefined,'pui-savefile pui-openfile');
  if(!retained){dialog.puiPreviousFocus=document.activeElement;dialog.puiSelection=new Set();}
  const selected=dialog.puiSelection;
  const form=el('form');dialog.replaceChildren(form);dialog.removeAttribute('aria-busy');
  let done=false,disposed=false,transferring=false;const abort=new AbortController();
  const dispose=()=>{if(disposed)return;disposed=true;done=true;abort.abort();dialog.close();dialog.remove();if(dialog.puiPreviousFocus?.isConnected)dialog.puiPreviousFocus.focus();};
  dispose.dialog=dialog;
  const finish=value=>{
    if(disposed)return;
    if(done){if(value===null)dialog.puiCancelRequested=true;return;}
    if(value && ['browse','page'].includes(value.action)){done=true;dialog.setAttribute('aria-busy','true');if(value.action==='browse'&&!multi)selected.clear();}
    else dispose();
    reply(value);
  };
  const action=(action,value)=>finish({action,value});
  const button=(parent,text,fn)=>{const b=el('button',text,'pui-Button');b.type='button';b.onclick=fn;parent.append(b);return b;};
  const heading=el('h2',body.title);heading.id='pui-openfile-title';dialog.setAttribute('aria-labelledby',heading.id);
  const header=el('div',undefined,'pui-openfile-heading');header.append(heading);form.append(header);
  const close=button(header,'',()=>finish(null));close.setAttribute('aria-label','Close');close.append(icon('cancel'));
  const error=el('p',o.error||'','pui-savefile-error');error.setAttribute('role','alert');error.hidden=!o.error;form.append(error);
  const fail=message=>{error.hidden=false;error.textContent=message;};
  const device=el('div',undefined,'pui-openfile-device');form.append(device);
  const picker=el('input');picker.type='file';picker.hidden=true;picker.multiple=multi||folder;
  if(folder)picker.setAttribute('webkitdirectory','');
  const extensions=o.patterns.filter(p=>/^\*\.[a-z0-9._-]+$/i.test(p)).map(p=>p.slice(1));
  if(o.patterns.length && extensions.length===o.patterns.length)picker.accept=extensions.join(',');
  const choose=button(device,folder?'Choose a folder':multi?'Choose files':'Choose a file',()=>{picker.value='';picker.click();});
  choose.prepend(icon(folder?'folder':'upload'));
  const hint=el('p',folder?'Folder drag & drop is not supported.':multi?'or drop files here':'or drop a file here');device.append(hint,picker);
  if(folder && !('webkitdirectory' in document.createElement('input'))){choose.disabled=true;hint.textContent='Folder selection is not supported by this browser.';}
  const progress=el('p');progress.setAttribute('role','status');progress.setAttribute('aria-live','polite');progress.hidden=true;device.append(progress);
  const controls=[];
  async function receive(files){
    if(done||transferring)return;
    if(!files.length){fail(folder?'No files found. Empty folders cannot be imported.':'Choose at least one file.');return;}
    if(!multi&&!folder&&files.length!==1){fail('Choose exactly one file.');return;}
    if(folder && files.some(f=>!f.webkitRelativePath)){fail('Choose a folder using the button. Folder drag & drop is not supported.');return;}
    const l=o.limits;
    if(files.length>l.max_files || files.some(f=>f.size>l.max_file_bytes) || files.reduce((n,f)=>n+f.size,0)>l.max_session_bytes){fail('Upload limit exceeded.');return;}
    const disabled=controls.map(b=>b.disabled);
    transferring=true;error.hidden=true;progress.hidden=false;choose.disabled=true;controls.forEach(b=>b.disabled=true);
    progress.textContent='Preparing files…';
    try{
      const key=await upload(files,o,abort.signal,(loaded,total)=>{progress.textContent=`${o.directory===undefined?'Importing':'Uploading'}… ${total?Math.min(100,Math.round(loaded/total*100))+'%':'0%'}`;});
      if(!disposed)action('upload',key);
    }catch(e){if(!disposed){fail(e.message);progress.hidden=true;}}
    finally{transferring=false;if(!disposed){choose.disabled=false;controls.forEach((b,i)=>b.disabled=disabled[i]);update();}}
  }
  picker.onchange=()=>receive(Array.from(picker.files));
  device.ondragover=e=>{e.preventDefault();e.stopPropagation();e.dataTransfer.dropEffect=folder?'none':'copy';if(!folder)device.classList.add('drag');};
  device.ondragleave=()=>device.classList.remove('drag');
  device.ondrop=e=>{e.preventDefault();e.stopPropagation();device.classList.remove('drag');
    if(folder||Array.from(e.dataTransfer.items).some(i=>i.webkitGetAsEntry?.()?.isDirectory)){fail('Folder drag & drop is not supported. Use Choose a folder in Open Directory.');return;}
    receive(Array.from(e.dataTransfer.files));};
  // Never let a file dropped outside the device area navigate the page.
  dialog.ondragover=e=>e.preventDefault();dialog.ondrop=e=>{e.preventDefault();fail('Drop files in the device selection area.');};
  const server=o.directory!==undefined;
  if(server){
    form.append(el('p','Browse server','pui-openfile-section'));
    const nav=el('div',undefined,'pui-file-path');form.append(nav);
    const up=button(nav,'Up',()=>action('browse',o.parent));up.disabled=o.parent===null;
    const directory=el('input');directory.type='text';directory.value=o.directory;directory.setAttribute('aria-label','Directory');nav.append(directory);
    const navigate=()=>{if(!transferring&&!done)action('browse',directory.value);};
    const go=button(nav,'Go',navigate);controls.push(up,directory,go);
    directory.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();navigate();}};
    const rows=el('div',undefined,'pui-savefile-entries');rows.setAttribute('aria-label','Files and folders');form.append(rows);
    for(const entry of o.entries){
      const row=button(rows,'',()=>{if(transferring||done)return;if(entry.directory)action('browse',entry.path);else{if(!multi)selected.clear();if(multi&&selected.has(entry.path))selected.delete(entry.path);else selected.add(entry.path);update();}});
      row.dataset.directory=String(entry.directory);row.dataset.path=entry.path;
      if(multi&&!entry.directory){const check=el('span',undefined,'pui-openfile-check');check.setAttribute('aria-hidden','true');row.append(check);}
      row.append(el('span',entry.name),el('span',entry.directory?'Folder':'File','pui-openfile-kind'));controls.push(row);
    }
    if(!o.entries.length)rows.append(el('p',folder?'No subfolders':'No files'));
    if(o.total>200){const pages=el('div',undefined,'pui-savefile-actions');form.append(pages);
      const prev=button(pages,'Previous',()=>action('page',String(o.offset-200)));prev.disabled=o.offset===0;
      pages.append(el('span',`${o.offset+1}–${o.offset+o.entries.length} / ${o.total}`));
      const next=button(pages,'Next',()=>action('page',String(o.offset+200)));next.disabled=o.offset+200>=o.total;controls.push(prev,next);
    }
    if(o.patterns.length)form.append(el('p',o.patterns.join(', ')));
  }
  const actions=el('div',undefined,'pui-savefile-actions');form.append(actions);const summary=el('span',undefined,'pui-openfile-selection');actions.append(summary);
  button(actions,'Cancel',()=>finish(null));
  const confirm=server?button(actions,folder?'Open this folder':'Open',()=>action('open',folder?o.directory:multi?[...selected]:[...selected][0])):null;
  if(confirm)controls.push(confirm);
  function update(){
    if(confirm)confirm.disabled=transferring||(!folder&&!selected.size);
    summary.textContent=server?(folder?'':multi?`${selected.size} files selected`:[...selected][0]?.split('/').pop()||'No file selected'):'';
    form.querySelectorAll('[data-path]').forEach(row=>{if(row.dataset.directory==='false'){const on=selected.has(row.dataset.path);row.setAttribute('aria-pressed',String(on));const check=row.querySelector('.pui-openfile-check');if(check)check.textContent=on?'✓':'';}});
  }
  dialog.oncancel=e=>{e.preventDefault();finish(null);};dialog.onclose=()=>finish(null);form.onsubmit=e=>e.preventDefault();
  update();if(!retained){document.body.append(dialog);dialog.showModal();}else choose.focus();
  if(dialog.puiCancelRequested){dialog.puiCancelRequested=false;finish(null);}
  return dispose;
}
