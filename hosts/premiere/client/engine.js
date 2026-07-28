/*
 * YT7th engine client for the Premiere CEP panel (Node.js context).
 *
 * Mirrors hosts/common/engine_client.py: find the running engine via its
 * state file, health-check it, launch the bundled engine binary if needed,
 * and drive jobs over the token-guarded 127.0.0.1 HTTP daemon.
 *
 * Pure Node (http/fs/os/child_process) with no CEP/Adobe globals, so it is
 * unit-testable outside Premiere. The CEP panel passes in the extension path.
 */
'use strict';

const http = require('http');
const fs = require('fs');
const os = require('os');
const path = require('path');
const cp = require('child_process');

const TOKEN_HEADER = 'x-yt7th-token';
const TERMINAL = ['done', 'error', 'cancelled'];

function appDataDir() {
  if (process.platform === 'win32') {
    return path.join(process.env.APPDATA || os.homedir(), 'YT7th');
  }
  if (process.platform === 'darwin') {
    return path.join(os.homedir(), 'Library', 'Application Support', 'YT7th');
  }
  const base = process.env.XDG_DATA_HOME || path.join(os.homedir(), '.local', 'share');
  return path.join(base, 'YT7th');
}

// YT7TH_STATE lets tests point at a temp state file (mirrors the Python tests).
function statePath() {
  return process.env.YT7TH_STATE || path.join(appDataDir(), 'engine.json');
}

function readState() {
  try {
    return JSON.parse(fs.readFileSync(statePath(), 'utf8'));
  } catch (e) {
    return null;
  }
}

function baseUrl(state) {
  return 'http://127.0.0.1:' + state.port;
}

// Low-level JSON request. Returns a Promise of the parsed body.
function request(base, token, method, urlPath, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(base + urlPath);
    const data = body != null ? Buffer.from(JSON.stringify(body)) : null;
    const headers = {};
    if (token) headers[TOKEN_HEADER] = token;
    if (data) {
      headers['content-type'] = 'application/json';
      headers['content-length'] = data.length;
    }
    const req = http.request(
      { hostname: u.hostname, port: u.port, path: u.pathname + u.search,
        method: method, headers: headers, timeout: 15000 },
      (res) => {
        let chunks = '';
        res.on('data', (c) => (chunks += c));
        res.on('end', () => {
          let parsed = {};
          try { parsed = chunks ? JSON.parse(chunks) : {}; } catch (e) {}
          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(parsed);
          } else {
            reject(new Error(parsed.error || ('HTTP ' + res.statusCode)));
          }
        });
      });
    req.on('error', reject);
    req.on('timeout', () => req.destroy(new Error('request timed out')));
    if (data) req.write(data);
    req.end();
  });
}

function health(base) {
  return request(base, null, 'GET', '/health', null)
    .then((b) => b).catch(() => null);
}

class EngineClient {
  constructor(base, token) {
    this.base = base.replace(/\/$/, '');
    this.token = token;
  }
  submit(url, settings) {
    return request(this.base, this.token, 'POST', '/jobs',
                   { url: url, settings: settings || {} });
  }
  getJob(id) {
    return request(this.base, this.token, 'GET', '/jobs/' + id, null);
  }
  listJobs() {
    return request(this.base, this.token, 'GET', '/jobs', null)
      .then((b) => b.jobs || []);
  }
  cancel(id) {
    return request(this.base, this.token, 'DELETE', '/jobs/' + id, null);
  }
}

// argv to launch the engine, or null if none is known.
function launchCommand(extensionPath) {
  if (process.env.YT7TH_ENGINE_CMD) {
    // naive split is fine for our controlled command
    const parts = process.env.YT7TH_ENGINE_CMD.split(' ').filter(Boolean);
    return parts;
  }
  const roots = [];
  if (extensionPath) roots.push(extensionPath);
  roots.push(path.join(__dirname, '..'));      // hosts/premiere
  let names;
  if (process.platform === 'win32') {
    names = ['YT7th.exe'];
  } else if (process.platform === 'darwin') {
    names = [path.join('YT7th.app', 'Contents', 'MacOS', 'YT7th'), 'YT7th'];
  } else {
    names = ['YT7th'];
  }
  for (const root of roots) {
    for (const name of names) {
      const candidate = path.join(root, 'engine', name);
      if (fs.existsSync(candidate)) return [candidate, '--serve'];
    }
  }
  return null;
}

function spawnEngine(argv) {
  const child = cp.spawn(argv[0], argv.slice(1), {
    detached: true, stdio: 'ignore',
    windowsHide: true,
  });
  child.unref();
}

function delay(ms) { return new Promise((r) => setTimeout(r, ms)); }

// Find or launch the engine; resolves to an EngineClient.
async function connect(extensionPath, timeoutMs) {
  timeoutMs = timeoutMs || 20000;
  let state = readState();
  if (state && (await health(baseUrl(state)))) {
    return new EngineClient(baseUrl(state), state.token);
  }
  const argv = launchCommand(extensionPath);
  if (!argv) {
    throw new Error(
      'YT7th engine is not running and no launcher was found. Start the ' +
      'YT7th app, or set YT7TH_ENGINE_CMD to the engine command.');
  }
  spawnEngine(argv);
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    state = readState();
    if (state && (await health(baseUrl(state)))) {
      return new EngineClient(baseUrl(state), state.token);
    }
    await delay(250);
  }
  throw new Error('YT7th engine did not start in time.');
}

// Submit -> poll -> resolve with the final job dict. Reports progress via
// onStatus(text). Terminal handling matches hosts/common/job_runner.py.
async function runJob(client, url, settings, onStatus, pollMs) {
  pollMs = pollMs || 1000;
  const status = (t) => { if (onStatus) onStatus(t); };
  status('Fetching video info...');
  let job = await client.submit(url, settings);
  while (TERMINAL.indexOf(job.status) === -1) {
    await delay(pollMs);
    job = await client.getJob(job.id);
    if (job.status === 'downloading') {
      status('Downloading ' + (job.title || '') + ' ' +
             Math.round(job.percent || 0) + '%');
    } else if (job.status === 'processing') {
      status('Processing...');
    }
  }
  return job;
}

module.exports = {
  appDataDir, statePath, readState, baseUrl, request, health,
  EngineClient, launchCommand, spawnEngine, connect, runJob, TERMINAL,
};
