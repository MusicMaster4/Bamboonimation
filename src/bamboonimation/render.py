"""Bounded-memory raster rendering and atomic FFmpeg exports."""
from __future__ import annotations

from collections import deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
import json
import math
import multiprocessing
import os
import pickle
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
import sys

import numpy as np
import skia

from .drawing import Canvas, _font


def ffmpeg_executable() -> str:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError) as exc:
        raise RuntimeError("FFmpeg unavailable. Install ffmpeg or imageio-ffmpeg.") from exc


def _terminate_encoder(process):
    """Stop the owned encoder tree, including executable launchers/shims."""
    if sys.platform == "win32":
        # Chocolatey and other launchers can keep the real encoder in a child.
        # Killing only the launcher leaves that child holding the temp output.
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait()


def frame_rate(value) -> Fraction:
    try:
        fps = value if isinstance(value, Fraction) else Fraction(str(value))
    except (ValueError, ZeroDivisionError, TypeError, OverflowError) as exc:
        raise ValueError("fps must be a positive number or rational such as 24000/1001") from exc
    if fps <= 0:
        raise ValueError("fps must be positive")
    return fps


def _available_memory():
    """Available physical RAM when discoverable, without an extra dependency."""
    try:
        if sys.platform == "win32":
            import ctypes
            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
                    (name, ctypes.c_ulonglong) for name in
                    ("total_phys", "available_phys", "total_page", "available_page", "total_virtual", "available_virtual", "extended")]
            status = MemoryStatus()
            status.length = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return status.available_phys
        elif hasattr(os, "sysconf"):
            return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE")
    except (AttributeError, OSError, ValueError):
        pass
    return None


