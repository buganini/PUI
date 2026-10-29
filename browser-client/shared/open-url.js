// URL commands run on the user's browser, not the Python server.
const prompts=new Set();
export function dismissOpenURLs(){for(const close of [...prompts])close();}
export function openURL(url){
  if(typeof url!=='string'||!url||url.length>8192||url!==url.trim()||/[\x00-\x1f\x7f]/.test(url))throw Error('Invalid URL');
  const parsed=new URL(url);
  if(!['http:','https:','mailto:'].includes(parsed.protocol)||(parsed.protocol==='mailto:'&&!parsed.pathname))throw Error('Unsupported URL');
  const tab=window.open('about:blank','_blank');
  if(tab){
    // Sever the opener before navigating; noopener in window.open itself can
    // return null even on success, making popup-block detection unreliable.
    tab.opener=null;
    tab.location.replace(url);
    return;
  }
  // Server/worker callbacks may arrive after transient user activation expires.
  // An actual link click gives the user a reliable way past popup blocking.
  const dialog=document.createElement('dialog'),title=document.createElement('h2');
  dialog.className='pui-savefile pui-message-dialog';
  dialog.setAttribute('aria-label','Open link');title.textContent='Open link';
  const link=document.createElement('a');link.textContent=url;link.href=url;
  link.target='_blank';link.rel='noopener noreferrer';link.style.overflowWrap='anywhere';
  const actions=document.createElement('div');actions.className='pui-savefile-actions';
  const cancel=document.createElement('button');cancel.className='pui-Button';cancel.textContent='Cancel';
  const close=()=>{prompts.delete(close);dialog.remove();};
  prompts.add(close);cancel.onclick=close;dialog.onclose=close;
  dialog.oncancel=e=>{e.preventDefault();close();};
  link.onclick=()=>setTimeout(close,0);
  actions.append(cancel);dialog.append(title,link,actions);document.body.append(dialog);dialog.showModal();
}
