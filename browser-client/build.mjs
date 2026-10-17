// Install pinned build dependencies in env/web-client; no Node runtime ships.
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { mkdir, copyFile, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
const root = fileURLToPath(new URL('../', import.meta.url));
const require = createRequire(path.join(root, 'env/web-client/package.json'));
const { build } = require('esbuild');
const output = path.join(root, 'PUI/web/static');
await mkdir(output, { recursive: true });
await build({ entryPoints: [path.join(root, 'browser-client/web/client.js')],
  outfile: path.join(output, 'client.js'), bundle: true, minify: true,
  format: 'esm', platform: 'browser', target: ['es2020'],
  nodePaths: [path.join(root, 'env/web-client/node_modules')], legalComments: 'eof' });
await copyFile(path.join(root, 'browser-client/shared/client.css'), path.join(output, 'client.css'));
const modules = path.join(root, 'env/web-client/node_modules');
await copyFile(path.join(modules, 'compress-utils/dist/algorithms/zstd/zstd.wasm'), path.join(output, 'zstd.wasm'));
let notices = '';
for (const name of ['@msgpack/msgpack', 'compress-utils']) {
  const directory = path.join(modules, name);
  const pkg = JSON.parse(await readFile(path.join(directory, 'package.json'), 'utf8'));
  notices += `${name} ${pkg.version}\n${await readFile(path.join(directory, 'LICENSE'), 'utf8')}\n\n`;
}
notices += await readFile(path.join(modules, 'compress-utils/THIRD_PARTY_NOTICES.md'), 'utf8') + '\n';
await writeFile(path.join(output, 'THIRD_PARTY_LICENSES.txt'), notices);
