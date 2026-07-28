/*
 * YT7th Premiere panel logic (CEP browser context with Node enabled).
 *
 * UI -> engine client (engine.js) -> ExtendScript import (host/index.jsx).
 * All engine/HTTP logic lives in engine.js (unit-tested); this file is the
 * thin glue that can only run inside Premiere.
 */
'use strict';

(function () {
  var path = require('path');
  var cs = new CSInterface();
  var extRoot = cs.getSystemPath(SystemPath.EXTENSION);
  var engine = require(path.join(extRoot, 'client', 'engine.js'));

  var QUALITIES = ['Best', '2160p', '1440p', '1080p', '720p', '480p', '360p'];
  var VIDEO_FORMATS = ['MP4', 'MKV', 'WEBM'];
  var AUDIO_FORMATS = ['MP3', 'M4A'];

  var $ = function (id) { return document.getElementById(id); };
  var statusEl = $('status');
  var btn = $('download');

  function setStatus(text, isError) {
    statusEl.textContent = text;
    statusEl.className = 'status' + (isError ? ' error' : '');
  }

  function fill(sel, values) {
    sel.innerHTML = '';
    values.forEach(function (v) {
      var o = document.createElement('option');
      o.value = v; o.textContent = v;
      sel.appendChild(o);
    });
  }

  fill($('quality'), QUALITIES);
  $('quality').value = '1080p';
  fill($('format'), VIDEO_FORMATS);

  $('audioOnly').addEventListener('change', function () {
    fill($('format'), this.checked ? AUDIO_FORMATS : VIDEO_FORMATS);
    $('quality').disabled = this.checked;
  });

  // Escape a JS string for embedding inside an evalScript() ExtendScript call.
  function esEscape(s) {
    return String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"');
  }

  function importIntoPremiere(files, append) {
    return new Promise(function (resolve, reject) {
      var pipe = files.join('|');
      var script = 'yt7thImport("' + esEscape(pipe) + '", ' +
                   (append ? 'true' : 'false') + ')';
      cs.evalScript(script, function (res) {
        if (res && res.indexOf('error:') === 0) reject(new Error(res.slice(6)));
        else resolve(res);
      });
    });
  }

  async function onDownload() {
    var url = $('url').value.trim();
    if (!url) { setStatus('Paste a URL first.', true); return; }

    var settings = {
      quality: $('quality').value,
      format: $('format').value,
      audio_only: $('audioOnly').checked,
    };
    var append = $('append').checked;

    btn.disabled = true;
    setStatus('Starting engine...');
    try {
      var client = await engine.connect(extRoot);
      var job = await engine.runJob(client, url, settings, function (s) {
        setStatus(s);
      });

      if (job.status === 'error') { setStatus('Error: ' + job.error, true); return; }
      if (job.status === 'cancelled') { setStatus('Cancelled.'); return; }

      var files = (job.files && job.files.length) ? job.files
                 : (job.filepath ? [job.filepath] : []);
      if (!files.length) { setStatus('No file was produced.', true); return; }

      setStatus('Importing into Premiere...');
      await importIntoPremiere(files, append);
      setStatus('Done. Imported ' + files.length + ' file(s)' +
                (append ? ' and appended to the sequence.' : '.'));
      $('url').value = '';
    } catch (e) {
      setStatus('Error: ' + (e && e.message ? e.message : e), true);
    } finally {
      btn.disabled = false;
    }
  }

  btn.addEventListener('click', onDownload);
  $('url').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') onDownload();
  });
})();