def _dimensions(scene, width, height, supersample, workers=1):
    width = scene.width if width is None else width
    height = scene.height if height is None else height
    for name, value in (("width", width), ("height", height), ("supersample", supersample)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    rw, rh = width * supersample, height * supersample
    if rw > 2**31 - 1 or rh > 2**31 - 1 or rw * rh * 4 > sys.maxsize:
        raise ValueError("Raster dimensions exceed Skia/platform address limits; reduce dimensions or supersample")
    # Conservative transient estimate includes previous frame, raw copies and downsampling.
    # Each worker owns its rasters; the ordered queue holds two frames per worker.
    # User painters/asset caches and FFmpeg may need additional RAM beyond this estimate.
    estimated = 4 * workers * (2 * rw * rh + 5 * width * height)
    available = _available_memory()
    if available is not None and estimated > available * .75:
        raise ValueError(f"Requested raster buffers need approximately {estimated / 2**20:.0f} MiB; "
                         f"only {available / 2**20:.0f} MiB RAM is available. Reduce dimensions, supersample or workers.")
    return width, height


def _box_downsample(image, width, height, factor):
    """Average every factor x factor block of premultiplied pixels exactly.

    A single bilinear tap is only a true box filter for factor 2; at 3 it reads
    one sub-pixel and at 4 a quarter of them, discarding the extra coverage.
    """
    pixels = image.toarray(colorType=skia.ColorType.kRGBA_8888_ColorType,
                           alphaType=skia.AlphaType.kPremul_AlphaType)
    count = factor * factor
    total = pixels.reshape(height, factor, width, factor, 4).sum(
        axis=(1, 3), dtype=np.uint16 if count <= 257 else np.uint32)
    averaged = ((total + count // 2) // count).astype(np.uint8)
    return skia.Image.fromarray(averaged, colorType=skia.ColorType.kRGBA_8888_ColorType,
                                alphaType=skia.AlphaType.kPremul_AlphaType)


def frame(scene, t: float, *, width=None, height=None, supersample=1) -> skia.Image:
    """Render at an absolute scene time. Geometry uses scene's logical coordinates.

    Alternate aspect ratios use centered contain (letterboxing), preserving shape.
    The scene background is also used for bars; transparent scenes retain alpha.
    """
    width, height = _dimensions(scene, width, height, supersample)
    if not math.isfinite(t) or t < 0 or t > scene.duration:
        raise ValueError("frame time must be within [0, scene.duration]")
    rw, rh = width * supersample, height * supersample
    surface = skia.Surface(rw, rh)
    if surface is None:
        raise MemoryError(f"Cannot allocate {rw}x{rh} raster surface")
    raw = surface.getCanvas()
    raw.clear(skia.ColorTRANSPARENT)
    background = getattr(scene, "background", None)
    if background is not None:
        from .drawing import color
        raw.clear(color(background))
    raw.scale(supersample, supersample)
    scale = min(width / scene.width, height / scene.height)
    raw.translate((width - scene.width * scale) / 2, (height - scene.height * scale) / 2)
    raw.scale(scale, scale)
    raw.clipRect(skia.Rect.MakeWH(scene.width, scene.height))
    canvas = Canvas(raw, scene.width, scene.height, time=t, seed=scene.seed)
    scene.draw(canvas, t)
    image = surface.makeImageSnapshot()
    if supersample != 1:
        image = _box_downsample(image, width, height, supersample)
    return image


def _png_target(output, overwrite):
    path = Path(output)
    if path.suffix.lower() != ".png":
        raise ValueError("Still frames must use .png")
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {path.name}; pass overwrite=True")
    return path


def _write_png(path, image):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = image.encodeToData(skia.kPNG, 100)
    if data is None:
        raise RuntimeError("PNG encoding failed")
    temp = path.with_name(f".{path.stem}-{uuid.uuid4().hex}.tmp.png")
    try:
        temp.write_bytes(bytes(data))
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)
    return path


def save_frame(scene, output, t=0.0, *, width=None, height=None, supersample=1, overwrite=False):
    path = _png_target(output, overwrite)
    return _write_png(path, frame(scene, t, width=width, height=height, supersample=supersample))


# Worker processes rebuild the scene once, then render frames by absolute time.
# Scenes are pure functions of time, so frame order across workers is irrelevant.
_worker_scene = None


def _init_worker(kind, payload):
    global _worker_scene
    if kind == "pickle":
        _worker_scene = pickle.loads(payload)
    else:
        from .cli import load_scene
        _worker_scene = load_scene(payload)


def _encode(image, encoding):
    if encoding == "png":
        data = image.encodeToData(skia.kPNG, 100)
        if data is None:
            raise RuntimeError("PNG encoding failed")
        return bytes(data)
    return image.toarray(colorType=skia.ColorType.kRGBA_8888_ColorType,
                         alphaType=skia.AlphaType.kUnpremul_AlphaType).tobytes()


def _worker_frame(t, width, height, supersample, encoding):
    return _encode(frame(_worker_scene, t, width=width, height=height, supersample=supersample), encoding)


def _scene_payload(scene):
    """Reload scenes from their file (with its local helper imports), else pickle."""
    source = getattr(scene, "source_file", None)
    if source is not None:
        return "file", str(source)
    try:
        return "pickle", pickle.dumps(scene)
    except Exception:
        pass
    raise ValueError("workers > 1 needs a scene loaded with load_scene() or a picklable scene "
                     "(module-level painter functions, not lambdas); use workers=1 otherwise")


def _check_workers(workers):
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 1:
        raise ValueError("workers must be a positive integer")


def _frames(scene, times, *, width, height, supersample, encoding, workers, payload=None):
    """Yield encoded frames in order, rendering up to ``workers`` at a time."""
    if workers == 1:
        for t in times:
            yield _encode(frame(scene, t, width=width, height=height, supersample=supersample), encoding)
        return
    kind, payload = payload or _scene_payload(scene)
    # Spawn on every platform: forking a process that holds Skia/FFmpeg state is unsafe.
    pool = ProcessPoolExecutor(workers, mp_context=multiprocessing.get_context("spawn"),
                               initializer=_init_worker, initargs=(kind, payload))
    pending = deque()
    remaining = iter(times)
    try:
        def submit():
            for t in remaining:
                pending.append(pool.submit(_worker_frame, t, width, height, supersample, encoding))
                return
        for _ in range(2 * workers):
            submit()
        while pending:
            data = pending.popleft().result()
            submit()
            yield data
    finally:
        for future in pending:
            future.cancel()
        pool.shutdown(wait=True, cancel_futures=True)


def default_workers(frame_count=None):
    """A conservative process count: leave a core free and avoid tiny-job overhead."""
    count = max(1, min(8, (os.cpu_count() or 1) - 1))
    if frame_count is not None:
        # Starting a worker costs roughly one module import; short clips stay serial.
        count = max(1, min(count, frame_count // 12))
    return count


def frame_times(start, end, fps):
    """Exact export sample times: ``start + i/fps`` for every frame in [start, end)."""
    fps = frame_rate(fps)
    count = math.ceil((Fraction(str(end)) - Fraction(str(start))) * fps)
    return [start + float(index / fps) for index in range(count)]


def contact_sheet(scene, output, times, *, cell_width=320, columns=None, fps=24,
                  supersample=1, overwrite=False, workers=1, labels=True):
    """Write a PNG grid of frames at absolute times, labelled with time and frame.

    Frame numbers are ``round(t * fps)``, matching a full export at ``fps``.
    Use it to review an action's consecutive frames or a whole shot at a glance.
    """
    path = _png_target(output, overwrite)
    times = [float(t) for t in times]
    if not times:
        raise ValueError("A contact sheet needs at least one time")
    if len(times) > 400:
        raise ValueError("A contact sheet holds at most 400 frames; narrow the time range")
    if any(not math.isfinite(t) or t < 0 or t > scene.duration for t in times):
        raise ValueError("Contact sheet times must be within [0, scene.duration]")
    if isinstance(cell_width, bool) or not isinstance(cell_width, int) or cell_width < 16:
        raise ValueError("cell_width must be an integer of at least 16 pixels")
    if columns is None:
        columns = min(len(times), max(1, round(math.sqrt(len(times) * 16 / 9 * scene.height / scene.width))))
    if isinstance(columns, bool) or not isinstance(columns, int) or columns < 1:
        raise ValueError("columns must be a positive integer")
    _check_workers(workers)
    fps = frame_rate(fps)
    cell_height = max(1, round(cell_width * scene.height / scene.width))
    width, height = _dimensions(scene, cell_width, cell_height, supersample, workers)
    gap, label = 8, (22 if labels else 0)
    rows = math.ceil(len(times) / columns)
    sheet = skia.Surface(gap + columns * (width + gap), gap + rows * (height + label + gap))
    canvas = sheet.getCanvas()
    canvas.clear(skia.ColorSetRGB(0x2b, 0x29, 0x30))
    ink = skia.Paint(AntiAlias=True, Color=skia.ColorSetRGB(0xe8, 0xe2, 0xd6))
    font = _font(None, 13)
    frames = _frames(scene, times, width=width, height=height, supersample=supersample,
                     encoding="rgba", workers=min(workers, len(times)))
    for index, data in enumerate(frames):
        t = times[index]
        pixels = np.frombuffer(data, np.uint8).reshape(height, width, 4)
        image = skia.Image.fromarray(pixels, colorType=skia.ColorType.kRGBA_8888_ColorType,
                                     alphaType=skia.AlphaType.kUnpremul_AlphaType)
        x = gap + (index % columns) * (width + gap)
        y = gap + (index // columns) * (height + label + gap)
        canvas.drawImage(image, x, y)
        if labels:
            canvas.drawString(f"{t:.3f} s  ·  frame {round(t * fps)}", x + 2, y + height + 16, font, ink)
    return _write_png(path, sheet.makeImageSnapshot())


@dataclass(frozen=True)
class RenderReport:
    output: str
    width: int
    height: int
    fps: str
    frames: int
    start: float
    end: float
    duration: float
    elapsed_seconds: float
    frames_per_second: float
    realtime_factor: float
    bytes: int
    supersample: int
    transparent: bool
    threads: int
    format: str
    workers: int = 1

    def to_dict(self):
        return asdict(self)


def render(scene, output, *, width=None, height=None, fps=24, start=0.0, end=None,
           supersample=1, overwrite=False, transparent=False, threads=2,
           preset="fast", crf=18, format=None, report=True, progress=None, workers=1):
    """Stream frames in order into FFmpeg, or write a PNG sequence directory.

    start/end are seconds in source scene; export duration is ceil((end-start)*fps)/fps.
    MP4 requires even dimensions. PNG/ProRes preserve odd sizes; WebM VP9 requires
    even sizes. Transparent output is supported for PNG, VP9 WebM and ProRes MOV.
    Existing targets are never replaced unless overwrite=True. A failed export
    leaves an existing target untouched; report output only includes its basename.
    ``workers`` renders frames in that many processes (``threads`` is FFmpeg's);
    the scene must come from load_scene() or be picklable. Output is identical.
    """
    _check_workers(workers)
    width, height = _dimensions(scene, width, height, supersample, workers)
    fps = frame_rate(fps)
    end = scene.duration if end is None else end
    if not all(math.isfinite(v) for v in (start, end, scene.duration)):
        raise ValueError("Scene and range must have finite times")
    if not 0 <= start < end <= scene.duration:
        raise ValueError("Render range must satisfy 0 <= start < end <= scene.duration")
    if isinstance(threads, bool) or not isinstance(threads, int) or threads < 1:
        raise ValueError("threads must be a positive integer")
    if preset not in ("ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"):
        raise ValueError("Unsupported FFmpeg preset")
    if isinstance(crf, bool) or not isinstance(crf, int) or not 0 <= crf <= 51:
        raise ValueError("crf must be an integer in [0, 51]")
    path = Path(output)
    extension = format or path.suffix.lower().lstrip(".")
    if extension not in ("mp4", "webm", "mov", "png"):
        raise ValueError("Supported formats: mp4, webm, mov, png (directory)")
    if transparent and extension == "mp4":
        raise ValueError("MP4 does not preserve alpha. Use .webm, .mov or a PNG sequence.")
    if extension in ("mp4", "webm") and (width % 2 or height % 2):
        raise ValueError("MP4/WebM dimensions must be even; use PNG/MOV for odd dimensions")
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {path.name}; use --overwrite")
    if path.exists() and path.is_dir() and extension != "png":
        raise ValueError("Video output must be a file")
    if extension == "png" and path.exists():
        # Avoid deleting arbitrary directories even with overwrite explicitly set.
        raise FileExistsError("PNG sequence output directory must be new; choose another directory")
    audio = getattr(scene, "audio", [])
    for clip in audio:
        if not Path(clip.path).is_file():
            raise FileNotFoundError(f"Audio input missing: {Path(clip.path).name}")
    executable = ffmpeg_executable() if extension != "png" else None
    times = frame_times(start, end, fps)
    frame_count = len(times)
    duration = float(frame_count / fps)
    workers = min(workers, frame_count)
    # Reject an unshareable scene before creating any output.
    payload = _scene_payload(scene) if workers > 1 else None
    frames = _frames(scene, times, width=width, height=height, supersample=supersample,
                     encoding="png" if extension == "png" else "rgba", workers=workers, payload=payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}-{uuid.uuid4().hex}.tmp{path.suffix}")
    started = time.perf_counter()
    process = None
    try:
        if extension == "png":
            temp.mkdir()
            for index, data in enumerate(frames):
                (temp / f"{index:06d}.png").write_bytes(data)
                if progress:
                    progress(index + 1, frame_count)
            size = sum(p.stat().st_size for p in temp.iterdir())
        else:
            command = [executable, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pixel_format", "rgba", "-video_size", f"{width}x{height}", "-framerate", str(fps), "-i", "pipe:0"]
            for clip in audio:
                command.extend(["-ss", str(clip.offset), "-i", str(clip.path)])
            if audio:
                filters = []
                for index, clip in enumerate(audio, 1):
                    # Absolute source-scene placement, then trim to export range.
                    delay = round(clip.start * 1000)
                    filters.append(f"[{index}:a]asetpts=PTS-STARTPTS,volume={clip.volume},adelay={delay}:all=1[a{index}]")
                inputs = "".join(f"[a{i}]" for i in range(1, len(audio) + 1))
                filters.append(f"{inputs}amix=inputs={len(audio)}:normalize=0,atrim=start={start}:end={start + duration},asetpts=PTS-STARTPTS,apad,atrim=duration={duration}[sound]")
                command.extend(["-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[sound]", "-c:a", "libopus" if extension == "webm" else ("pcm_s16le" if extension == "mov" else "aac")])
            if extension == "mp4":
                command.extend(["-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart"])
            elif extension == "webm":
                command.extend(["-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0", "-deadline", "good", "-cpu-used", "4", "-pix_fmt", "yuva420p" if transparent else "yuv420p"])
            else:
                command.extend(["-c:v", "prores_ks", "-profile:v", "4" if transparent else "3", "-pix_fmt", "yuva444p10le" if transparent else "yuv422p10le"])
            command.extend(["-threads", str(threads), "-frames:v", str(frame_count), "-t", str(duration), "-f", extension, str(temp)])
            # A temporary stderr file prevents pipe deadlocks and preserves diagnostics.
            with tempfile.TemporaryFile() as stderr:
                process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                           stderr=stderr, start_new_session=sys.platform != "win32")
                try:
                    for index, data in enumerate(frames):
                        process.stdin.write(data)
                        if progress:
                            progress(index + 1, frame_count)
                    process.stdin.close()
                    code = process.wait()
                except BaseException:
                    if process.stdin and not process.stdin.closed:
                        try:
                            process.stdin.close()
                        except BrokenPipeError:
                            pass
                    _terminate_encoder(process)
                    stderr.seek(0)
                    diagnostics = stderr.read().decode("utf-8", errors="replace").strip()
                    if diagnostics:
                        raise RuntimeError(f"FFmpeg export failed: {diagnostics}")
                    raise
                stderr.seek(0)
                diagnostics = stderr.read().decode("utf-8", errors="replace").strip()
                if code != 0:
                    raise RuntimeError(f"FFmpeg exited {code}: {diagnostics}")
            size = temp.stat().st_size
        os.replace(temp, path)
    finally:
        frames.close()
        if temp.is_dir():
            shutil.rmtree(temp)
        else:
            temp.unlink(missing_ok=True)
    elapsed = time.perf_counter() - started
    result = RenderReport(path.name, width, height, str(fps), frame_count, float(start), float(end), duration, elapsed, frame_count / max(elapsed, 1e-9), duration / max(elapsed, 1e-9), size, supersample, transparent, threads, extension, workers)
    if report:
        report_path = path.with_suffix(path.suffix + ".json") if extension != "png" else path / "render.json"
        report_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return result
