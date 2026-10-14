// Display lists are data only. Drawing/presentation credit is independent of DOM ACKs.
const fail=message=>{throw new Error(message);};
const fields=(v,names)=>v && Object.getPrototypeOf(v)===Object.prototype &&
  Object.keys(v).sort().join(',')===names.split(' ').sort().join(',');
const num=(v,min=-1e9)=>typeof v==='number' && Number.isFinite(v) && v>=min && v<=1e9;
const integer=v=>Number.isSafeInteger(v) && v>0;
const color=v=>v===null || (typeof v==='string' && /^#[0-9a-f]{6}$/i.test(v));
const point=v=>Array.isArray(v) && v.length===2 && v.every(x=>num(x));
const shapes={line:'x1 y1 x2 y2 color width',polyline:'points color width',
  cubic:'start control1 control2 end color width',polygon:'points fill stroke width',
  rect:'x1 y1 x2 y2 fill stroke width',ellipse:'x y rx ry fill stroke width',
  text:'x y text w h size color rotate anchor',path:'subpaths fill_rule fill stroke width'};
const anchors={LEFT_TOP:[0,0],LEFT_CENTER:[0,.5],LEFT_BOTTOM:[0,1],CENTER_TOP:[.5,0],
  CENTER:[.5,.5],CENTER_BOTTOM:[.5,1],RIGHT_TOP:[1,0],RIGHT_CENTER:[1,.5],RIGHT_BOTTOM:[1,1]};
export const canvasEvents=['click','dblclick','mousedown','mouseup','mousemove','mouseenter','mouseleave','wheel'];
const modifiers=e=>(e.shiftKey?1:0)|(e.ctrlKey?2:0)|(e.altKey?4:0)|(e.metaKey?8:0);
const button=e=>[1,4,2,8,16][e.button] || 0;
export function validateFrame(f) {
  if(!fields(f,'node_id frame_rev measure_rev width height dpr background continue commands') ||
    typeof f.node_id!=='string' || !f.node_id || !integer(f.frame_rev) || !integer(f.measure_rev) ||
    !num(f.width,0) || !num(f.height,0) || f.width===0 || f.height===0 || f.width>16384 || f.height>16384 ||
    !num(f.dpr,0) || f.dpr===0 || f.dpr>8 || Math.ceil(f.width*f.dpr)*Math.ceil(f.height*f.dpr)>16777216 ||
    !color(f.background) || typeof f.continue!=='boolean' || !Array.isArray(f.commands) || f.commands.length>10000)
    fail('Invalid Canvas frame');
  for(const c of f.commands) {
    if(!Object.hasOwn(shapes,c?.op) || !fields(c,'op '+shapes[c.op]))fail('Invalid Canvas command');
    for(const [key,value] of Object.entries(c)) {
      if(key==='op')continue;
      if(['color','fill','stroke'].includes(key)){if(!color(value))fail('Invalid Canvas color');}
      else if(key==='points'){if(!Array.isArray(value) || value.length>20000 || !value.every(point))fail('Invalid Canvas points');}
      else if(key==='subpaths'){
        if(!Array.isArray(value) || value.some(p=>!fields(p,'points closed') || typeof p.closed!=='boolean' ||
          !Array.isArray(p.points) || !p.points.every(point)) || value.reduce((n,p)=>n+p.points.length,0)>20000)fail('Invalid Canvas subpaths');
      }
      else if(key==='fill_rule'){if(!['evenodd','nonzero'].includes(value))fail('Invalid Canvas fill rule');}
      else if(['start','control1','control2','end'].includes(key)){if(!point(value))fail('Invalid Canvas point');}
      else if(key==='text'){if(typeof value!=='string' || [...value].length>65536)fail('Invalid Canvas text');}
      else if(key==='anchor'){if(!Object.hasOwn(anchors,value))fail('Invalid Canvas anchor');}
      else if(['w','h','size'].includes(key)){if(value!==null && !num(value,0))fail('Invalid text bounds');}
      else if(!num(value,['width','rx','ry'].includes(key)?0:-1e9))fail('Invalid Canvas number');
    }
  }
}

function text(ctx,c,style) {
  const size=c.size===null?parseFloat(style.fontSize):c.size*96/72;
  if(size<=0)return;
  ctx.font=`${style.fontWeight} ${size}px ${style.fontFamily}`;
  ctx.textBaseline='alphabetic';ctx.textAlign='left';
  const lines=c.text.split('\n'),metrics=ctx.measureText('Mg');
  const ascent=metrics.fontBoundingBoxAscent || metrics.actualBoundingBoxAscent || size*.8;
  const descent=metrics.fontBoundingBoxDescent || metrics.actualBoundingBoxDescent || size*.2;
  const height=(ascent+descent)*lines.length,width=lines.reduce((w,line)=>Math.max(w,ctx.measureText(line).width),0);
  const anchor=anchors[c.anchor];ctx.translate(c.x,c.y);ctx.rotate(c.rotate*Math.PI/180);
  ctx.translate(-anchor[0]*width,-anchor[1]*height);
  if(c.w!==null || c.h!==null){ctx.beginPath();ctx.rect(0,0,c.w??width,c.h??height);ctx.clip();}
  ctx.fillStyle=c.color || style.color;
  lines.forEach((line,i)=>ctx.fillText(line,0,ascent+i*(ascent+descent)));
}

export function drawFrame(canvas,frame,style) {
  canvas.width=Math.ceil(frame.width*frame.dpr);canvas.height=Math.ceil(frame.height*frame.dpr);
  const ctx=canvas.getContext('2d');if(!ctx)fail('Canvas 2D context is unavailable');
  ctx.setTransform(frame.dpr,0,0,frame.dpr,0,0);
  if(frame.background!==null){ctx.fillStyle=frame.background;ctx.fillRect(0,0,frame.width,frame.height);}
  for(const c of frame.commands) {
    ctx.save();
    try {
      if(c.op==='text'){text(ctx,c,style);continue;}
      ctx.beginPath();ctx.lineWidth=c.width || 1/frame.dpr;ctx.lineCap='square';ctx.lineJoin='bevel';
      const stroke=c.stroke===undefined?c.color:c.stroke;
      if(c.op==='line'){ctx.moveTo(c.x1,c.y1);ctx.lineTo(c.x2,c.y2);}
      else if(c.op==='polyline' || c.op==='polygon'){
        c.points.forEach((p,i)=>i?ctx.lineTo(...p):ctx.moveTo(...p));if(c.op==='polygon')ctx.closePath();
      } else if(c.op==='cubic'){ctx.moveTo(...c.start);ctx.bezierCurveTo(...c.control1,...c.control2,...c.end);}
      else if(c.op==='path')for(const p of c.subpaths){p.points.forEach((v,i)=>i?ctx.lineTo(...v):ctx.moveTo(...v));if(p.closed)ctx.closePath();}
      else if(c.op==='rect')ctx.rect(Math.min(c.x1,c.x2),Math.min(c.y1,c.y2),Math.abs(c.x2-c.x1),Math.abs(c.y2-c.y1));
      else if(c.op==='ellipse')ctx.ellipse(c.x,c.y,c.rx,c.ry,0,0,2*Math.PI);
      if(c.fill!=null){ctx.fillStyle=c.fill;ctx.fill(c.fill_rule || 'evenodd');}
      if(stroke!==null){ctx.strokeStyle=stroke;ctx.stroke();}
    } finally {ctx.restore();}
  }
}

export class Canvases {
  constructor(renderer,control,onError) {
    this.renderer=renderer;this.control=control;this.onError=onError;this.records=new Map();this.revisions=new Map();this.raf=null;
    this.onResize=()=>this.schedule();this.onVisibility=()=>this.run();
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
    if(name==='mousedown' && (events.mousedown || events.mouseup || events.mousemove)) {
      r.pointers.set(e.pointerId,{...this.position(r,e),button:button(e),buttons:e.buttons&31,modifiers:modifiers(e)});
      // A pointer can become inactive before its capture request is processed.
      try{r.element.setPointerCapture(e.pointerId);}catch(error){if(error.name!=='NotFoundError')throw error;}
    }
    const samples=name==='mousemove'?(e.getCoalescedEvents?.() || []):[];
    for(const sample of samples.length?samples:[e]) {
      const buttons=sample.buttons&31;
      const changed=name==='mousemove'?(buttons && !(buttons&(buttons-1))?buttons:0):button(sample);
      this.event(id,name,{...this.position(r,sample),button:['mouseenter','mouseleave'].includes(name)?0:changed,
        buttons,modifiers:modifiers(sample),pointer_id:Math.max(0,sample.pointerId || 0),cancelled:false});
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
  update(n) {
    const r=this.records.get(n.id);
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
    for(const id of this.revisions.keys())if(!state.nodes.has(id))this.revisions.delete(id);
    const offered=body.mode==='snapshot'?body.canvases:body.ops.filter(op=>op.op==='put_canvas').map(op=>op.frame);
    for(const [id,r] of this.records)if(!state.canvases.has(id)){r.pending=null;r.presented=null;r.intact=false;r.canvas.width=r.canvas.height=0;}
    for(const f of offered) {
      const r=this.records.get(f.node_id);
      if(r.pending && r.pending.frame_rev!==f.frame_rev)this.ack(r.pending,'superseded');
      r.pending=f;
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
          drawFrame(r.canvas,f,getComputedStyle(r.element));r.intact=true;r.presented=f.frame_rev;status='drawn';
        }
        r.pending=null;this.ack(f,status);
      }
    } catch(error){this.onError(error);}
  }
  reset() {
    this.revisions.clear();
    for(const r of this.records.values()){r.measure=null;r.revision=0;r.pending=null;r.presented=null;r.intact=false;r.pointers.clear();}
  }
  remove(id) {
    const r=this.records.get(id);if(!r)return;
    for(const id of r.pointers.keys())if(r.element.hasPointerCapture(id))r.element.releasePointerCapture(id);
    r.observer.disconnect();r.canvas.width=r.canvas.height=0;this.records.delete(id);
  }
  destroy() {
    for(const id of this.records.keys())this.remove(id);
    if(this.raf!==null)cancelAnimationFrame(this.raf);
    window.removeEventListener('resize',this.onResize);document.removeEventListener('visibilitychange',this.onVisibility);
    this.density.removeEventListener('change',this.onDensity);
    this.revisions.clear();
  }
}
