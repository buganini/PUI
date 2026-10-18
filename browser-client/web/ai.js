// AI lives outside the application root and survives worker renewal via its token.
export function startAI(root, {resumeId, renew}) {
  if (!root.dataset.ai) return;
  const storage = 'pui:ai:' + location.pathname + ':' + root.dataset.resumeOwner;
  let saved;
  try { saved = JSON.parse(sessionStorage.getItem(storage) || '{}'); } catch { saved = {}; }
  let socket, stopped=false, retry;
  const panel=document.createElement('aside');panel.className='pui-ai';
  panel.setAttribute('aria-label','AI development');
  const heading=document.createElement('h2');heading.textContent='AI development';
  const provider=document.createElement('select');provider.setAttribute('aria-label','AI provider');
  const model=document.createElement('input');model.placeholder='Default';model.setAttribute('aria-label','Model');
  const models=document.createElement('datalist');models.id='pui-ai-models';model.setAttribute('list',models.id);
  const effort=document.createElement('select');effort.setAttribute('aria-label','Effort');
  const modelLabel=document.createElement('label');modelLabel.textContent='Model';modelLabel.append(model,models);
  const effortLabel=document.createElement('label');effortLabel.textContent='Effort';effortLabel.append(effort);
  const choices={}, selections={}, effortLevels={};let selectedProvider='';
  const option=(value,label=value)=>{const o=document.createElement('option');o.value=value;o.textContent=label;return o;};
  function updateEfforts(value=effort.value){
    const list=choices[provider.value]||[], selected=list.find(m=>m.model===model.value);
    const levels=selected?[...selected.efforts]:[...(effortLevels[provider.value]||new Set(list.flatMap(m=>m.efforts)))];
    if(!selected && value && !levels.includes(value))levels.push(value);
    effort.replaceChildren(option('','Default'),...levels.map(e=>option(e)));
    effort.value=levels.includes(value)?value:'';
  }
  function saveSelection(){if(selectedProvider)selections[selectedProvider]={model:model.value,effort:effort.value};}
  function selectProvider(){
    saveSelection();selectedProvider=provider.value;
    const selected=selections[selectedProvider]||{};model.value=selected.model||'';
    models.replaceChildren(...(choices[selectedProvider]||[]).map(m=>option(m.model)));
    updateEfforts(selected.effort||'');
  }
  provider.onchange=selectProvider;
  model.oninput=()=>{updateEfforts();saveSelection();};effort.onchange=saveSelection;
  const workspace=document.createElement('small');
  const log=document.createElement('div');log.className='pui-ai-log';log.setAttribute('role','log');
  const approvals=document.createElement('div');
  const error=document.createElement('p');error.setAttribute('role','status');
  const prompt=document.createElement('textarea');prompt.placeholder='Describe a change…';prompt.setAttribute('aria-label','Prompt');
  const send=document.createElement('button');send.textContent='Send';send.type='button';send.disabled=true;
  const cancel=document.createElement('button');cancel.textContent='Cancel';cancel.type='button';cancel.disabled=true;
  panel.append(heading,provider,modelLabel,effortLabel,workspace,log,approvals,error,prompt,send,cancel);
  root.after(panel);document.body.classList.add('pui-with-ai');
  const transmit=data=>{if(socket?.readyState===WebSocket.OPEN)socket.send(JSON.stringify(data));};
  send.onclick=()=>{if(!prompt.value.trim())return;transmit({type:'prompt',provider:provider.value,settings:{model:model.value,effort:effort.value},text:prompt.value,resume_id:resumeId()});prompt.value='';send.disabled=true;};
  cancel.onclick=()=>transmit({type:'cancel'});
  let approvalKey='';
  function display(data) {
    if (data.type==='error') {error.textContent=data.text;return;}
    saved.conversation=data.conversation;
    for(const [name,selection] of Object.entries(data.selections||{}))if(!selections[name])selections[name]={...selection};
    Object.assign(choices,data.models||{});
    Object.assign(effortLevels,data.effort_levels||{});
    const previous=provider.value;
    provider.replaceChildren(...data.providers.map(name=>{const option=document.createElement('option');option.value=option.textContent=name;return option;}));
    if(data.providers.includes(previous))provider.value=previous;
    selectProvider();
    workspace.textContent=data.cwd;
    const atEnd=log.scrollHeight-log.scrollTop-log.clientHeight<30;
    log.replaceChildren(...data.messages.map(message=>{
      const block=document.createElement('pre');block.textContent=(message.provider||message.role)+': '+message.text;return block;
    }));
    if(atEnd)log.scrollTop=log.scrollHeight;
    send.disabled=data.busy;cancel.disabled=!data.busy;provider.disabled=data.busy;
    error.textContent=data.busy?'Working…':'';
    const key=JSON.stringify(data.approvals);
    if(key!==approvalKey){
      approvalKey=key;approvals.replaceChildren();
      for(const approval of data.approvals){
        const block=document.createElement('section'),title=document.createElement('strong'),details=document.createElement('pre');
        title.textContent=approval.title;details.textContent=approval.details;block.append(title,details);
        const answer=document.createElement('textarea');answer.setAttribute('aria-label','Answer');
        if(approval.input)block.append(answer);
        for(const [label,allow] of [['Allow / Send',true],['Deny',false]]){
          const button=document.createElement('button');button.type='button';button.textContent=label;
          button.onclick=()=>transmit({type:'answer',id:approval.id,allow,text:answer.value});block.append(button);
        }
        approvals.append(block);
      }
    }
    const changed=data.renew>(saved.renew||0);
    saved.renew=data.renew;sessionStorage.setItem(storage,JSON.stringify(saved));
    // Only the tab whose current application was edited renews. Other tabs can
    // share a login cookie without losing their application state.
    if(changed && data.resume_id===resumeId())renew(data.resume_id);
  }
  function connect(){
    const url=new URL(root.dataset.ai,location.href);url.protocol=location.protocol==='https:'?'wss:':'ws:';
    socket=new WebSocket(url);
    socket.onopen=()=>transmit({type:'attach',conversation:saved.conversation||null});
    socket.onmessage=event=>{try{display(JSON.parse(event.data));}catch(e){error.textContent=e.message;}};
    socket.onclose=event=>{
      send.disabled=cancel.disabled=true;
      error.textContent=event.code===4001?'Signed out.':'AI connection closed.';
      if(!stopped && ![1008,4001].includes(event.code))retry=setTimeout(connect,2000);
    };
  }
  window.addEventListener('pagehide',()=>{stopped=true;clearTimeout(retry);socket?.close();},{once:true});
  connect();
}
