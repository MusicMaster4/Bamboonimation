"""Command-line authoring, inspection and rendering tools."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid


def load_scene(filename):
    """Execute a trusted Python scene file. Scene files have normal Python access."""
    path = Path(filename).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Scene file not found: {path.name}")
    name = f"_bamboonimation_scene_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Scene input must be a Python .py file")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
        scene = module.make_scene() if callable(getattr(module, "make_scene", None)) else getattr(module, "scene", None)
        if scene is None or not callable(getattr(scene, "draw", None)):
            raise ValueError("Scene file must define scene = Scene(...) or make_scene() returning a Scene")
        try:
            # Render workers and the live preview reload the scene from here.
            scene.source_file = path
        except AttributeError:
            pass
        return scene
    finally:
        sys.path.pop(0)
        sys.modules.pop(name, None)


def _workers(value):
    if value == "auto":
        return value
    try:
        count = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("use a positive integer or 'auto'") from None
    if count < 1:
        raise argparse.ArgumentTypeError("use a positive integer or 'auto'")
    return count


def _parser():
    parser = argparse.ArgumentParser(prog="bamboonimation", description="Draw and animate 2D cartoons with Python. All rendering runs locally.")
    parser.add_argument("--version", action="version", version="Bamboonimation 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("render", "Export a video or PNG sequence"), ("frame", "Render one PNG at an absolute time"), ("sheet", "Render a labelled contact sheet of many frames"), ("preview", "Open a local timeline preview that reloads on save"), ("benchmark", "Measure an actual render")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("scene", type=Path, help="Trusted Python scene file")
        command.add_argument("--width", type=int, help="Cell width for sheet" if name == "sheet" else None)
        if name != "sheet":
            command.add_argument("--height", type=int)
        command.add_argument("--supersample", type=int, default=1, help="Integer antialiasing multiplier; 2 uses about 4x raster work")
        if name != "preview":
            command.add_argument("-o", "--output", type=Path, required=True)
            command.add_argument("--overwrite", action="store_true")
        if name in ("render", "benchmark", "sheet"):
            command.add_argument("--workers", type=_workers, default="auto",
                                 help="Frame-rendering processes, or 'auto' (default; short jobs stay serial)")
        if name in ("render", "benchmark"):
            command.add_argument("--fps", default="24", help="Positive FPS or rational, e.g. 24000/1001")
            command.add_argument("--start", type=float, default=0)
            command.add_argument("--end", type=float)
            command.add_argument("--threads", type=int, default=2, help="FFmpeg encoder threads")
            command.add_argument("--crf", type=int, default=18)
            command.add_argument("--preset", default="fast")
            command.add_argument("--transparent", action="store_true", help="Preserve alpha in WebM/MOV/PNG; author a transparent scene")
            command.add_argument("--format", choices=("mp4", "webm", "mov", "png"))
        elif name == "frame":
            command.add_argument("--time", type=float, default=0)
        elif name == "sheet":
            command.add_argument("--start", type=float, default=0)
            command.add_argument("--end", type=float, help="Defaults to the scene duration")
            command.add_argument("--count", type=int, default=12, help="Evenly spaced frames from start to end, inclusive")
            command.add_argument("--every-frame", action="store_true",
                                 help="Instead of --count, include every exported frame in [start, end) at --fps")
            command.add_argument("--fps", default="24", help="Frame rate for frame numbers and --every-frame")
            command.add_argument("--columns", type=int)
        else:
            command.add_argument("--port", type=int, default=0, help="Loopback port; 0 chooses a free port")
            command.add_argument("--no-open", action="store_true")
            command.add_argument("--fps", default="24", help="Frame rate for arrow-key stepping and frame numbers")
            command.add_argument("--no-reload", action="store_true", help="Do not reload the scene when its folder's .py files change")
    doctor = commands.add_parser("doctor", help="Check Python, Skia and video encoders")
    doctor.add_argument("--json", action="store_true")
    init = commands.add_parser("init", help="Create a small editable scene project")
    init.add_argument("directory", type=Path)
    return parser


_TEMPLATE = '''"""Your first Bamboonimation scene. Edit this trusted Python file freely."""
import math
from bamboonimation import Scene


def paint(c, t):
    # Everything uses logical 1280x720 coordinates, independent of export size.
    c.ellipse(640, 590, 130, 22, fill="#d7c3a0")
    y = 390 - abs(math.sin(t * math.pi)) * 130
    with c.transform(x=640, y=y, rotation=math.sin(t * 2) * 8):
        c.ellipse(0, 0, 95, 110, fill="#df8c51", stroke="#383348", width=5)
        c.ellipse(-30, -15, 13, 19, fill="#383348")
        c.ellipse(30, -15, 13, 19, fill="#383348")
        c.path("M -28 35 Q 0 65 28 35", stroke="#383348", width=5)
    c.text("A little bounce", 470, 660, size=38, fill="#383348")


scene = Scene(width=1280, height=720, duration=12, background="#f2e4cb", painter=paint)
'''


def doctor_info():
    import skia
    from .render import ffmpeg_executable
    result = {"python": platform.python_version(), "platform": platform.system(), "skia": skia.__version__}
    try:
        ffmpeg = ffmpeg_executable()
        check = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=20, check=True)
        result["ffmpeg"] = True
        result["encoders"] = {name: name in check.stdout for name in ("libx264", "libvpx-vp9", "prores_ks")}
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        result["ffmpeg"] = False
        result["error"] = type(exc).__name__
    return result


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            info = doctor_info()
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"Python {info['python']} · {info['platform']} · Skia {info['skia']}")
                print("FFmpeg: " + ("ready" if info["ffmpeg"] else "unavailable"))
                for encoder, available in info.get("encoders", {}).items():
                    print(f"  {encoder}: {'ready' if available else 'missing'}")
            return 0 if info["ffmpeg"] and info["encoders"].get("libx264") else 1
        if args.command == "init":
            directory = args.directory
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / "scene.py"
            if target.exists():
                raise FileExistsError("scene.py already exists; choose an empty project directory")
            target.write_text(_TEMPLATE, encoding="utf-8")
            (directory / "README.md").write_text("# My animation\n\nPreview: `bamboonimation preview scene.py`\n\nRender: `bamboonimation render scene.py -o movie.mp4 --fps 24`\n", encoding="utf-8")
            print(f"Created {directory / 'scene.py'}")
            return 0
        scene = load_scene(args.scene)
        if args.command == "sheet":
            from .render import contact_sheet, default_workers, frame_times
            end = scene.duration if args.end is None else args.end
            if not 0 <= args.start < end <= scene.duration:
                raise ValueError("Sheet range must satisfy 0 <= start < end <= scene duration")
            if args.every_frame:
                times = frame_times(args.start, end, args.fps)
            else:
                if args.count < 1:
                    raise ValueError("--count must be positive")
                times = [args.start + (end - args.start) * i / max(1, args.count - 1) for i in range(args.count)]
            workers = default_workers(len(times)) if args.workers == "auto" else args.workers
            result = contact_sheet(scene, args.output, times, cell_width=args.width or 320, columns=args.columns,
                                   fps=args.fps, supersample=args.supersample, overwrite=args.overwrite, workers=workers)
            print(f"Saved {result} ({len(times)} frames)")
            return 0
        common = dict(width=args.width, height=args.height, supersample=args.supersample)
        if args.command == "preview":
            from .preview import serve
            serve(scene, port=args.port, open_browser=not args.no_open, fps=args.fps,
                  source=None if args.no_reload else args.scene, **common)
            return 0
        if args.command == "frame":
            from .render import save_frame
            result = save_frame(scene, args.output, args.time, overwrite=args.overwrite, **common)
            print(f"Saved {result}")
            return 0
        from .render import default_workers, frame_rate, render
        workers = args.workers
        if workers == "auto":
            end = scene.duration if args.end is None else args.end
            workers = default_workers(math.ceil(max(0, end - args.start) * frame_rate(args.fps)))
        last = [0.0]
        def progress(index, count):
            now = time.monotonic()
            if now - last[0] > 2 or index == count:
                print(f"\rRendering {index}/{count} ({index / count:.0%})", end="", file=sys.stderr, flush=True)
                last[0] = now
        result = render(scene, args.output, fps=args.fps, start=args.start, end=args.end, threads=args.threads, crf=args.crf, preset=args.preset, transparent=args.transparent, format=args.format, overwrite=args.overwrite, progress=progress, workers=workers, **common)
        print(file=sys.stderr)
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    except KeyboardInterrupt:
        print("Stopped.", file=sys.stderr)
        return 130
    except (ValueError, RuntimeError, OSError, TypeError, AttributeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
