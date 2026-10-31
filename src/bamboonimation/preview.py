"""A dependency-free timeline preview served only on IPv4 loopback."""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib
import json
import math
from pathlib import Path
import secrets
import sys
import threading
import time
import traceback
from urllib.parse import parse_qs, urlsplit
import webbrowser

import skia
from .render import frame, frame_rate, _dimensions


_HTML = '''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bamboonimation preview</title>
<style>
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#34313d;background:#f4eee3}*{box-sizing:border-box}body{margin:0;padding:32px;max-width:1440px;margin-inline:auto}header{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}h1{font-family:Georgia,serif;font-size:32px;font-weight:500;margin:0}header span{color:#726b77;font-size:14px}main{background:#dfd8ce;border-radius:14px;padding:12px;box-shadow:0 14px 50px #39314012}figure{margin:0;display:flex;align-items:center;justify-content:center;min-height:220px;background:repeating-conic-gradient(#e8e4de 0% 25%,#f5f2ed 0% 50%) 50%/20px 20px;border-radius:8px;overflow:hidden}img{display:block;width:100%;height:auto;max-height:76vh;object-fit:contain}.controls{display:flex;align-items:center;gap:16px;padding:20px 8px 8px}button{border:0;border-radius:8px;padding:10px 18px;color:white;background:#4c5861;font:inherit;cursor:pointer;min-width:88px}button:focus-visible,input:focus-visible{outline:3px solid #d29657;outline-offset:3px}input{flex:1;accent-color:#b56d45;min-width:30px}output{font-variant-numeric:tabular-nums;white-space:nowrap;font-size:14px}p{font-size:14px;color:#726b77;margin-top:18px}#status{color:#a34b37;min-height:1.5em;white-space:pre-wrap;font-family:ui-monospace,monospace}@media(max-width:640px){body{padding:16px}header{display:block}h1{margin-bottom:8px}.controls{flex-wrap:wrap;gap:8px}input{min-width:50%}}
</style>
<header><h1>Bamboonimation</h1><span>Timeline preview</span></header>
<main><figure><img id="image" alt="Current animation frame"></figure><div class="controls"><button id="play" type="button" aria-label="Play animation">Play</button><input id="scrub" type="range" min="0" max="__DURATION__" step="0.001" value="0" aria-label="Timeline position"><output id="clock">0.00 / __DURATION__ s</output></div></main>
<p>__HINT__ Space plays or pauses. Left/Right step one frame, Shift+Left/Right one second, Home/End jump to the ends.</p><p id="status" role="status"></p>
<script>
let duration=__DURATION__;const token=__TOKEN__,fps=__FPS__,live=__LIVE__;
const img=document.getElementById('image'),slider=document.getElementById('scrub'),play=document.getElementById('play'),clock=document.getElementById('clock'),status=document.getElementById('status');
let running=false,time=0,origin=0,busy=false,pending=null,lastURL=null,version=null,reloadError='';
function update(){slider.value=time;clock.textContent=time.toFixed(2)+' / '+duration.toFixed(2)+' s · frame '+Math.round(time*fps);}
async function draw(t){pending=t;if(busy)return;busy=true;while(pending!==null){const requested=pending;pending=null;try{const response=await fetch('/'+token+'/frame?t='+requested.toFixed(5));if(!response.ok)throw new Error(await response.text());const blob=await response.blob();const url=URL.createObjectURL(blob);img.src=url;if(lastURL)URL.revokeObjectURL(lastURL);lastURL=url;status.textContent=reloadError;}catch(error){status.textContent=error.message;pause();pending=null;}}busy=false;}
function pause(){running=false;play.textContent='Play';play.setAttribute('aria-label','Play animation');}
function toggle(){if(running){pause();return;}if(time>=duration)time=0;running=true;origin=performance.now()-time*1000;play.textContent='Pause';play.setAttribute('aria-label','Pause animation');requestAnimationFrame(tick);}
function tick(now){if(!running)return;time=Math.min(duration,(now-origin)/1000);update();draw(time);if(time>=duration)pause();else requestAnimationFrame(tick);}
function seek(t){pause();time=Math.max(0,Math.min(duration,t));update();draw(time);}
function step(frames){seek((Math.round(time*fps)+frames)/fps);}
async function poll(){try{const response=await fetch('/'+token+'/state');if(!response.ok)return;const state=await response.json();if(state.version===version)return;const first=version===null;version=state.version;reloadError=state.error?'Reload failed, still showing the previous version:\\n'+state.error:'';status.textContent=reloadError;if(first||state.error)return;duration=state.duration;slider.max=duration;time=Math.min(time,duration);update();draw(time);}catch(error){}}
play.addEventListener('click',toggle);slider.addEventListener('input',()=>{pause();time=Number(slider.value);update();draw(time);});
document.addEventListener('keydown',event=>{
if(event.code==='Space'&&event.target!==slider&&event.target!==play){event.preventDefault();toggle();return;}
const keys={ArrowLeft:event.shiftKey?-Math.round(fps):-1,ArrowRight:event.shiftKey?Math.round(fps):1};
if(event.code in keys){event.preventDefault();step(keys[event.code]);}
else if(event.code==='Home'){event.preventDefault();seek(0);}
else if(event.code==='End'){event.preventDefault();seek(duration);}});
update();draw(0);if(live){poll();setInterval(poll,700);}
</script></html>'''


def _describe(exc):
    return f"{type(exc).__name__}: {exc}"


