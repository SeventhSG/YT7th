"""Localhost HTTP daemon wrapping a single QueueManager.

The shared substrate every editor-host plugin talks to. Bound to 127.0.0.1
and guarded by a per-run token, so only local processes that can read the
state file (same user) may drive it.

Endpoints (all JSON):
    GET    /health          -> {ok, version, jobs}
    POST   /jobs            body {url, settings?} -> job
    GET    /jobs            -> {jobs: [...]}
    GET    /jobs/{id}       -> job
    DELETE /jobs/{id}       -> {ok}

A "job" mirrors a QueueItem:
    {id, url, status, percent, speed, eta, title, channel,
     is_playlist, files, filepath, error}
"""
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import data
from .queue_manager import QueueManager

try:
    from version import __version__
except Exception:  # noqa: BLE001 - version module optional in some contexts
    __version__ = "0.0.0"

TOKEN_HEADER = "X-YT7th-Token"


def _job_json(item):
    p = item.progress or {}
    meta = item.metadata or {}
    return {
        "id": item.id,
        "url": item.url,
        "status": item.status,
        "percent": round(p.get("percent", 0) or 0, 1),
        "speed": p.get("speed", 0) or 0,
        "eta": p.get("eta", 0) or 0,
        "title": meta.get("title") or p.get("title", ""),
        "channel": meta.get("channel", ""),
        "is_playlist": meta.get("is_playlist", False),
        "files": list(item.files),
        "filepath": item.files[0] if item.files else "",
        "error": item.error,
    }


class EngineServer:
    """Owns the QueueManager and the HTTP server. Thread-safe; the queue
    already serializes its own state behind a lock.
    """

    def __init__(self, host="127.0.0.1", port=0, token=None, manager=None,
                 on_file_done=None):
        self.host = host
        self.token = token or secrets.token_hex(16)
        self.manager = manager or QueueManager(
            on_file_done=on_file_done or data.add_history,
        )
        handler = _make_handler(self)
        self._httpd = ThreadingHTTPServer((host, port), handler)
        self.port = self._httpd.server_address[1]
        self._thread = None

    @property
    def base_url(self):
        return f"http://{self.host}:{self.port}"

    def serve_forever(self):
        self._httpd.serve_forever()

    def start_background(self):
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()
        return self

    def shutdown(self):
        self._httpd.shutdown()
        self.manager.shutdown()

    # --- request handling (called from handler, already authenticated) ---

    def submit(self, url, settings):
        merged = {**data.load_settings(), **(settings or {})}
        item = self.manager.add(url, merged)
        return _job_json(item)

    def list_jobs(self):
        return [_job_json(i) for i in self.manager.items()]

    def get_job(self, job_id):
        item = next((i for i in self.manager.items() if i.id == job_id), None)
        return _job_json(item) if item else None

    def cancel_job(self, job_id):
        self.manager.remove(job_id)


def _make_handler(server):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):  # silence default stderr logging
            pass

        def _send(self, code, payload):
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authed(self):
            return self.headers.get(TOKEN_HEADER) == server.token

        def _read_body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            try:
                return json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                return None

        def _job_id_from(self, path):
            parts = [p for p in path.split("/") if p]
            if len(parts) == 2 and parts[0] == "jobs" and parts[1].isdigit():
                return int(parts[1])
            return None

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/health":
                self._send(200, {"ok": True, "version": __version__,
                                 "jobs": len(server.manager.items())})
                return
            if not self._authed():
                self._send(401, {"error": "unauthorized"})
                return
            if path == "/jobs":
                self._send(200, {"jobs": server.list_jobs()})
                return
            job_id = self._job_id_from(path)
            if job_id is not None:
                job = server.get_job(job_id)
                if job is None:
                    self._send(404, {"error": "no such job"})
                else:
                    self._send(200, job)
                return
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._authed():
                self._send(401, {"error": "unauthorized"})
                return
            if urlparse(self.path).path != "/jobs":
                self._send(404, {"error": "not found"})
                return
            body = self._read_body()
            if body is None:
                self._send(400, {"error": "invalid JSON"})
                return
            url = (body.get("url") or "").strip()
            if not url:
                self._send(400, {"error": "url is required"})
                return
            self._send(201, server.submit(url, body.get("settings")))

        def do_DELETE(self):
            if not self._authed():
                self._send(401, {"error": "unauthorized"})
                return
            job_id = self._job_id_from(urlparse(self.path).path)
            if job_id is None:
                self._send(404, {"error": "not found"})
                return
            server.cancel_job(job_id)
            self._send(200, {"ok": True})

    return Handler


if __name__ == "__main__":
    from .service import run_server
    run_server()

