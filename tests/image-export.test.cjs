const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Exercise the production helper without loading a model, ads or the full UI.
function loadHelper(file) {
  const html = fs.readFileSync(path.join(__dirname, '..', file), 'utf8');
  const start = html.indexOf('    function fileExtensionFor(');
  assert.notEqual(start, -1, `${file}: fileExtensionFor is missing`);
  const compositeStart = html.indexOf('    function compositeBlob(', start);
  assert.notEqual(compositeStart, -1, `${file}: compositeBlob is missing`);
  const rest = html.slice(compositeStart);
  const end = rest.slice(1).search(/\n    (?:async )?function /);
  assert.notEqual(end, -1, `${file}: could not locate the next helper`);
  const source = html.slice(start, compositeStart + end + 1);
  const calls = { created: 0, revoked: 0, fills: [], mime: null, width: 0, height: 0 };
  const context = {
    fillStyle: '',
    fillRect() { calls.fills.push(this.fillStyle); },
    drawImage() {},
  };
  const canvas = {
    width: 0,
    height: 0,
    getContext() { return context; },
    toBlob(callback, mime) {
      calls.mime = mime;
      calls.width = this.width;
      calls.height = this.height;
      callback({ type: mime });
    },
  };
  class ImageMock {
    constructor() { this.naturalWidth = 320; this.naturalHeight = 200; }
    set src(value) { this.onload(); }
  }
  const sandbox = {
    Image: ImageMock,
    URL: {
      createObjectURL() { calls.created++; return 'blob:test'; },
      revokeObjectURL() { calls.revoked++; },
    },
    document: { createElement(name) { assert.equal(name, 'canvas'); return canvas; } },
  };
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox);
  return { extensionFor: sandbox.fileExtensionFor, run: sandbox.compositeBlob, calls };
}

for (const file of ['index.html', 'it.html', 'fr.html']) {
  test(`${file}: transparent PNG retains original blob`, async () => {
    const { run, calls } = loadHelper(file);
    const input = { type: 'image/png' };
    assert.equal(await run(input, '', 'png'), input);
    assert.equal(calls.created, 0);
  });

  test(`${file}: filenames follow the actual encoded MIME type`, () => {
    const { extensionFor } = loadHelper(file);
    assert.equal(extensionFor({ type: 'image/png' }, 'webp'), 'png');
    assert.equal(extensionFor({ type: 'image/jpeg' }, 'png'), 'jpg');
    assert.equal(extensionFor({ type: 'image/webp' }, 'png'), 'webp');
  });

  for (const [format, mime] of [['png', 'image/png'], ['jpg', 'image/jpeg'], ['webp', 'image/webp']]) {
    test(`${file}: ${format} with white background uses the correct encoder`, async () => {
      const { run, calls } = loadHelper(file);
      const output = await run({ type: 'image/png' }, '#ffffff', format);
      assert.equal(output.type, mime);
      assert.equal(calls.mime, mime);
      assert.deepEqual(calls.fills, ['#ffffff']);
      assert.equal(calls.width, 320);
      assert.equal(calls.height, 200);
      assert.equal(calls.created, calls.revoked);
    });
  }

  test(`${file}: JPEG without a chosen fill gets white rather than black`, async () => {
    const { run, calls } = loadHelper(file);
    await run({ type: 'image/png' }, '', 'jpg');
    assert.deepEqual(calls.fills, ['#ffffff']);
  });

  test(`${file}: explicit custom fill is retained`, async () => {
    const { run, calls } = loadHelper(file);
    await run({ type: 'image/png' }, '#123456', 'jpg');
    assert.deepEqual(calls.fills, ['#123456']);
  });

  test(`${file}: transparent WebP is not flattened`, async () => {
    const { run, calls } = loadHelper(file);
    await run({ type: 'image/png' }, '', 'webp');
    assert.equal(calls.mime, 'image/webp');
    assert.deepEqual(calls.fills, []);
  });
}
