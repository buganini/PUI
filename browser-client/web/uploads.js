// Multipart streams File objects; XHR supplies upload progress without buffering
// complete file contents in JavaScript. No binary data uses the WebSocket.
export function uploadFiles(url, headers, files, names, signal, progress=()=>{}) {
  return new Promise((resolve,reject)=>{
    if(signal.aborted){reject(Error('Upload cancelled'));return;}
    const xhr=new XMLHttpRequest(),form=new FormData();
    files.forEach((file,i)=>form.append('files',file,names[i]));
    xhr.open('POST',url);xhr.withCredentials=true;
    for(const [key,value] of Object.entries(headers))xhr.setRequestHeader(key,value);
    const abort=()=>xhr.abort();signal.addEventListener('abort',abort,{once:true});
    xhr.onloadend=()=>signal.removeEventListener('abort',abort);
    xhr.upload.onprogress=e=>progress(e.loaded,e.lengthComputable?e.total:0);
    xhr.onerror=()=>reject(Error('Upload failed'));xhr.onabort=()=>reject(Error('Upload cancelled'));
    xhr.onload=()=>{if(xhr.status<200||xhr.status>=300){reject(Error(xhr.responseText||'Upload failed'));return;}
      try{resolve(JSON.parse(xhr.responseText).upload_id);}catch{reject(Error('Invalid upload response'));}};
    xhr.send(form);
  });
}
