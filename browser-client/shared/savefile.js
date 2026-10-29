// Imperative SaveFile UI. Each step returns through the existing dialog transport;
// filesystem traversal and destination validation belong to the Python worker.
const paths = {
  upload: ['M12 16V3m-5 5 5-5 5 5', 'M4 16v5h16v-5'],
  folder: ['M3 7V5h6l2 2h10v13H3Z'],
  download: ['M12 3v12m-5-5 5 5 5-5', 'M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5'],
  save: ['M5 3h12l4 4v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z', 'M7 3v6h10V3M7 21v-8h10v8M14 5v2'],
  cancel: ['m6 6 12 12M18 6 6 18'],
};
function element(tag, text, className) {
  const node=document.createElement(tag);
  if(text!==undefined)node.textContent=text;
  if(className)node.className=className;
  return node;
}
export function icon(kind) {
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  for(const [key,value] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.75','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true'}))svg.setAttribute(key,value);
  for(const d of paths[kind]){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}
  return svg;
}
export function showSaveFile(body, reply, retained=null) {
  const o=body.options;
  const dialog=retained||element('dialog',undefined,'pui-savefile');
  if(!retained)dialog.puiPreviousFocus=document.activeElement;
  const previous=dialog.puiPreviousFocus;
  const form=element('form');dialog.replaceChildren(form);
  dialog.removeAttribute('aria-busy');
  const heading=element('h2',body.title);heading.id='pui-savefile-title';dialog.setAttribute('aria-labelledby',heading.id);form.append(heading);
  let finished=false, disposed=false, name;
  const dispose=()=>{if(disposed)return;disposed=true;finished=true;dialog.close();dialog.remove();if(previous?.isConnected)previous.focus();};
  dispose.dialog=dialog;
  const finish=value=>{
    if(disposed)return;
    if(finished){if(value===null)dialog.puiCancelRequested=true;return;}
    if(value && ['browse','page'].includes(value.action)){
      finished=true;dialog.setAttribute('aria-busy','true');
    }else dispose();
    reply(value);
  };
  const result=(action,value='')=>finish(
    name && ['browse','page'].includes(action)?{action,value,name:name.value}:{action,value});
  const button=(parent,label,click)=>{const b=element('button',label,'pui-Button');b.type='button';b.onclick=click;parent.append(b);return b;};
  const input=(label,value)=>{const wrapper=element('label',label);const field=element('input');field.type='text';field.value=value||'';wrapper.append(field);form.append(wrapper);return field;};
  dialog.oncancel=e=>{e.preventDefault();finish(null);};
  dialog.onclose=()=>finish(null);
  form.onsubmit=e=>e.preventDefault();
  if(o.stage==='choice') {
    const choices=element('div',undefined,'pui-savefile-choices');form.append(choices);
    for(const [kind,label] of [['download','Download'],['save','Save to Server'],['cancel','Cancel']]){
      const b=button(choices,'',()=>kind==='cancel'?finish(null):result(kind));b.append(icon(kind),element('span',label));
    }
  } else if(o.stage==='overwrite') {
    form.append(element('p',`Replace the existing file?\n${o.path}`));
    const actions=element('div',undefined,'pui-savefile-actions');form.append(actions);
    button(actions,'Cancel',()=>finish(null));button(actions,'Replace',()=>result('confirm'));
  } else {
    if(o.error){const error=element('p',o.error,'pui-savefile-error');error.setAttribute('role','alert');form.append(error);}
    if(o.stage==='browse') {
      const directory=element('input');directory.type='text';directory.value=o.directory;directory.setAttribute('aria-label','Directory');
      const navigation=element('div',undefined,'pui-file-path');form.append(navigation);
      button(navigation,'Up',()=>result('browse',o.parent)).disabled=o.parent===null;
      navigation.append(directory);
      button(navigation,'Go',()=>result('browse',directory.value));
      directory.onkeydown=e=>{if(e.key==='Enter'){e.preventDefault();result('browse',directory.value);}};
      const entries=element('div',undefined,'pui-savefile-entries');entries.setAttribute('aria-label','Files and folders');form.append(entries);
      for(const entry of o.entries){
        const row=button(entries,entry.name,()=>{
          if(entry.directory)result('browse',entry.path);
          else {name.value=entry.name;name.focus();}
        });
        row.dataset.directory=String(entry.directory);
      }
      if(!o.entries.length)entries.append(element('p','No files'));
      if(o.total>200){
        const pages=element('div',undefined,'pui-savefile-actions');form.append(pages);
        button(pages,'Previous',()=>result('page',String(o.offset-200))).disabled=o.offset===0;
        pages.append(element('span',`${o.offset+1}–${o.offset+o.entries.length} / ${o.total}`));
        button(pages,'Next',()=>result('page',String(o.offset+200))).disabled=o.offset+200>=o.total;
      }
      if(o.filter)form.append(element('p',o.filter));
    }
    name=input('File name',o.name);name.required=true;name.autocomplete='off';
    const actions=element('div',undefined,'pui-savefile-actions');form.append(actions);
    button(actions,'Cancel',()=>finish(null));
    const confirm=button(actions,o.stage==='name'?'Download':'Save',()=>{});confirm.type='submit';
    form.onsubmit=e=>{e.preventDefault();if(form.reportValidity())result('confirm',name.value);};
  }
  if(!retained){document.body.append(dialog);dialog.showModal();}
  else form.querySelector('input,button')?.focus();
  if(dialog.puiCancelRequested){dialog.puiCancelRequested=false;finish(null);}
  return dispose;
}
