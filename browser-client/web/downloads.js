// Session-owned download shelf. Poll metadata, never the file body.
export class Downloads {
  constructor(endpoint) {
    this.endpoint=endpoint;this.generation=0;
  }
  start(session) {
    this.stop();
    if(!this.endpoint)return;
    const generation=this.generation, key='pui:downloads-dismissed:'+session;
    let dismissed;
    try{dismissed=new Set(JSON.parse(sessionStorage.getItem(key)||'[]'));}catch{dismissed=new Set();}
    const shelf=document.createElement('aside');shelf.className='pui-downloads';
    shelf.setAttribute('aria-label','Downloads');
    document.body.append(shelf);this.shelf=shelf;
    const cards=new Map();
    const poll=async()=>{
      this.abort=new AbortController();
      try{
        const response=await fetch(this.endpoint,{credentials:'same-origin',cache:'no-store',
          headers:{'X-PUI-Session':session},signal:this.abort.signal});
        if(generation!==this.generation)return;
        if(!response.ok){if([401,403,404].includes(response.status)){this.stop();return;}throw Error('Download metadata unavailable');}
        const entries=await response.json();
        if(generation!==this.generation)return;
        const ids=new Set(entries.map(e=>e.id));
        for(const [id,card] of cards)if(!ids.has(id)){card.container.remove();cards.delete(id);}
        for(const entry of entries){
          if(dismissed.has(entry.id))continue;
          let card=cards.get(entry.id);
          if(!card){
            const container=document.createElement('section');container.className='pui-download-card';
            const title=document.createElement('strong');title.textContent=entry.name;
            const close=document.createElement('button');close.type='button';close.textContent='×';close.className='pui-download-close';
            close.setAttribute('aria-label','Dismiss '+entry.name);
            close.onclick=()=>{dismissed.add(entry.id);try{sessionStorage.setItem(key,JSON.stringify([...dismissed]));}catch{}container.remove();cards.delete(entry.id);};
            const time=document.createElement('time');const created=new Date(entry.created*1000);
            time.dateTime=created.toISOString();time.textContent='Created '+created.toLocaleString();
            const size=document.createElement('span');size.className='pui-download-size';
            const link=document.createElement('a');link.textContent='Download';link.download=entry.name;
            link.href=this.endpoint.replace(/\/$/,'')+'/'+encodeURIComponent(entry.id);
            container.append(title,close,time,size,link);shelf.prepend(container);
            card={container,size,link};cards.set(entry.id,card);
          }
          card.size.textContent=entry.size===null?'Waiting for file…':formatSize(entry.size);
          card.link.hidden=entry.size===null;
        }
      }catch(error){
        if(error.name!=='AbortError' && generation===this.generation){
          for(const card of cards.values()){card.size.textContent='Size unavailable · retrying…';}
        }
      }finally{
        if(generation===this.generation)this.timer=setTimeout(poll,1000);
      }
    };
    poll();
  }
  stop() {
    ++this.generation;clearTimeout(this.timer);this.abort?.abort();this.shelf?.remove();this.shelf=null;
  }
}
function formatSize(bytes) {
  const exact=new Intl.NumberFormat().format(bytes)+' bytes';
  if(bytes<1024)return exact;
  const units=['KiB','MiB','GiB','TiB'];let value=bytes/1024,index=0;
  while(value>=1024 && index<units.length-1){value/=1024;index++;}
  return `${value.toFixed(1)} ${units[index]} (${exact})`;
}
