// Display lists are data only. Drawing/presentation credit is independent of DOM ACKs.
import { Images } from './images.js';
const fail=message=>{throw new Error(message);};
const fields=(v,names)=>v && Object.getPrototypeOf(v)===Object.prototype &&
  Object.keys(v).sort().join(',')===names.split(' ').sort().join(',');
const num=(v,min=-1e9)=>typeof v==='number' && Number.isFinite(v) && v>=min && v<=1e9;
const integer=v=>Number.isSafeInteger(v) && v>0;
const color=v=>v===null || (typeof v==='string' && /^#(?:[0-9a-f]{6}|[0-9a-f]{8})$/i.test(v));
const anchors={LeftTop:[0,0],LeftCenter:[0,.5],LeftBottom:[0,1],CenterTop:[.5,0],
  Center:[.5,.5],CenterBottom:[.5,1],RightTop:[1,0],RightCenter:[1,.5],RightBottom:[1,1]};
export const canvasEvents=['click','dblclick','mousedown','mouseup','mousemove','mouseenter','mouseleave','wheel','keydown','keyup','blur'];
const modifiers=e=>(e.shiftKey?1:0)|(e.ctrlKey?2:0)|(e.altKey?4:0)|(e.metaKey?8:0);
const button=e=>[1,4,2,8,16][e.button] || 0;
export function validateFrame(f) {
  if(!fields(f,'node_id frame_rev measure_rev width height dpr background continue commands') ||
    typeof f.node_id!=='string' || !f.node_id || !integer(f.frame_rev) || !integer(f.measure_rev) ||
    !num(f.width,0) || !num(f.height,0) || f.width===0 || f.height===0 || f.width>16384 || f.height>16384 ||
    !num(f.dpr,0) || f.dpr===0 || f.dpr>8 || Math.ceil(f.width*f.dpr)*Math.ceil(f.height*f.dpr)>16777216 ||
    !color(f.background) || typeof f.continue!=='boolean' || !Array.isArray(f.commands) || f.commands.length>300000)
    fail('Invalid Canvas frame');
}

export function patchFrame(before, op) {
  if(!fields(op,'op base_frame_rev start delete_count frame'))fail('Invalid Canvas patch');
  const f=op.frame;
  validateFrame(f);
  if(!before || !integer(op.base_frame_rev) || before.frame_rev!==op.base_frame_rev ||
    f.frame_rev<=before.frame_rev || ['node_id','measure_rev','width','height','dpr'].some(k=>f[k]!==before[k]))
    fail('Canvas base mismatch');
  if(!Number.isSafeInteger(op.start) || op.start<0 || op.start>before.commands.length ||
    !Number.isSafeInteger(op.delete_count) || op.delete_count<0 ||
    op.delete_count>before.commands.length-op.start ||
    before.commands.length-op.delete_count+f.commands.length>300000)fail('Invalid Canvas splice');
  // Own the new payload once. Retained commands are read-only; never splice the
  // previous frame, which may still be drawing or needed after a failed render.
  const owned=structuredClone(f);
  owned.commands=before.commands.slice(0,op.start).concat(owned.commands,
    before.commands.slice(op.start+op.delete_count));
  return owned;
}

function text(ctx,c,style) {
  const [,x,y,value,w,h,fontSize,color,rotate,anchorName]=c;
  const size=fontSize===null?parseFloat(style.fontSize):fontSize*96/72;
  if(size<=0)return;
  ctx.font=`${style.fontWeight} ${size}px ${style.fontFamily}`;
  ctx.textBaseline='alphabetic';ctx.textAlign='left';
  const lines=value.split('\n'),metrics=ctx.measureText('Mg');
  const ascent=metrics.fontBoundingBoxAscent || metrics.actualBoundingBoxAscent || size*.8;
  const descent=metrics.fontBoundingBoxDescent || metrics.actualBoundingBoxDescent || size*.2;
  const height=(ascent+descent)*lines.length,width=lines.reduce((w,line)=>Math.max(w,ctx.measureText(line).width),0);
  const anchor=anchors[anchorName];ctx.translate(x,y);ctx.rotate(rotate*Math.PI/180);
  ctx.translate(-anchor[0]*width,-anchor[1]*height);
  if(w!==null || h!==null){ctx.beginPath();ctx.rect(0,0,w??width,h??height);ctx.clip();}
  ctx.fillStyle=color || style.color;
  lines.forEach((line,i)=>ctx.fillText(line,0,ascent+i*(ascent+descent)));
}

function vectorPath(commands) {
  if(!Array.isArray(commands) || commands.length>20000)fail('Invalid path');
  const path=new Path2D();let started=false;
  for(const c of commands){
    const count={M:2,L:2,Q:4,C:6,Z:0}[c?.[0]];
    if(count===undefined || c.length!==count+1 || !c.slice(1).every(v=>num(v)))fail('Invalid path command');
    if(c[0]==='M')started=true;else if(!started)fail('Path must start with MoveTo');
    path[{M:'moveTo',L:'lineTo',Q:'quadraticCurveTo',C:'bezierCurveTo',Z:'closePath'}[c[0]]](...c.slice(1));
  }
  return path;
}
function rule(value){if(!['nonzero','evenodd'].includes(value))fail('Invalid fill rule');return value;}

export function drawFrame(canvas,frame,style,images=new Map()) {
  canvas.width=Math.ceil(frame.width*frame.dpr);canvas.height=Math.ceil(frame.height*frame.dpr);
  const ctx=canvas.getContext('2d');if(!ctx)fail('Canvas 2D context is unavailable');
  ctx.setTransform(frame.dpr,0,0,frame.dpr,0,0);
  if(frame.background!==null){ctx.fillStyle=frame.background;ctx.fillRect(0,0,frame.width,frame.height);}
  const defaults={fill:ctx.fillStyle,stroke:ctx.strokeStyle,width:ctx.lineWidth};
  let fill=defaults.fill,strokeStyle=defaults.stroke,lineWidth=defaults.width;
  ctx.lineCap='square';ctx.lineJoin='bevel';
  const stack=[];
  for(const [index,c] of frame.commands.entries()) {
    let scoped=false;
    try {
      if(c[0]==='push'){ctx.save();stack.push([fill,strokeStyle,lineWidth]);continue;}
      if(c[0]==='pop'){
        if(!stack.length)fail('Unmatched Canvas.pop');
        ctx.restore();[fill,strokeStyle,lineWidth]=stack.pop();continue;
      }
      if(c[0]==='clipRect'){
        if(c.length!==5 || !c.slice(1).every(v=>num(v)))fail('Invalid clip rectangle');
        const p=new Path2D();p.rect(c[1],c[2],Math.max(0,c[3]),Math.max(0,c[4]));ctx.clip(p);continue;
      }
      if(c[0]==='clipPath'){ctx.clip(vectorPath(c[1]),rule(c[2]));continue;}
      if(c[0]==='vector'){
        const p=vectorPath(c[1]);const fillRule=rule(c[2]);
        ctx.save();scoped=true;
        if(c[3]!==null){ctx.fillStyle=c[3];ctx.fill(p,fillRule);}
        if(c[4]!==null){ctx.strokeStyle=c[4];ctx.lineWidth=c[5] || 1/frame.dpr;ctx.stroke(p);}
        continue;
      }
      if(c[0]==='rgba'){
        const [,iw,ih,data,x,y,w,h,sx,sy,sw,sh,opacity]=c;
        if(!integer(iw)||!integer(ih)||iw*ih>1048576||typeof data!=='string'||data.length>5592408)fail('Invalid RGBA image');
        const raw=atob(data);if(raw.length!==iw*ih*4)fail('RGBA size mismatch');
        const image=document.createElement('canvas');image.width=iw;image.height=ih;
        const bytes=Uint8ClampedArray.from(raw,c=>c.charCodeAt(0));
        image.getContext('2d').putImageData(new ImageData(bytes,iw,ih),0,0);
        ctx.save();scoped=true;ctx.globalAlpha=opacity;
        ctx.drawImage(image,sx,sy,sw??(iw-sx),sh??(ih-sy),x,y,w??(sw??iw-sx),h??(sh??ih-sy));continue;
      }
      if(c[0]==='text'){
        ctx.save();scoped=true;
        ctx.fillStyle=defaults.fill;
        text(ctx,c,style);continue;
      }
      if(c[0]==='image') {
        ctx.save();scoped=true;
        const img=images.get(c);if(img instanceof Error)throw img;if(!img)fail('Image is not ready');
        const [,,,x,y,width,height,sx,sy,srcWidth,srcHeight,opacity]=c;
        const sw=srcWidth??(img.width-sx),sh=srcHeight??(img.height-sy);
        const dw=width??sw,dh=height??sh;
        if(sw>0 && sh>0 && dw>0 && dh>0){ctx.globalAlpha=opacity;ctx.drawImage(img,sx,sy,sw,sh,x,y,dw,dh);}
        continue;
      }
      ctx.beginPath();
      let stroke, requestedFill, requestedWidth, fillRule='evenodd';
      if(c[0]==='line') {
        const [,x1,y1,x2,y2,color,width]=c;
        ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);stroke=color;requestedWidth=width;
      } else if(c[0]==='polyline') {
        const [,points,color,width]=c;
        points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));stroke=color;requestedWidth=width;
      } else if(c[0]==='polygon') {
        const [,points,fill,color,width]=c;
        points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));ctx.closePath();
        requestedFill=fill;stroke=color;requestedWidth=width;
      } else if(c[0]==='cubic') {
        const [,start,control1,control2,end,color,width]=c;
        ctx.moveTo(...start);ctx.bezierCurveTo(...control1,...control2,...end);stroke=color;requestedWidth=width;
      } else if(c[0]==='rect') {
        const [,x1,y1,x2,y2,fill,color,width]=c;
        ctx.rect(Math.min(x1,x2),Math.min(y1,y2),Math.abs(x2-x1),Math.abs(y2-y1));
        requestedFill=fill;stroke=color;requestedWidth=width;
      } else if(c[0]==='ellipse') {
        const [,x,y,rx,ry,fill,color,width]=c;
        ctx.ellipse(x,y,rx,ry,0,0,2*Math.PI);requestedFill=fill;stroke=color;requestedWidth=width;
      } else if(c[0]==='path') {
        const [,subpaths,rule,fill,color,width]=c;
        for(const p of subpaths){p.points.forEach((v,i)=>i?ctx.lineTo(...v):ctx.moveTo(...v));if(p.closed)ctx.closePath();}
        requestedFill=fill;stroke=color;requestedWidth=width;fillRule=rule;
      } else fail('Unknown Canvas opcode');
      const width=requestedWidth || 1/frame.dpr;
      if(width!==lineWidth){ctx.lineWidth=defaults.width;ctx.lineWidth=width;lineWidth=width;}
      // Native setters can silently ignore invalid values. Reset to the frame
      // default on a changed request, preserving isolated-command semantics
      // without validating arguments or saving the whole context per primitive.
      if(requestedFill!=null){
        if(requestedFill!==fill){ctx.fillStyle=defaults.fill;ctx.fillStyle=requestedFill;fill=requestedFill;}
        ctx.fill(fillRule || 'evenodd');
      }
      if(stroke!==null){
        if(stroke!==strokeStyle){ctx.strokeStyle=defaults.stroke;ctx.strokeStyle=stroke;strokeStyle=stroke;}
        ctx.stroke();
      }
    } catch(error) {
      console.warn(`Canvas ${frame.node_id}: skipped command ${index} (${c?.[0] ?? 'unknown'})`,error);
    } finally {if(scoped)ctx.restore();}
  }
  while(stack.length){ctx.restore();stack.pop();}
}

