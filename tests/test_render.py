from fractions import Fraction
from pathlib import Path
import json
import math
import shutil
import subprocess
import threading
import urllib.error
import urllib.request
import wave

import numpy as np
import pytest
import skia

from bamboonimation import Scene
from bamboonimation.audio import AudioClip, Envelope, viseme
from bamboonimation.cli import load_scene, main
from bamboonimation.preview import make_server
from bamboonimation.render import frame, frame_rate, render, save_frame


def tiny_scene(duration=.4, background="#123456"):
    return Scene(width=64, height=48, duration=duration, background=background,
                 painter=lambda c, t: c.ellipse(16 + t * 60, 24, 8, 8, fill="#f6e3a1"))


def probe(path):
    executable = shutil.which("ffprobe")
    if not executable:
        pytest.skip("ffprobe not installed")
    result = subprocess.run([executable, "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(path)], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def test_rational_fps_and_validation():
    assert frame_rate("24000/1001") == Fraction(24000, 1001)
    assert frame_rate(29.97) == Fraction(2997, 100)
    for invalid in (0, -1, "nan", "inf", "1/0", None):
        with pytest.raises(ValueError):
            frame_rate(invalid)


def test_frame_random_access_and_letterbox(tmp_path):
    scene = tiny_scene()
    first = frame(scene, .1, width=128, height=128).toarray()
    frame(scene, .3)
    second = frame(scene, .1, width=128, height=128).toarray()
    assert np.array_equal(first, second)
    assert np.array_equal(first[0, 0], first[10, 30])
    path = save_frame(scene, tmp_path / "still.png", .1, width=91, height=71, supersample=2)
    image = skia.Image.MakeFromEncoded(path.read_bytes())
    assert (image.width(), image.height()) == (91, 71)
    with pytest.raises(FileExistsError):
        save_frame(scene, path)


def test_render_metadata_exact_rational_and_refuse_overwrite(tmp_path):
    output = tmp_path / "tiny.mp4"
    report = render(tiny_scene(), output, fps="24000/1001")
    assert report.frames == 10
    assert report.fps == "24000/1001"
    assert report.duration == pytest.approx(10 * 1001 / 24000)
    video = probe(output)["streams"][0]
    assert int(video["nb_read_frames"]) == 10
    assert video["r_frame_rate"] == "24000/1001"
    assert (video["width"], video["height"]) == (64, 48)
    sidecar = json.loads(output.with_suffix(".mp4.json").read_text())
    assert sidecar["output"] == "tiny.mp4"
    assert str(tmp_path) not in json.dumps(sidecar)
    previous = output.read_bytes()
    with pytest.raises(FileExistsError):
        render(tiny_scene(), output)
    assert output.read_bytes() == previous


def test_invalid_render_leaves_no_output(tmp_path):
    target = tmp_path / "bad.mp4"
    for kwargs in ({"fps": 0}, {"width": 63}, {"end": 2}, {"start": -.1}, {"transparent": True}, {"threads": 0}):
        with pytest.raises(ValueError):
            render(tiny_scene(), target, **kwargs)
        assert not target.exists()
    assert not list(tmp_path.iterdir())


def test_painter_failure_preserves_existing_output(tmp_path):
    output = tmp_path / "previous.mp4"
    output.write_bytes(b"existing-content")
    def broken(c, t):
        if t >= .1:
            raise ValueError("bad drawing")
    scene = Scene(width=64, height=48, duration=.3, painter=broken)
    with pytest.raises((ValueError, RuntimeError)):
        render(scene, output, overwrite=True, fps=10)
    assert output.read_bytes() == b"existing-content"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["previous.mp4"]


def test_painter_failure_stops_encoder_launcher_and_child(tmp_path, monkeypatch):
    """A launcher must not leave an encoder child alive with the output open."""
    import importlib
    import sys
    import time
    import psutil

    renderer = importlib.import_module("bamboonimation.render")
    helper = tmp_path / "encoder_launcher.py"
    ready = tmp_path / "encoder-ready.json"
    helper.write_text(
        "import json, os, subprocess, sys, time\n"
        "from pathlib import Path\n"
        "if sys.argv[1] == '--child':\n"
        "    with open(sys.argv[-1], 'wb') as output:\n"
        "        ready = Path(sys.argv[2])\n"
        "        pending = ready.with_suffix('.pending')\n"
        "        pending.write_text(json.dumps({'parent': os.getppid(), 'child': os.getpid()}))\n"
        "        pending.replace(ready)\n"
        "        while sys.stdin.buffer.read(4096):\n"
        "            pass\n"
        "        time.sleep(60)\n"
        "else:\n"
        "    subprocess.Popen([sys.executable, __file__, '--child', sys.argv[1], sys.argv[-1]]).wait()\n",
        encoding="utf-8")
    original_popen = subprocess.Popen

    def launch(command, **kwargs):
        if command[0] == "test-encoder-launcher":
            command = [sys.executable, str(helper), str(ready), command[-1]]
        return original_popen(command, **kwargs)

    monkeypatch.setattr(renderer, "ffmpeg_executable", lambda: "test-encoder-launcher")
    monkeypatch.setattr(renderer.subprocess, "Popen", launch)

    def broken(c, t):
        if t >= .1:
            deadline = time.monotonic() + 10
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            assert ready.exists(), "encoder child did not start"
            raise ValueError("bad drawing")

    def running(pid):
        try:
            process = psutil.Process(pid)
            return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
        except psutil.NoSuchProcess:
            return False

    output = tmp_path / "previous.mp4"
    output.write_bytes(b"existing-content")
    try:
        with pytest.raises(ValueError, match="bad drawing"):
            render(Scene(width=64, height=48, duration=.3, painter=broken),
                   output, overwrite=True, fps=10)
        pids = json.loads(ready.read_text())
        deadline = time.monotonic() + 3
        while any(running(pid) for pid in pids.values()) and time.monotonic() < deadline:
            time.sleep(.01)
        assert not any(running(pid) for pid in pids.values())
        assert output.read_bytes() == b"existing-content"
        assert not list(tmp_path.glob(".*.tmp*"))
    finally:
        # Keep a failing regression from leaking the deliberately waiting child.
        if ready.exists():
            for pid in json.loads(ready.read_text()).values():
                if running(pid):
                    psutil.Process(pid).kill()


def test_png_alpha_sequence_and_no_directory_deletion(tmp_path):
    scene = tiny_scene(background=None)
    output = tmp_path / "sequence"
    report = render(scene, output, fps=10, format="png", transparent=True, width=65, height=49)
    assert report.frames == 4
    images = sorted(output.glob("*.png"))
    image = skia.Image.MakeFromEncoded(images[0].read_bytes())
    pixels = image.toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
    assert pixels[0, 0, 3] == 0
    assert pixels[24, 16, 3] == 255
    with pytest.raises(FileExistsError):
        render(scene, output, format="png", overwrite=True)
    assert len(list(output.glob("*.png"))) == 4


def test_audio_clip_export_and_rms(tmp_path):
    audio = tmp_path / "voice.wav"
    rate = 8000
    values = (np.sin(np.arange(rate // 2) * 2 * np.pi * 440 / rate) * 10000).astype("<i2")
    with wave.open(str(audio), "wb") as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes(values.tobytes())
    envelope = Envelope.from_wav(audio)
    assert envelope(.1) > .9
    assert envelope(-1) == 0
    assert envelope(1) == 0
    scene = tiny_scene(duration=.4)
    scene.audio.append(AudioClip(audio, start=.1, volume=.5))
    output = tmp_path / "audio.mp4"
    report = render(scene, output, fps=10, start=.1, end=.4)
    assert report.frames == 3
    streams = probe(output)["streams"]
    assert {stream["codec_type"] for stream in streams} == {"audio", "video"}
    with pytest.raises(ValueError):
        AudioClip(audio, start=-1)
    assert viseme(.15, [(0, "rest"), (.1, "open"), (.2, "rest")]) == "open"


def test_cli_scaffold_and_loader(tmp_path):
    project = tmp_path / "project"
    assert main(["init", str(project)]) == 0
    scene = load_scene(project / "scene.py")
    assert scene.duration == 12
    assert main(["frame", str(project / "scene.py"), "-o", str(tmp_path / "frame.png"), "--width", "160", "--height", "90", "--time", "2"]) == 0
    assert (tmp_path / "frame.png").is_file()
    assert main(["init", str(project)]) == 1


def test_preview_loopback_frame_and_path_security():
    server = make_server(tiny_scene(), width=64, height=48)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert server.server_address[0] == "127.0.0.1"
        with urllib.request.urlopen(server.preview_url) as response:
            assert b"Timeline preview" in response.read()
        with urllib.request.urlopen(server.preview_url + "frame?t=0.1") as response:
            assert response.read().startswith(b"\x89PNG")
        for url in (server.preview_url + "frame?t=nan", server.preview_url + "frame?t=999", server.preview_url + "../../pyproject.toml"):
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(url)
        request = urllib.request.Request(server.preview_url, headers={"Host": "attacker.example"})
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(request)
        assert exc.value.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


@pytest.mark.parametrize("extension,width,height", [("webm", 64, 48), ("mov", 65, 49)])
def test_video_alpha_survives_codec_round_trip(tmp_path, extension, width, height):
    from bamboonimation.render import ffmpeg_executable
    scene = Scene(width=width, height=height, duration=.2, background=None,
                  painter=lambda c, t: c.ellipse(20, 24, 10, 10, fill="#ff0000"))
    output = tmp_path / ("alpha." + extension)
    render(scene, output, fps=10, transparent=True)
    command = [ffmpeg_executable(), "-v", "error"]
    # FFmpeg's native VP9 decoder ignores alpha; libvpx-vp9 decodes both planes.
    if extension == "webm":
        command += ["-c:v", "libvpx-vp9"]
    command += ["-i", str(output), "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgba", "pipe:1"]
    result = subprocess.run(command, capture_output=True, check=True)
    pixels = np.frombuffer(result.stdout, np.uint8).reshape(height, width, 4)
    assert pixels[0, 0, 3] == 0
    assert pixels[24, 20, 3] == 255
    assert pixels[24, 20, 0] >= 250



def test_contain_bars_are_clipped_to_authored_viewport():
    scene = Scene(width=64, height=48, duration=1, background="#123456",
                  painter=lambda c, t: c.rect(-1000, -1000, 2000, 2000, fill="#ff0000"))
    pixels = frame(scene, .1, width=128, height=128).toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
    assert tuple(pixels[0, 64, :3]) == (0x12, 0x34, 0x56)
    assert tuple(pixels[64, 64, :3]) == (255, 0, 0)



def test_impossible_raster_allocation_is_rejected_before_output(tmp_path, monkeypatch):
    import importlib
    renderer = importlib.import_module("bamboonimation.render")
    output = tmp_path / "huge.mp4"
    with pytest.raises(ValueError, match="address limits"):
        render(tiny_scene(), output, width=2**32, height=2**32)
    monkeypatch.setattr(renderer, "_available_memory", lambda: 1024)
    with pytest.raises(ValueError, match="RAM is available"):
        render(tiny_scene(), output, width=1920, height=1080)
    assert not output.exists()
    assert not list(tmp_path.iterdir())



def test_invalid_audio_reports_encoder_error_and_preserves_output(tmp_path):
    invalid = tmp_path / "broken.wav"
    invalid.write_bytes(b"this is not audio")
    scene = tiny_scene()
    scene.audio.append(AudioClip(invalid))
    output = tmp_path / "previous.mp4"
    output.write_bytes(b"previous movie")
    with pytest.raises(RuntimeError, match="FFmpeg"):
        render(scene, output, overwrite=True)
    assert output.read_bytes() == b"previous movie"
    assert not list(tmp_path.glob(".*.tmp*"))



def test_preview_playback_displays_completed_frames_while_next_time_is_pending():
    """Run the shipped UI script with a slow asynchronous network/browser clock.

    Playback must display completed responses even when RAF has queued a newer
    time. Otherwise a renderer slower than the display refresh rate starves.
    """
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is optional; browser preview integration is tested separately")
    from bamboonimation.preview import _HTML
    script = _HTML.split("<script>", 1)[1].split("</script>", 1)[0]
    script = (script.replace("__DURATION__", "12").replace("__TOKEN__", '\"test-token\"')
              .replace("__FPS__", "24").replace("__LIVE__", "false"))
    driver = r"""
const vm = require('node:vm');
const fs = require('node:fs');
const assert = require('node:assert/strict');
const source = JSON.parse(fs.readFileSync(0, 'utf8'));
const elements = {};
for (const id of ['image', 'scrub', 'play', 'clock', 'status']) {
  elements[id] = {handlers:{}, addEventListener(name, fn){this.handlers[name]=fn;},setAttribute(){}};
}
const requests = [], animationFrames = [], displayed = [];
let objectURLs = 0;
Object.defineProperty(elements.image, 'src', {set(value){displayed.push(value);},get(){return displayed.at(-1);}});
vm.runInNewContext(source, {
  document:{getElementById:id=>elements[id],addEventListener(){}},
  performance:{now:()=>0},
  requestAnimationFrame:callback=>animationFrames.push(callback),
  URL:{createObjectURL:()=>`blob:${++objectURLs}`,revokeObjectURL(){}},
  fetch:url=>new Promise(resolve=>requests.push({url,resolve})),
});
(async()=>{
  assert.equal(requests.length,1);
  elements.play.handlers.click();
  animationFrames.shift()(1000);
  animationFrames.shift()(2000);
  requests[0].resolve({ok:true,blob:async()=>({frame:0})});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(displayed.length,1,'Playback must display a completed frame while a newer request is queued');
  assert.equal(requests.length,2,'Coalesced latest time should be requested next');
  assert.ok(requests[1].url.endsWith('t=2.00000'));
  requests[1].resolve({ok:true,blob:async()=>({frame:2})});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(displayed.length,2);
  assert.notEqual(displayed[0],displayed[1]);
})().catch(error=>{console.error(error);process.exitCode=1;});
"""
    result = subprocess.run([node, "-e", driver], input=json.dumps(script), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_supersample_is_an_exact_box_filter():
    # A white column one third of a pixel wide: with supersample=3 exactly one of
    # the three sub-pixel columns is covered, so the pixel must be one-third lit.
    scene = Scene(width=4, height=4, duration=1, background="#000000",
                  painter=lambda c, t: c.rect(0, 0, 1 / 3, 4, fill="#ffffff"))
    for factor, expected in ((2, 128), (3, 85), (4, 128)):
        width = 1 / 2 if factor in (2, 4) else 1 / 3
        scene.painter = lambda c, t, width=width: c.rect(0, 0, width, 4, fill="#ffffff")
        pixels = frame(scene, 0, supersample=factor).toarray(colorType=skia.ColorType.kRGBA_8888_ColorType)
        assert abs(int(pixels[2, 0, 0]) - expected) <= 1, factor
        assert tuple(pixels[2, 1, :3]) == (0, 0, 0)


SCENE_FILE = '''
from bamboonimation import Scene

def paint(c, t):
    c.ellipse(16 + t * 60, 24, 8, 8, fill="#f6e3a1")
    if t > {fail_after}:
        raise ValueError("bad drawing")

scene = Scene(width=64, height=48, duration={duration}, background="#123456", painter=paint)
'''


def write_scene(path, duration=.5, fail_after=99):
    path.write_text(SCENE_FILE.format(duration=duration, fail_after=fail_after), encoding="utf-8")
    return path


def test_parallel_render_matches_serial_frames(tmp_path):
    scene = load_scene(write_scene(tmp_path / "scene.py"))
    serial = render(scene, tmp_path / "serial", format="png", fps=24)
    parallel = render(scene, tmp_path / "parallel", format="png", fps=24, workers=3)
    assert (serial.frames, parallel.frames, parallel.workers) == (12, 12, 3)
    for index in range(12):
        name = f"{index:06d}.png"
        assert (tmp_path / "serial" / name).read_bytes() == (tmp_path / "parallel" / name).read_bytes()


def test_parallel_render_reports_worker_failure_and_keeps_output(tmp_path):
    scene = load_scene(write_scene(tmp_path / "scene.py", fail_after=.2))
    output = tmp_path / "previous.mp4"
    output.write_bytes(b"existing-content")
    with pytest.raises((ValueError, RuntimeError), match="bad drawing"):
        render(scene, output, overwrite=True, fps=24, workers=2)
    assert output.read_bytes() == b"existing-content"
    assert not list(tmp_path.glob(".*.tmp*"))


def test_parallel_render_rejects_unshareable_scene_before_output(tmp_path):
    with pytest.raises(ValueError, match="workers"):
        render(tiny_scene(), tmp_path / "out.mp4", workers=2)
    with pytest.raises(ValueError, match="workers"):
        render(tiny_scene(), tmp_path / "out.mp4", workers=0)
    assert not list(tmp_path.iterdir())


def test_contact_sheet_and_cli(tmp_path):
    from bamboonimation.render import contact_sheet
    path = contact_sheet(tiny_scene(), tmp_path / "sheet.png", [0, .1, .2, .3, .4], cell_width=64, columns=3)
    image = skia.Image.MakeFromEncoded(path.read_bytes())
    # 3 columns x 2 rows of 64x48 cells, an 8 px gap and a 22 px label strip.
    assert (image.width(), image.height()) == (8 + 3 * 72, 8 + 2 * (48 + 22 + 8))
    with pytest.raises(FileExistsError):
        contact_sheet(tiny_scene(), path, [0])
    with pytest.raises(ValueError):
        contact_sheet(tiny_scene(), tmp_path / "bad.png", [5])
    scene_file = write_scene(tmp_path / "scene.py")
    assert main(["sheet", str(scene_file), "-o", str(tmp_path / "every.png"), "--every-frame",
                 "--fps", "12", "--width", "64", "--columns", "6"]) == 0
    image = skia.Image.MakeFromEncoded((tmp_path / "every.png").read_bytes())
    assert (image.width(), image.height()) == (8 + 6 * 72, 8 + 1 * (48 + 22 + 8))


def test_preview_reloads_scene_and_keeps_last_good_version(tmp_path, capsys):
    import os
    import time
    scene_file = write_scene(tmp_path / "scene.py", duration=.5)
    server = make_server(load_scene(scene_file), width=64, height=48, source=scene_file)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def state():
        time.sleep(.3)  # File checks are throttled to four per second.
        with urllib.request.urlopen(server.preview_url + "state") as response:
            return json.loads(response.read())

    def touch_later(path, step):
        stamp = path.stat().st_mtime_ns + step * 10**9
        os.utime(path, ns=(stamp, stamp))

    try:
        assert state() == {"version": 1, "duration": .5, "error": None}
        write_scene(scene_file, duration=2)
        touch_later(scene_file, 1)
        assert state() == {"version": 2, "duration": 2, "error": None}
        with urllib.request.urlopen(server.preview_url + "frame?t=1.5") as response:
            assert response.read().startswith(b"\x89PNG")
        scene_file.write_text("def broken(:\n", encoding="utf-8")
        touch_later(scene_file, 2)
        broken = state()
        assert broken["version"] == 3 and "SyntaxError" in broken["error"] and broken["duration"] == 2
        with urllib.request.urlopen(server.preview_url + "frame?t=1.5") as response:
            assert response.read().startswith(b"\x89PNG")
        write_scene(scene_file, duration=2, fail_after=.1)
        touch_later(scene_file, 3)
        assert state()["error"] is None
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(server.preview_url + "frame?t=1")
        assert exc.value.code == 500 and b"ValueError: bad drawing" in exc.value.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert "Traceback" in capsys.readouterr().err
