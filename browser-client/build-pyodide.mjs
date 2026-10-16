// Build only the local bridge and shared renderer, without Web codecs.
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {readFile,copyFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const require=createRequire(path.join(root,'env/web-client/package.json'));
const {build}=require('esbuild');
const output=path.join(root,'dist/pyodide/cookbook/pyodide');
const archive=await readFile(path.join(output,'app.zip'));
const hash=createHash('sha256').update(archive).digest('hex');
// Include all bundled code in the build identity (also detects old cached workers).
const probe=await build({entryPoints:['client','worker'].map(n=>path.join(root,`browser-client/pyodide/${n}.js`)),
  outdir:output,bundle:true,write:false,format:'esm',platform:'browser',target:['es2022']});
const identity=createHash('sha256').update(hash);
for(const file of probe.outputFiles)identity.update(file.contents);
const version=identity.digest('hex');
await build({entryPoints:['client','worker'].map(n=>path.join(root,`browser-client/pyodide/${n}.js`)),
  outdir:output,bundle:true,minify:true,format:'esm',platform:'browser',target:['es2022'],
  define:{__PUI_BUILD__:JSON.stringify(version),__PUI_ARCHIVE_HASH__:JSON.stringify(hash)},
  legalComments:'eof'});
await copyFile(path.join(root,'browser-client/shared/client.css'),path.join(output,'client.css'));
console.log(`Built Pyodide cookbook ${version.slice(0,12)} (${archive.length} archive bytes)`);
