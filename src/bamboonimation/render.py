"""Bounded-memory raster rendering and atomic FFmpeg exports."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
import json
import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
import uuid
import sys

import skia

from .drawing import Canvas


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


def _dimensions(scene, width, height, supersample):
    width = scene.width if width is None else width
    height = scene.height if height is None else height
    for name, value in (("width", width), ("height", height), ("supersample", supersample)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")
    rw, rh = width * supersample, height * supersample
    if rw > 2**31 - 1 or rh > 2**31 - 1 or rw * rh * 4 > sys.maxsize:
        raise ValueError("Raster dimensions exceed Skia/platform address limits; reduce dimensions or supersample")
    # Conservative transient estimate includes previous frame, raw copies and downsampling.
    # User painters/asset caches and FFmpeg may need additional RAM beyond this estimate.
    estimated = 4 * (2 * rw * rh + 3 * width * height)
    available = _available_memory()
    if available is not None and estimated > available * .75:
        raise ValueError(f"Requested raster buffers need approximately {estimated / 2**20:.0f} MiB; "
                         f"only {available / 2**20:.0f} MiB RAM is available. Reduce dimensions or supersample.")
    return width, height


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
        target = skia.Surface(width, height)
        target.getCanvas().drawImageRect(image, skia.Rect.MakeWH(width, height), skia.SamplingOptions(skia.FilterMode.kLinear))
        image = target.makeImageSnapshot()
    return image


def save_frame(scene, output, t=0.0, *, width=None, height=None, supersample=1, overwrite=False):
    path = Path(output)
    if path.suffix.lower() != ".png":
        raise ValueError("Still frames must use .png")
    if path.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {path.name}; pass overwrite=True")
    image = frame(scene, t, width=width, height=height, supersample=supersample)
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

    def to_dict(self):
        return asdict(self)


def render(scene, output, *, width=None, height=None, fps=24, start=0.0, end=None,
           supersample=1, overwrite=False, transparent=False, threads=2,
           preset="fast", crf=18, format=None, report=True, progress=None):
    """Stream one frame at a time into FFmpeg, or write a PNG sequence directory.

    start/end are seconds in source scene; export duration is ceil((end-start)*fps)/fps.
    MP4 requires even dimensions. PNG/ProRes preserve odd sizes; WebM VP9 requires
    even sizes. Transparent output is supported for PNG, VP9 WebM and ProRes MOV.
    Existing targets are never replaced unless overwrite=True. A failed export
    leaves an existing target untouched; report output only includes its basename.
    """
    width, height = _dimensions(scene, width, height, supersample)
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
    frame_count = math.ceil((Fraction(str(end)) - Fraction(str(start))) * fps)
    duration = float(frame_count / fps)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.stem}-{uuid.uuid4().hex}.tmp{path.suffix}")
    started = time.perf_counter()
    process = None
    try:
        if extension == "png":
            temp.mkdir()
            for index in range(frame_count):
                image = frame(scene, start + float(index / fps), width=width, height=height, supersample=supersample)
                data = image.encodeToData(skia.kPNG, 100)
                (temp / f"{index:06d}.png").write_bytes(bytes(data))
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
                    for index in range(frame_count):
                        image = frame(scene, start + float(index / fps), width=width, height=height, supersample=supersample)
                        pixels = image.toarray(colorType=skia.ColorType.kRGBA_8888_ColorType, alphaType=skia.AlphaType.kUnpremul_AlphaType)
                        process.stdin.write(pixels.tobytes())
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
        if temp.is_dir():
            shutil.rmtree(temp)
        else:
            temp.unlink(missing_ok=True)
    elapsed = time.perf_counter() - started
    result = RenderReport(path.name, width, height, str(fps), frame_count, float(start), float(end), duration, elapsed, frame_count / max(elapsed, 1e-9), duration / max(elapsed, 1e-9), size, supersample, transparent, threads, extension)
    if report:
        report_path = path.with_suffix(path.suffix + ".json") if extension != "png" else path / "render.json"
        report_path.write_text(json.dumps(result.to_dict(), indent=2) + "\n", encoding="utf-8")
    return result