export class Canvases {
  constructor(renderer,control,onError) {
    this.renderer=renderer;this.control=control;this.onError=onError;this.records=new Map();this.revisions=new Map();this.raf=null;
    this.images=new Images(renderer.resources.url,renderer.resources.valid);
    this.onResize=()=>this.schedule();this.onVisibility=()=>{if(document.hidden)this.blurAll();this.run();};
    this.onBlur=()=>this.blurAll();window.addEventListener('blur',this.onBlur);
    window.addEventListener('resize',this.onResize);document.addEventListener('visibilitychange',this.onVisibility);
    this.onDensity=()=>{this.watchDensity();this.schedule();};this.watchDensity();
  }
  watchDensity() {
    this.density?.removeEventListener('change',this.onDensity);
    this.density=matchMedia(`(resolution: ${devicePixelRatio}dppx)`);this.density.addEventListener('change',this.onDensity);
  }
  add(id,element) {
    const canvas=document.createElement('canvas');canvas.width=canvas.height=0;element.append(canvas);
    const r={canvas,element,measure:null,revision:this.revisions.get(id)||0,pending:null,presented:null,intact:false,pointers:new Map()};
    r.observer=new ResizeObserver(()=>this.schedule());r.observer.observe(element);
    canvas.addEventListener('contextlost',event=>{event.preventDefault();r.intact=false;});
    canvas.addEventListener('contextrestored',()=>{r.measure=null;this.schedule();});
    this.records.set(id,r);
    for(const [native,name] of [['pointerdown','mousedown'],['pointerup','mouseup'],['pointermove','mousemove'],
      ['pointerenter','mouseenter'],['pointerleave','mouseleave'],['click','click'],['dblclick','dblclick']])
      element.addEventListener(native,event=>this.pointer(id,name,event));
    // PointerEvent.detail is zero in Chrome. The corresponding MouseEvent
    // carries the native click count, while pointerdown handles capture/focus.
    element.addEventListener('mousedown',event=>{
      const pointerId=r.mouseDown;r.mouseDown=null;
      if(pointerId==null)return;
      this.event(id,'mousedown',{...this.position(r,event),button:button(event),
        buttons:event.buttons&31,modifiers:modifiers(event),pointer_id:pointerId,
        cancelled:false,dblclick:event.detail===2});
    });
    for(const name of ['keydown','keyup'])element.addEventListener(name,event=>{
      if(!this.renderer.state.nodes.get(id)?.events[name] || event.isComposing)return;
      // Tab retains normal focus traversal; browser/system shortcuts retain
      // their defaults. Cancel only keys which scroll a focused drawing area.
      if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown',' ','PageUp','PageDown','Home','End'].includes(event.key))event.preventDefault();
      this.event(id,name,{key:event.key,code:event.code,modifiers:modifiers(event)});
    });
    element.addEventListener('blur',()=>this.blur(id));
    element.addEventListener('contextmenu',event=>{
      if(this.renderer.state.nodes.get(id)?.events.keydown)event.preventDefault();
    });
    element.addEventListener('pointercancel',event=>this.cancel(id,event));
    element.addEventListener('lostpointercapture',event=>this.cancel(id,event));
    element.addEventListener('wheel',event=>{
      if(!this.renderer.state.nodes.get(id)?.events.wheel)return;
      event.preventDefault();const p=this.position(r,event);
      this.event(id,'wheel',{...p,delta_x:event.deltaX,delta_y:event.deltaY,
        delta_mode:['pixel','line','page'][event.deltaMode],modifiers:modifiers(event)});
    },{passive:false});
  }
  position(r,e) {
    const rect=r.element.getBoundingClientRect();
    return {x:(e.clientX-rect.left)*(rect.width?r.element.clientWidth/rect.width:1),
      y:(e.clientY-rect.top)*(rect.height?r.element.clientHeight/rect.height:1)};
  }
  event(id,name,data) {
    const renderer=this.renderer,n=renderer.state.nodes.get(id);
    if(renderer.dirty || renderer.applying || !n?.events[name])return;
    if(['mousedown','click','dblclick'].includes(name)) {
      const focused=renderer.focusedEditor();if(focused)renderer.commit(focused);
    }
    renderer.actions('event',{node_id:id,event:name,token:n.events[name],observed_render_rev:renderer.rev,data});
  }
  pointer(id,name,e) {
    if(this.renderer.dirty || this.renderer.applying)return;
    const r=this.records.get(id);if(!r)return;
    const events=this.renderer.state.nodes.get(id)?.events || {};
    if(name==='mousedown' && events.keydown) {
      const focused=this.renderer.focusedEditor();if(focused)this.renderer.commit(focused);
      r.element.focus({preventScroll:true});
    }
    if(name==='mousedown' && (events.mousedown || events.mouseup || events.mousemove)) {
      r.pointers.set(e.pointerId,{...this.position(r,e),button:button(e),buttons:e.buttons&31,modifiers:modifiers(e)});
      // A pointer can become inactive before its capture request is processed.
      try{r.element.setPointerCapture(e.pointerId);}catch(error){if(error.name!=='NotFoundError')throw error;}
    }
    if(name==='mousedown' && e.pointerType==='mouse' && events.keydown){r.mouseDown=e.pointerId;return;}
    const samples=name==='mousemove'?(e.getCoalescedEvents?.() || []):[];
    for(const sample of samples.length?samples:[e]) {
      const buttons=sample.buttons&31;
      const changed=name==='mousemove'?(buttons && !(buttons&(buttons-1))?buttons:0):button(sample);
      this.event(id,name,{...this.position(r,sample),button:['mouseenter','mouseleave'].includes(name)?0:changed,
        buttons,modifiers:modifiers(sample),pointer_id:Math.max(0,sample.pointerId || 0),cancelled:false,
        ...(name==='mousedown'?{dblclick:sample.detail===2}:{})});
      if(r.pointers.has(e.pointerId))r.pointers.set(e.pointerId,{...this.position(r,sample),button:changed,buttons,modifiers:modifiers(sample)});
    }
    if(name==='mouseup' && !e.buttons) {
      r.pointers.delete(e.pointerId);
      if(r.element.hasPointerCapture(e.pointerId))r.element.releasePointerCapture(e.pointerId);
    }
  }
  cancel(id,e) {
    const r=this.records.get(id),last=r?.pointers.get(e.pointerId);if(!last)return;
    r.pointers.delete(e.pointerId);
    this.event(id,'mouseup',{...last,buttons:0,pointer_id:e.pointerId,cancelled:true});
    if(r.element.hasPointerCapture(e.pointerId))r.element.releasePointerCapture(e.pointerId);
  }
  blur(id) {
    const r=this.records.get(id);if(!r)return;
    for(const pointerId of [...r.pointers.keys()])this.cancel(id,{pointerId});
    this.event(id,'blur',{cancelled:true});
  }
  blurAll() {for(const id of this.records.keys())this.blur(id);}
  update(n) {
    const r=this.records.get(n.id);
    if(n.events.keydown)r.element.tabIndex=0;else r.element.removeAttribute('tabindex');
    if(n.props.show_fps && !r.fps) {
      const label=document.createElement('span');label.className='pui-canvas-fps';
      label.textContent='FPS: ...';r.element.append(label);
      r.fps={label,started:null,frames:0};
    } else if(!n.props.show_fps && r.fps) {
      r.fps.label.remove();r.fps=null;
    }
    r.element.style.touchAction=['mousedown','mouseup','mousemove'].some(name=>n.events[name])?'none':'';
  }
  ack(frame,status) {queueMicrotask(()=>this.control('canvas_ack',{node_id:frame.node_id,frame_rev:frame.frame_rev,measure_rev:frame.measure_rev,status}));}
  measure(id,r) {
    const visible=!document.hidden && r.element.getClientRects().length>0 && getComputedStyle(r.element).visibility!=='hidden';
    const width=visible?r.element.clientWidth:0,height=visible?r.element.clientHeight:0,dpr=devicePixelRatio;
    const m={node_id:id,measure_rev:r.revision+1,width,height,dpr,visible:visible && width>0 && height>0};
    if(width>16384 || height>16384 || dpr>8 || Math.ceil(width*dpr)*Math.ceil(height*dpr)>16777216)
      fail('Canvas bitmap exceeds limits');
    if(!r.measure || ['width','height','dpr','visible'].some(k=>m[k]!==r.measure[k])) {
      r.measure=m;r.revision=m.measure_rev;r.intact=false;r.canvas.width=r.canvas.height=0;
      this.revisions.set(id,r.revision);
      this.control('measure',m);
    }
  }
  sync(state,body) {
    this.images.retain(state.canvases.values());
    for(const id of this.revisions.keys())if(!state.nodes.has(id))this.revisions.delete(id);
    const offered=body.mode==='snapshot'?[...state.canvases.values()]:
      [...new Set(body.ops.filter(op=>['put_canvas','patch_canvas'].includes(op.op)).map(op=>op.frame.node_id))]
        .map(id=>state.canvases.get(id)).filter(Boolean);
    for(const [id,r] of this.records)if(!state.canvases.has(id)){r.pending=null;r.presented=null;r.intact=false;r.canvas.width=r.canvas.height=0;}
    for(const f of offered) {
      const r=this.records.get(f.node_id);
      if(r.pending && r.pending.frame_rev!==f.frame_rev)this.ack(r.pending,'superseded');
      r.pending=f;
      if(r.loading && r.loading.frame!==f)r.loading=null;
    }
    this.schedule();
  }
  schedule() {
    if(this.raf===null)this.raf=requestAnimationFrame(()=>{this.raf=null;this.run();});
  }
  run() {
    if(this.renderer.dirty || this.renderer.applying)return;
    try {
      for(const [id,r] of this.records) {
        this.measure(id,r);
        const f=r.pending;if(!f)continue;
        let status;
        if(!r.measure.visible)status='hidden';
        else if(f.measure_rev!==r.measure.measure_rev)status='stale_measure';
        else if(r.intact && r.presented===f.frame_rev)status='unchanged';
        else {
          if(['width','height','dpr'].some(k=>f[k]!==r.measure[k]))fail('Canvas measurement mismatch');
          if(f.commands.some(c=>c?.[0]==='image')) {
            if(!r.loading || r.loading.frame!==f) {
              const loading=r.loading={frame:f,ready:false,images:null,error:null};
              this.images.frame(f).then(images=>{loading.images=images;loading.ready=true;this.schedule();},
                error=>{loading.error=error;loading.ready=true;this.schedule();});
            }
            if(!r.loading.ready)continue;
            if(r.loading.error)throw r.loading.error;
          }
          const images=r.loading?.images;
          drawFrame(r.canvas,f,getComputedStyle(r.element),images);r.loading=null;
          // Failed image loads stop continuous retries but do not hide other drawing.
          status=images && [...images.values()].some(image=>image instanceof Error)?'failed':'drawn';
          r.intact=status==='drawn';r.presented=f.frame_rev;
          if(status==='drawn' && r.fps) {
            const now=performance.now(),fps=r.fps;
            if(fps.started===null)fps.started=now;
            else {
              fps.frames++;
              const elapsed=now-fps.started;
              if(elapsed>=500) {
                fps.label.textContent=`FPS: ${(fps.frames*1000/elapsed).toFixed(1)}`;
                fps.started=now;fps.frames=0;
              }
            }
          }
        }
        r.pending=null;this.ack(f,status);
      }
    } catch(error){this.onError(error);}
  }
  reset() {
    this.images.retain([]);
    this.revisions.clear();
    for(const r of this.records.values()){r.measure=null;r.revision=0;r.pending=null;r.loading=null;r.presented=null;r.intact=false;r.pointers.clear();}
  }
  remove(id) {
    const r=this.records.get(id);if(!r)return;
    for(const id of r.pointers.keys())if(r.element.hasPointerCapture(id))r.element.releasePointerCapture(id);
    r.observer.disconnect();r.canvas.width=r.canvas.height=0;this.records.delete(id);
  }
  destroy() {
    this.images.retain([]);
    for(const id of this.records.keys())this.remove(id);
    if(this.raf!==null)cancelAnimationFrame(this.raf);
    window.removeEventListener('blur',this.onBlur);window.removeEventListener('resize',this.onResize);document.removeEventListener('visibilitychange',this.onVisibility);
    this.density.removeEventListener('change',this.onDensity);
    this.revisions.clear();
  }
}
