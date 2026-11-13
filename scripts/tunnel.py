"""Share ONE file at a temporary public HTTPS address using a Cloudflare quick tunnel.

Used by post_instagram.py so Instagram can download a clip from a link (video_url)
instead of us pushing the file to its upload server.

Safety rules:
  - Only a copy of the one file is shared, from an empty temporary folder, under a
    random file name. The repo, .env and everything else are never reachable.
  - The web server answers only GET/HEAD for that exact path; anything else gets 404.
  - The server listens on 127.0.0.1 only, so it's reachable only through the tunnel.
  - The tunnel, server and copy are shut down and deleted on exit, even after an error.

Needs `cloudflared` (brew install cloudflared). No Cloudflare account is required.

Usage:
    with share_file(Path("clip1.mp4"), log) as url:
        ...  # url is live here; Instagram (or anyone with the url) can download the file
"""

import contextlib
import hashlib
import queue
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

CLOUDFLARED_CANDIDATES = ["/opt/homebrew/bin/cloudflared", "/usr/local/bin/cloudflared"]
# api.trycloudflare.com shows up in cloudflared error messages; it is never a tunnel.
URL_PATTERN = re.compile(r"https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com")


class TunnelError(Exception):
    pass


def find_cloudflared():
    path = shutil.which("cloudflared") or next((p for p in CLOUDFLARED_CANDIDATES if Path(p).exists()), None)
    if not path:
        raise TunnelError("cloudflared is not installed. Run: brew install cloudflared")
    return path


def make_handler(served_path, file_path, size):
    class OneFileHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the job's output clean
            pass

        def _headers(self, status, length, extra=None):
            self.send_response(status)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()

        def _not_found(self):
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _serve(self, body):
            if self.path.split("?")[0] != served_path:
                return self._not_found()
            start, end = 0, size - 1
            match = re.match(r"bytes=(\d*)-(\d*)$", self.headers.get("Range", ""))
            if match and (match.group(1) or match.group(2)):
                if match.group(1):
                    start = int(match.group(1))
                    end = int(match.group(2)) if match.group(2) else size - 1
                else:  # suffix range: last N bytes
                    start = max(0, size - int(match.group(2)))
                end = min(end, size - 1)
                if start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                self._headers(206, end - start + 1, {"Content-Range": f"bytes {start}-{end}/{size}"})
            else:
                self._headers(200, size)
            if not body:
                return
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = f.read(min(1 << 20, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    remaining -= len(chunk)

        def do_GET(self):
            self._serve(body=True)

        def do_HEAD(self):
            self._serve(body=False)

        def do_POST(self):
            self._not_found()

    return OneFileHandler


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_url(url, expected_size, expected_hash, timeout=180):
    """Download the file back through the public address and check it matches."""
    deadline = time.time() + timeout
    last_error = None
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "poly_nomial-tunnel-check"})
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            if len(data) == expected_size and hashlib.sha256(data).hexdigest() == expected_hash:
                return
            last_error = f"got {len(data)} bytes, expected {expected_size}"
        except Exception as e:  # DNS for a new tunnel can take a few seconds
            last_error = str(e)
        time.sleep(3)
    raise TunnelError(f"tunnel address never served the file correctly: {last_error}")


@contextlib.contextmanager
def share_file(file_path, log=print):
    file_path = Path(file_path)
    cloudflared = find_cloudflared()
    tmp = Path(tempfile.mkdtemp(prefix="ig-share-"))
    server = proc = None
    try:
        name = f"{secrets.token_urlsafe(24)}.mp4"
        copy = tmp / name
        shutil.copyfile(file_path, copy)
        size, digest = copy.stat().st_size, sha256(copy)

        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(f"/{name}", copy, size))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]

        proc = subprocess.Popen(
            [cloudflared, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # Read cloudflared's output on a background thread (for the whole run, so its
        # pipe never fills up) and wait at most 45s for the tunnel address.
        lines = queue.Queue()
        threading.Thread(target=lambda: [lines.put(l) for l in proc.stdout], daemon=True).start()
        base, seen, deadline = None, [], time.time() + 45
        while not base and time.time() < deadline:
            try:
                line = lines.get(timeout=1)
            except queue.Empty:
                if proc.poll() is not None:
                    break
                continue
            seen.append(line)
            found = URL_PATTERN.search(line)
            if found:
                base = found.group(0)
        if not base:
            raise TunnelError("cloudflared didn't open a tunnel: " + "".join(seen[-5:]).strip()[:300])

        url = f"{base}/{name}"
        log(f"tunnel open: {base}/<random-name>.mp4 ({size / 1e6:.1f} MB); checking it serves the file")
        verify_url(url, size, digest)
        log("tunnel verified: file downloads correctly through the public address")
        yield url
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if server:
            server.shutdown()
            server.server_close()
        shutil.rmtree(tmp, ignore_errors=True)
        log("tunnel closed and temporary copy deleted")
