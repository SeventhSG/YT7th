/*
 * Node unit tests for the Premiere engine client.
 * Run: node --test hosts/premiere/client/engine.test.js
 *
 * Spins a fake engine HTTP server (same contract as yt7th_engine.server),
 * points the client's state file at a temp file, and drives the flow.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');

const engine = require('./engine.js');

const TOKEN = 'testtoken';

function startFakeEngine() {
  let poll = 0;
  const server = http.createServer((req, res) => {
    const send = (code, obj) => {
      const b = JSON.stringify(obj);
      res.writeHead(code, { 'content-type': 'application/json' });
      res.end(b);
    };
    const authed = req.headers['x-yt7th-token'] === TOKEN;

    if (req.url === '/health') return send(200, { ok: true, version: '9.9', jobs: 0 });
    if (!authed) return send(401, { error: 'unauthorized' });

    if (req.method === 'POST' && req.url === '/jobs') {
      let body = '';
      req.on('data', (c) => (body += c));
      req.on('end', () => {
        const parsed = JSON.parse(body || '{}');
        send(201, { id: 1, url: parsed.url, status: 'queued', percent: 0,
                    title: 'V', files: [], filepath: '', error: '' });
      });
      return;
    }
    if (req.method === 'GET' && req.url === '/jobs/1') {
      poll += 1;
      if (poll === 1) {
        return send(200, { id: 1, status: 'downloading', percent: 50,
                           title: 'V', files: [], filepath: '', error: '' });
      }
      return send(200, { id: 1, status: 'done', percent: 100, title: 'V',
                         files: ['/fake/clip.mp4'], filepath: '/fake/clip.mp4',
                         error: '' });
    }
    if (req.method === 'DELETE' && req.url === '/jobs/1') return send(200, { ok: true });
    send(404, { error: 'not found' });
  });
  return new Promise((resolve) => {
    server.listen(0, '127.0.0.1', () => resolve(server));
  });
}

function withTempState(port, token) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'yt7th-'));
  const statePath = path.join(dir, 'engine.json');
  fs.writeFileSync(statePath, JSON.stringify({ port, token, pid: 123 }));
  process.env.YT7TH_STATE = statePath;
  return () => { try { fs.rmSync(dir, { recursive: true, force: true }); } catch (e) {} };
}

test('connect reuses a healthy engine from the state file', async () => {
  const server = await startFakeEngine();
  const port = server.address().port;
  const cleanup = withTempState(port, TOKEN);
  try {
    const client = await engine.connect(null, 3000);
    assert.strictEqual(client.token, TOKEN);
    assert.ok(client.base.endsWith(':' + port));
  } finally {
    cleanup(); server.close();
  }
});

test('submit + runJob polls to done and returns files', async () => {
  const server = await startFakeEngine();
  const port = server.address().port;
  const cleanup = withTempState(port, TOKEN);
  try {
    const client = new engine.EngineClient('http://127.0.0.1:' + port, TOKEN);
    const seen = [];
    const job = await engine.runJob(client, 'https://youtu.be/x',
                                    { quality: '720p' }, (s) => seen.push(s), 20);
    assert.strictEqual(job.status, 'done');
    assert.deepStrictEqual(job.files, ['/fake/clip.mp4']);
    assert.ok(seen.some((s) => s.indexOf('Downloading') === 0));
  } finally {
    cleanup(); server.close();
  }
});

test('bad token is rejected', async () => {
  const server = await startFakeEngine();
  const port = server.address().port;
  try {
    const client = new engine.EngineClient('http://127.0.0.1:' + port, 'wrong');
    await assert.rejects(() => client.listJobs());
  } finally {
    server.close();
  }
});

test('launchCommand finds a bundled engine binary', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'yt7th-ext-'));
  const name = process.platform === 'win32' ? 'YT7th.exe' : 'YT7th';
  fs.mkdirSync(path.join(dir, 'engine'), { recursive: true });
  const bin = process.platform === 'darwin'
    ? path.join(dir, 'engine', 'YT7th.app', 'Contents', 'MacOS', 'YT7th')
    : path.join(dir, 'engine', name);
  fs.mkdirSync(path.dirname(bin), { recursive: true });
  fs.writeFileSync(bin, 'x');
  delete process.env.YT7TH_ENGINE_CMD;
  const argv = engine.launchCommand(dir);
  assert.ok(argv && argv[argv.length - 1] === '--serve');
  assert.ok(argv[0].indexOf('engine') !== -1);
  fs.rmSync(dir, { recursive: true, force: true });
});

test('launchCommand returns null when nothing is available', () => {
  delete process.env.YT7TH_ENGINE_CMD;
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'yt7th-empty-'));
  const argv = engine.launchCommand(dir);
  assert.strictEqual(argv, null);
  fs.rmSync(dir, { recursive: true, force: true });
});