def _forget_local_modules(directory):
    """Drop helper modules imported from the scene's folder so edits reload too."""
    for name, module in list(sys.modules.items()):
        file = getattr(module, "__file__", None)
        if not file or name.split(".")[0] == "bamboonimation":
            continue
        try:
            if Path(file).resolve().parent == directory:
                del sys.modules[name]
        except (OSError, ValueError):
            pass


class _LiveScene:
    """The current scene, reloaded when a .py file next to its source changes.

    A failed reload keeps the last working scene and reports the error, so a
    half-saved file never takes the preview down. Callers hold ``lock``.
    """
    def __init__(self, scene, source, width, height, supersample):
        self.lock = threading.Lock()
        self.scene, self.width, self.height, self.supersample = scene, width, height, supersample
        self.size = self._size(scene)
        self.source = Path(source).resolve() if source is not None else None
        self.version, self.error = 1, None
        self._stamp = self._snapshot()
        self._checked = time.monotonic()

    def _size(self, scene):
        if not math.isfinite(scene.duration) or scene.duration <= 0:
            raise ValueError("Scene duration must be positive and finite")
        width, height = self.width, self.height
        if width is None and height is None:
            ratio = min(1, 960 / scene.width, 540 / scene.height)
            width, height = max(1, round(scene.width * ratio)), max(1, round(scene.height * ratio))
        return _dimensions(scene, width, height, self.supersample)

    def _snapshot(self):
        if self.source is None:
            return None
        stamp = {}
        for path in self.source.parent.glob("*.py"):
            try:
                stamp[path] = path.stat().st_mtime_ns
            except OSError:
                pass
        return stamp

    def refresh(self):
        if self.source is None or time.monotonic() - self._checked < .25:
            return
        self._checked = time.monotonic()
        stamp = self._snapshot()
        if stamp == self._stamp:
            return
        self._stamp = stamp
        from .cli import load_scene
        _forget_local_modules(self.source.parent)
        importlib.invalidate_caches()
        try:
            scene = load_scene(self.source)
            size = self._size(scene)
        except Exception as exc:
            self.error = _describe(exc)
            print(f"Reload failed; keeping the previous scene.\n{traceback.format_exc()}", file=sys.stderr, flush=True)
        else:
            self.scene, self.size, self.error = scene, size, None
            print(f"Reloaded {self.source.name}", flush=True)
        self.version += 1


def make_server(scene, *, port=0, width=None, height=None, supersample=1, fps=24, source=None):
    """Return an unstarted server for embedding; routes expose frames only.

    A random route token and strict Host header prevent cross-origin websites
    from guessing a frame endpoint or using DNS rebinding to access the server.
    No filesystem routes or upload/code-execution endpoints are exposed. With
    ``source`` (the scene's trusted file), saving any .py file in its folder
    reloads the scene; the page picks up the new version automatically.
    """
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer in [0, 65535]")
    fps = frame_rate(fps)
    holder = _LiveScene(scene, source, width, height, supersample)
    token = secrets.token_urlsafe(24)
    hint = ("Save any .py file in the scene's folder to reload the preview." if source is not None
            else "Restart the preview to load your changes.")
    html = (_HTML.replace("__DURATION__", str(scene.duration)).replace("__TOKEN__", json.dumps(token))
            .replace("__FPS__", json.dumps(float(fps))).replace("__LIVE__", json.dumps(source is not None))
            .replace("__HINT__", hint).encode())
    reported = set()

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
            if url.path == f"/{token}/state":
                with holder.lock:
                    holder.refresh()
                    state = {"version": holder.version, "duration": holder.scene.duration, "error": holder.error}
                self.respond(200, json.dumps(state).encode(), "application/json")
                return
            if url.path == f"/{token}/frame":
                try:
                    t = float(parse_qs(url.query).get("t", ["0"])[0])
                except ValueError:
                    self.respond(400, b"Frame time must be a number", "text/plain")
                    return
                with holder.lock:
                    holder.refresh()
                    current, (w, h) = holder.scene, holder.size
                    if not math.isfinite(t) or not 0 <= t <= current.duration:
                        self.respond(400, f"Frame time must be within [0, {current.duration}]".encode(), "text/plain; charset=utf-8")
                        return
                    try:
                        image = frame(current, t, width=w, height=h, supersample=supersample)
                        png = bytes(image.encodeToData(skia.kPNG, 100))
                    except Exception as exc:
                        # The scene is the author's own trusted code: show the cause in
                        # the page and the full traceback once in the terminal.
                        message = _describe(exc)
                        if message not in reported:
                            reported.add(message)
                            print(f"Scene drawing failed at t={t:.3f}s\n{traceback.format_exc()}", file=sys.stderr, flush=True)
                        self.respond(500, f"Scene drawing failed at t={t:.3f}s: {message}".encode(), "text/plain; charset=utf-8")
                        return
                self.respond(200, png, "image/png")
                return
            self.respond(404, b"Not found", "text/plain")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.preview_url = f"http://127.0.0.1:{server.server_port}/{token}/"
    return server


def serve(scene, *, port=0, width=None, height=None, supersample=1, open_browser=True, fps=24, source=None):
    server = make_server(scene, port=port, width=width, height=height, supersample=supersample, fps=fps, source=source)
    print(f"Preview: {server.preview_url}", flush=True)
    if source is not None:
        print(f"Watching .py files in {Path(source).resolve().parent} for changes.", flush=True)
    print("Press Ctrl+C to stop. Preview is not a realtime performance benchmark.", flush=True)
    if open_browser:
        webbrowser.open(server.preview_url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
