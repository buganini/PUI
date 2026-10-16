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
  const pyodide=await requireBuild('esbuild').build({
    entryPoints:['client','worker'].map(name=>path.join(root,'browser-client/pyodide/'+name+'.js')),
    outdir:'unused',bundle:true,write:false,metafile:true,format:'esm',platform:'browser',
  });
  for(const source of Object.keys(pyodide.metafile.inputs)) {
    assert.match(source,/browser-client\/(shared|pyodide)\//);
    assert.doesNotMatch(source,/node_modules|\/web\//);
  }
  const code=pyodide.outputFiles.map(f=>f.text).join('\n');
  assert.doesNotMatch(code,/initializeCodec|new WebSocket/);
  assert.match(code,/cdn\.jsdelivr\.net\/pyodide\/v314\.0\.7\/full\//);
  console.log('Pyodide bundle uses shared/local code and the pinned CDN; no Web adapters/codecs.');
})().catch(error=>{console.error(error);process.exitCode=1;});
