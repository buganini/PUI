// Expansion is local to siblings, in the coordinate system of their parent.
// Descendants never promote the priority of their containing box.
const priorities = {
  HBox:[2,1], VBox:[1,2], Grid:[1,1], Stack:[1,1],
  Views:[2,2], Tabs:[2,2], Tab:[2,2],
  TextField:[3,0], MaskedField:[3,0], Text:[3,3], Canvas:[3,3], Table:[3,3], ProgressBar:[1,0],
};
const linear = new Set(['Window','HBox','VBox','Scroll','Views','Tabs','Tab']);
const dimensions = ['width','height'];

function priority(node, axis) {
  if(node.type==='Scroll')return node.props[axis===0?'horizontal':'vertical']==='hidden'?1:3;
  // Explicit Canvas dimensions keep their existing fixed-size behavior, but
  // specifying one dimension must not disable expansion on the other axis.
  if(node.type==='Canvas' && node.layout[dimensions[axis]]!==undefined)return 0;
  if(node.type==='Divider')return axis===0?1:0;
  if(node.props.direction)return (node.props.direction==='row'?[2,1]:[1,2])[axis];
  return priorities[node.type]?.[axis] || 0;
}

export function applyLayout(state, elements) {
  // A retained node can move from a linear container to Grid/Stack. Clear the
  // parent-dependent properties even when that node received no property patch.
  for(const node of state.nodes.values()) {
    const style=elements.get(node.id).style;
    style.flex='';style.alignSelf='';
  }
  for(const parent of state.nodes.values()) {
    if(!linear.has(parent.type))continue;
    // Tabs' public children live in the column-oriented page wrapper, even
    // when the tab header itself is on the left or right.
    const axis=(parent.props.direction==='row' || parent.type==='HBox')?0:1, cross=1-axis;
    const centered=parent.type==='HBox' || parent.type==='VBox';
    const scrolling=parent.type==='Scroll' && parent.props.vertical!=='hidden';
    const children=parent.children.map(id=>state.nodes.get(id)).filter(n=>!elements.get(n.id).hidden);
    const mainPriority=n=>n.layout.weight===undefined?priority(n,axis):(n.layout.weight>0?4:0);
    const highest=children.reduce((maximum,n)=>Math.max(maximum,mainPriority(n)),0);
    for(const node of children) {
      const style=elements.get(node.id).style, weight=node.layout.weight;
      const grows=!scrolling && highest>0 && mainPriority(node)===highest;
      const weighted=grows && weight>0;
      // Scroll content keeps its natural extent. A zero weight also keeps its
      // preferred size instead of collapsing it to a zero flex basis.
      const shrinks=!scrolling && (weighted || (weight!==0 && priority(node,axis)>0));
      style.flex=`${grows?(weighted?weight:1):0} ${shrinks?1:0} ${weighted?'0px':'auto'}`;
      // Explicit cross-axis sizes cannot stretch; center those alongside
      // naturally compact controls in HBox/VBox.
      const stretches=priority(node,cross)>0 &&
        (!centered || node.layout[dimensions[cross]]===undefined);
      style.alignSelf=stretches?'stretch':(axis===0?'center':'flex-start');
    }
  }
}
