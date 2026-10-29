// Modal UI for the generic synchronous dialog bridge; all strings are plain text.
export function showMessageDialog(body, reply) {
  if(!['information','warning','critical','confirm','prompt'].includes(body.kind))throw Error('Unknown dialog kind');
  const previous=document.activeElement,dialog=document.createElement('dialog');
  dialog.className='pui-savefile pui-message-dialog';dialog.dataset.kind=body.kind;
  const form=document.createElement('form'),title=document.createElement('h2'),message=document.createElement('p');
  title.textContent=body.title;title.id='pui-message-title';message.textContent=body.message;message.id='pui-message-body';
  dialog.setAttribute('aria-labelledby',title.id);dialog.setAttribute('aria-describedby',message.id);
  form.append(title,message);dialog.append(form);
  let done=false,field;
  const dispose=()=>{if(done)return;done=true;dialog.close();dialog.remove();if(previous?.isConnected)previous.focus();};
  const finish=value=>{if(done)return;dispose();reply(value);};
  const cancel=()=>finish(body.kind==='confirm'?false:null);
  dialog.oncancel=e=>{e.preventDefault();cancel();};dialog.onclose=cancel;
  if(body.kind==='prompt'){
    field=document.createElement('input');field.type='text';field.value=body.default;field.setAttribute('aria-label',body.message||'Input');form.append(field);
  }
  const actions=document.createElement('div');actions.className='pui-savefile-actions';form.append(actions);
  if(['confirm','prompt'].includes(body.kind)){
    const button=document.createElement('button');button.type='button';button.className='pui-Button';button.textContent='Cancel';button.onclick=cancel;actions.append(button);
  }
  const ok=document.createElement('button');ok.type='submit';ok.className='pui-Button';ok.textContent='OK';actions.append(ok);
  form.onsubmit=e=>{e.preventDefault();finish(body.kind==='confirm'?true:field?field.value:null);};
  document.body.append(dialog);dialog.showModal();
  if(field){field.focus();field.select();}
  return dispose;
}
