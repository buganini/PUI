const login=require('./web_login.cjs');
// Run against a Web cookbook, with PUI_WEB_URL/PUI_BROWSER_MODULES overrides.
const assert = require('node:assert/strict'), path = require('node:path');
const {createRequire} = require('node:module');
const requireBrowser = process.env.PUI_BROWSER_MODULES
  ? createRequire(path.join(process.env.PUI_BROWSER_MODULES, 'package.json')) : require;
const {chromium} = requireBrowser('playwright');

(async () => {
  const browser = await chromium.launch({executablePath: process.env.PUI_CHROME || '/usr/bin/google-chrome',
    headless: true, args: ['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport: {width: 1600, height: 1050}});
    page.setDefaultTimeout(30000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.env.PUI_WEB_URL || 'http://localhost:8866/pui/');await login(page);
    await page.getByRole('button', {name: 'HeavyCanvas', exact: true}).click();
    const bitmap = page.locator('.pui-Canvas canvas');
    const image = () => bitmap.evaluate(c => c.toDataURL());
    const changed = before => page.waitForFunction(value => {
      const c = document.querySelector('.pui-Canvas canvas');
      return c?.width > 0 && c.toDataURL() !== value;
    }, before);
    await page.waitForFunction(() => document.querySelector('.pui-Canvas canvas')?.height === 720);
    await page.getByText('1,000 sessions | Seed 42 | ~9,000 draw calls', {exact: true}).waitFor();
    // A finished frame contains both the background and the four panel grids.
    const pixels = await bitmap.evaluate(c => {
      const ctx = c.getContext('2d');
      return [[0, 0], [70, 24], [70, 340]].map(([x, y]) => [...ctx.getImageData(x, y, 1, 1).data]);
    });
    assert.deepEqual(pixels[0], [16, 26, 43, 255]);
    assert.notDeepEqual(pixels[1], pixels[0]);
    const original = await image();
    let box = await bitmap.boundingBox();
    await page.mouse.move(box.x + box.width * 0.6, box.y + 110);
    await changed(original);
    const hovered = await image();
    if (process.env.PUI_HEAVY_SCREENSHOT) {
      await bitmap.screenshot({path: process.env.PUI_HEAVY_SCREENSHOT});
    }
    await page.mouse.move(0, 0);
    await page.waitForFunction(value => document.querySelector('.pui-Canvas canvas').toDataURL() === value, original);
    assert.notEqual(hovered, original);

    await page.mouse.move(box.x + box.width * 0.7, box.y + 110);
    await changed(original);
    const scrollPosition = () => bitmap.evaluate(c => {
      const positions = [];
      for (let node = c; node; node = node.parentElement) positions.push([node.scrollLeft, node.scrollTop]);
      return positions;
    });
    const scrollBefore = await scrollPosition();
    await page.mouse.wheel(0, -120);
    await page.getByText('Visible: 800 / 1,000 sessions | Zoom 1.25x', {exact: true}).waitFor();
    await page.mouse.move(0, 0);
    await changed(original);
    assert.deepEqual(await scrollPosition(), scrollBefore, 'chart wheel must not scroll the page');
    await page.getByRole('button', {name: 'Reset zoom', exact: true}).click();
    await page.getByText('Visible: 1,000 / 1,000 sessions | Zoom 1.00x', {exact: true}).waitFor();
    await page.waitForFunction(value => document.querySelector('.pui-Canvas canvas').toDataURL() === value, original);

    await page.getByRole('button', {name: 'Regenerate', exact: true}).click();
    await page.getByText('1,000 sessions | Seed 43 | ~9,000 draw calls', {exact: true}).waitFor();
    await changed(original);
    let before = await image();
    const counts = [1000, 3000, 5000, 7500, 10000, 15000, 20000, 25000, 30000];
    assert.deepEqual(await page.getByRole('combobox').locator('option:not([hidden])').allTextContents(), counts.map(String));
    for (const count of counts.slice(1)) {
      const label = `${count.toLocaleString('en-US')} sessions | Seed 43 | ~${(9 * count).toLocaleString('en-US')} draw calls`;
      await page.getByRole('combobox').selectOption({label: String(count)});
      await page.getByText(label, {exact: true}).waitFor();
      await changed(before);
      before = await image();
    }
    box = await bitmap.boundingBox();
    await page.mouse.move(box.x + box.width * 0.7, box.y + 120);
    await changed(before);
    await page.mouse.wheel(0, -120);
    await page.getByText('Visible: 24,000 / 30,000 sessions | Zoom 1.25x', {exact: true}).waitFor();
    await page.getByText('30,000 sessions | Seed 43 | ~216,000 draw calls', {exact: true}).waitFor();
    await page.mouse.move(0, 0);
    await changed(before);
    // Wheel out restores the complete display list after a large replacement.
    await page.mouse.move(box.x + box.width * 0.7, box.y + 120);
    await page.mouse.wheel(0, 120);
    await page.getByText('Visible: 30,000 / 30,000 sessions | Zoom 1.00x', {exact: true}).waitFor();
    await page.mouse.move(0, 0);
    await page.waitForFunction(value => document.querySelector('.pui-Canvas canvas').toDataURL() === value, before);
    const oldWidth = box.width;
    await page.setViewportSize({width: 1200, height: 850});
    await page.waitForFunction(width => {
      const c = document.querySelector('.pui-Canvas canvas');
      return c?.width > 0 && c.width < width && c.height === 720;
    }, oldWidth);
    assert.deepEqual(errors, []);
    assert.equal(await page.locator('#pui-status').isVisible(), false);
    // Navigation retires the large display list and mounts a fresh example.
    await page.getByRole('button', {name: 'Canvas', exact: true}).click();
    await page.getByText('Rotate: 15', {exact: true}).waitFor();
    await page.getByRole('button', {name: 'HeavyCanvas', exact: true}).click();
    await page.getByText('1,000 sessions | Seed 42 | ~9,000 draw calls', {exact: true}).waitFor();
    assert.deepEqual(errors, []);
    console.log('HeavyCanvas: rendering, hover, wheel zoom/reset, large command replacement, regeneration, presets, resize and remount passed.');
  } finally {
    await browser.close();
  }
})().catch(error => {console.error(error); process.exitCode = 1;});
