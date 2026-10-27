"""A dependency-free timeline preview served only on IPv4 loopback."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import secrets
import threading
from urllib.parse import parse_qs, urlsplit
import webbrowser

import skia
from .render import frame, _dimensions


_HTML = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bamboonimation preview</title>
<style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#34313d;background:#f4eee3}*{box-sizing:border-box}body{margin:0;padding:32px;max-width:1440px;margin-inline:auto}header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}h1{font-family:Georgia,serif;font-size:32px;font-weight:500;margin:0}header span{color:#726b77;font-size:14px}main{background:#dfd8ce;border-radius:14px;padding:12px;box-shadow:0 14px 50px #39314012}figure{margin:0;display:flex;align-items:center;justify-content:center;min-height:220px;background:repeating-conic-gradient(#e8e4de 0% 25%,#f5f2ed 0% 50%) 50%/20px 20px;border-radius:8px;overflow:hidden}img{display:block;width:100%;height:auto;max-height:76vh;object-fit:contain}.controls{display:flex;align-items:center;gap:16px;padding:20px 8px 8px}button{border:0;border-radius:8px;padding:10px 18px;color:white;background:#4c5861;font:inherit;cursor:pointer;min-width:88px}button:focus-visible,input:focus-visible{outline:3px solid #d29657;outline-offset:3px}input{flex:1;accent-color:#b56d45;min-width:30px}output{font-variant-numeric:tabular-nums;white-space:nowrap;font-size:14px}p{font-size:14px;color:#726b77;margin-top:18px}#status{color:#a34b37;min-height:1.5em}@media(max-width:640px){body{padding:16px}header{display:block}h1{margin-bottom:8px}.controls{flex-wrap:wrap;gap:8px}input{min-width:50%}}
</style>
<header><h1>Bamboonimation</h1><span>Timeline preview</span></header>
<main><figure><img id="image" alt="Current animation frame"></figure><div class="controls"><button id="play" type="button" aria-label="Play animation">Play</button><input id="scrub" type="range" min="0" max="__DURATION__" step="0.001" value="0" aria-label="Timeline position"><output id="clock">0.00 / __DURATION__ s</output></div></main>
<p>Edit the scene in your code editor. Restart the preview to load your changes. Space plays or pauses; the slider scrubs to an exact time.</p><p id="status" role="status"></p>
<script>
const duration=__DURATION__,token=__TOKEN__;
const img=document.getElementById('image'),slider=document.getElementById('scrub'),play=document.getElementById('play'),clock=document.getElementById('clock'),status=document.getElementById('status');
let running=false,time=0,origin=0,busy=false,pending=null,lastURL=null;
function update(){slider.value=time;clock.textContent=time.toFixed(2)+' / '+duration.toFixed(2)+' s';}
async function draw(t){pending=t;if(busy)return;busy=true;while(pending!==null){const requested=pending;pending=null;try{const response=await fetch('/'+token+'/frame?t='+requested.toFixed(5));if(!response.ok)throw new Error(await response.text());const blob=await response.blob();const url=URL.createObjectURL(blob);img.src=url;if(lastURL)URL.revokeObjectURL(lastURL);lastURL=url;status.textContent='';}catch(error){status.textContent=error.message;pause();pending=null;}}busy=false;}
function pause(){running=false;play.textContent='Play';play.setAttribute('aria-label','Play animation');}
function toggle(){if(running){pause();return;}if(time>=duration)time=0;running=true;origin=performance.now()-time*1000;play.textContent='Pause';play.setAttribute('aria-label','Pause animation');requestAnimationFrame(tick);}
function tick(now){if(!running)return;time=Math.min(duration,(now-origin)/1000);update();draw(time);if(time>=duration)pause();else requestAnimationFrame(tick);}
play.addEventListener('click',toggle);slider.addEventListener('input',()=>{pause();time=Number(slider.value);update();draw(time);});document.addEventListener('keydown',event=>{if(event.code==='Space'&&event.target!==slider&&event.target!==play){event.preventDefault();toggle();}});update();draw(0);
</script></html>'''


def make_server(scene, *, port=0, width=None, height=None, supersample=1):
    """Return an unstarted server for embedding; routes expose frames only.

    A random route token and strict Host header prevent cross-origin websites
    from guessing a frame endpoint or using DNS rebinding to access the server.
    No filesystem routes or upload/code-execution endpoints are exposed.
    """
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer in [0, 65535]")
    if width is None and height is None:
        ratio = min(1, 960 / scene.width, 540 / scene.height)
        width, height = max(1, round(scene.width * ratio)), max(1, round(scene.height * ratio))
    width, height = _dimensions(scene, width, height, supersample)
    if not math.isfinite(scene.duration) or scene.duration <= 0:
        raise ValueError("Scene duration must be positive and finite")
    token = secrets.token_urlsafe(24)
    html = _HTML.replace("__DURATION__", str(scene.duration)).replace("__TOKEN__", json.dumps(token)).encode()
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, code, data, content_type):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
            if self.headers.get("Host") not in allowed:
                self.respond(403, b"Invalid host", "text/plain")
                return
            url = urlsplit(self.path)
            if url.path in (f"/{token}", f"/{token}/"):
                self.respond(200, html, "text/html; charset=utf-8")
                return
            if url.path == f"/{token}/frame":
                try:
                    t = float(parse_qs(url.query).get("t", ["0"])[0])
                    with lock:
                        image = frame(scene, t, width=width, height=height, supersample=supersample)
                        png = bytes(image.encodeToData(skia.kPNG, 100))
                    self.respond(200, png, "image/png")
                except (ValueError, TypeError) as exc:
                    self.respond(400, str(exc).encode(), "text/plain; charset=utf-8")
                except Exception:
                    self.respond(500, b"Scene drawing failed; inspect the scene code and restart the preview.", "text/plain")
                return
            self.respond(404, b"Not found", "text/plain")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.preview_url = f"http://127.0.0.1:{server.server_port}/{token}/"
    return server


def serve(scene, *, port=0, width=None, height=None, supersample=1, open_browser=True):
    server = make_server(scene, port=port, width=width, height=height, supersample=supersample)
    print(f"Preview: {server.preview_url}", flush=True)
    print("Press Ctrl+C to stop. Preview is not a realtime performance benchmark.", flush=True)
    if open_browser:
        webbrowser.open(server.preview_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
