// Shared native-directory filters must not disconnect browser renderers.
const assert = require('node:assert/strict');
const {buildSync} = require('../env/web-client/node_modules/esbuild');
const {mkdtempSync, rmSync} = require('node:fs');
const {tmpdir} = require('node:os');
const path = require('node:path');
const directory = mkdtempSync(path.join(tmpdir(), 'pui-drop-filter-'));
try {
  const bundle = path.join(directory, 'dom.cjs');
  buildSync({entryPoints: [path.join(__dirname, '../browser-client/shared/dom.js')],
    bundle: true, platform: 'node', format: 'cjs', outfile: bundle});
  const {prepare} = require(bundle);
  const node = {id:'window', type:'Window', props:{title:'Drop'}, children:[],
    layout:{}, style:{}, bindings:{}, events:{}};
  const snapshot = {mode:'snapshot', base_rev:null, rev:1, processed_seq:0,
    roots:[node], bindings:[], canvases:[]};
  for (const extensions of [null, ['.txt', '.json', '/'], ['/']]) {
    node.props.drop_extensions = extensions;
    assert.doesNotThrow(() => prepare(null, snapshot));
  }
  for (const extensions of [['directory'], [42], '/']) {
    node.props.drop_extensions = extensions;
    assert.throws(() => prepare(null, snapshot), /Invalid drop extensions/);
  }
  console.log('Drop filter validation passed');
} finally {
  rmSync(directory, {recursive:true, force:true});
}
