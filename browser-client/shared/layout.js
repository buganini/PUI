// Expansion is local to siblings, in the coordinate system of their parent.
// Descendant demand promotes containers to level 2, without inheriting weights.
const priorities = {
  HBox:[3,1], VBox:[1,3], Splitter:[3,3], Grid:[1,1], Stack:[1,1],
  Views:[3,3], Tabs:[3,3], Tab:[3,3],
  TextField:[4,0], MaskedField:[4,0], Text:[4,4], Canvas:[4,4], Table:[4,4], ProgressBar:[1,0],
};
const linear = new Set(['Window','HBox','VBox','Scroll','Views','Tabs','Tab']);
const dimensions = ['width','height'];

function priority(node, axis) {
  if(node.type==='Scroll')return node.props[axis===0?'horizontal':'vertical']==='hidden'?1:4;
  // Explicit Canvas dimensions keep their existing fixed-size behavior, but
  // specifying one dimension must not disable expansion on the other axis.
  if(node.type==='Canvas' && node.layout[dimensions[axis]]!==undefined)return 0;
  if(node.type==='Divider')return axis===0?1:0;
  if(node.props.direction)return (node.props.direction==='row'?[3,1]:[1,3])[axis];
  return priorities[node.type]?.[axis] || 0;
}

export function applyLayout(state, elements) {
  const parents=new Map(), demandCache=new Map();
  for(const parent of state.nodes.values())for(const id of parent.children)parents.set(id,parent);
  const mainAxis=p=>(p.props.direction==='row' || p.type==='HBox')?0:1;
  const demand=(node,axis)=>{
    const key=node.id+':'+axis;
    if(demandCache.has(key))return demandCache.get(key);
    const parent=parents.get(node.id), weight=node.layout.weight;
    let value=priority(node,axis);
    if(elements.get(node.id).hidden)value=0;
    else if(parent && linear.has(parent.type) && mainAxis(parent)===axis && weight!==undefined)
      value=weight>0?5:0;
    else if(value<2 && node.layout[dimensions[axis]]===undefined &&
      node.children.some(id=>demand(state.nodes.get(id),axis)>=2))value=2;
    demandCache.set(key,value);
    return value;
  };
  const gridChildren=new Set();
  for(const parent of state.nodes.values())
    if(parent.type==='Grid')for(const id of parent.children)gridChildren.add(id);
  // A retained node can move from a linear container to Grid/Stack. Clear the
  // parent-dependent properties even when that node received no property patch.
  for(const node of state.nodes.values()) {
    const element=elements.get(node.id), style=element.style;
    if(node.type==='Divider') {
      element.classList.remove('pui-divider-vertical');
      element.setAttribute('aria-orientation','horizontal');
    }
    style.flex='';style.alignSelf=gridChildren.has(node.id)?'stretch':'';
    // Grid cells stretch like native Grid items. Keep the declared dimensions
    // as minimums (set by the renderer), allowing expanded spans to fill holes.
    // Restore fixed dimensions when a retained item leaves Grid.
    for(const dimension of dimensions)
      style[dimension]=gridChildren.has(node.id)?'auto':
        node.layout[dimension]===undefined?'':node.layout[dimension]+'px';
  }
  for(const parent of state.nodes.values()) {
    if(!linear.has(parent.type))continue;
    // Tabs' public children live in the column-oriented page wrapper, even
    // when the tab header itself is on the left or right.
    const axis=(parent.props.direction==='row' || parent.type==='HBox')?0:1, cross=1-axis;
    const centered=parent.type==='HBox' || parent.type==='VBox';
    const scrolling=parent.type==='Scroll' && parent.props.vertical!=='hidden';
    const children=parent.children.map(id=>state.nodes.get(id)).filter(n=>!elements.get(n.id).hidden);
    const mainPriority=n=>n.type==='Divider'?0:
      demand(n,axis);
    const highest=children.reduce((maximum,n)=>Math.max(maximum,mainPriority(n)),0);
    for(const node of children) {
      const style=elements.get(node.id).style, weight=node.layout.weight;
      if(node.type==='Divider') {
        const element=elements.get(node.id);
        element.classList.toggle('pui-divider-vertical',axis===0);
        element.setAttribute('aria-orientation',axis===0?'vertical':'horizontal');
        style.flex='0 0 auto';
        style.alignSelf='stretch';
        continue;
      }
      const grows=!scrolling && highest>0 && mainPriority(node)===highest;
      const weighted=grows && weight>0;
      // Scroll content keeps its natural extent. A zero weight also keeps its
      // preferred size instead of collapsing it to a zero flex basis.
      const shrinks=!scrolling && (weighted || (weight!==0 && demand(node,axis)>0));
      style.flex=`${grows?(weighted?weight:1):0} ${shrinks?1:0} ${weighted?'0px':'auto'}`;
      // Explicit cross-axis sizes cannot stretch; center those alongside
      // naturally compact controls in HBox/VBox.
      const stretches=demand(node,cross)>0 &&
        (!centered || node.layout[dimensions[cross]]===undefined);
      style.alignSelf=stretches?'stretch':(axis===0?'center':'flex-start');
    }
  }
}
