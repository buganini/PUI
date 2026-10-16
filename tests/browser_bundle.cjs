// A shared UI bundle must not require Web codecs, Pyodide, or either bootstrap.
const assert=require('node:assert/strict');
const path=require('node:path');
const {createRequire}=require('node:module');
const root=path.resolve(__dirname,'..');
const requireBuild=createRequire(path.join(root,'env/web-client/package.json'));

(async()=>{
  const result=await requireBuild('esbuild').build({
    entryPoints:[path.join(root,'browser-client/shared/controller.js')],
    bundle:true,write:false,metafile:true,format:'esm',platform:'browser',
  });
  for(const source of Object.keys(result.metafile.inputs)) {
    assert.match(source,/browser-client\/shared\//);
    assert.doesNotMatch(source,/node_modules|\/web\/|\/pyodide\//);
  }
  assert.doesNotMatch(result.outputFiles[0].text,/initializeCodec|new WebSocket|loadPyodide/);
  console.log('Shared renderer/controller bundle has no backend or codec dependencies.');
})().catch(error=>{console.error(error);process.exitCode=1;});
