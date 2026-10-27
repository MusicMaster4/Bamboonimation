"""Reproduce resource measurements without publishing hostnames or absolute paths.

Install development extras, then run:
python tools/measure_render.py examples/tea_for_two.py --width 1280 --height 720

Python+FFmpeg RSS and cumulative CPU times are sampled every nominal50ms.
Sampled peaks/CPU can miss brief work between observations; measurements are
not guaranteed upper bounds. No account, network or generative service is used.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import time

import psutil


def file_sha256(path):
    """Stream hashes so large final videos do not grow the measurement tool's RAM."""
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def input_snapshot(scene, root):
    """Repository source/audio snapshot; audio inventory is not an asset-use claim."""
    engine = hashlib.sha256()
    for source in sorted((root / 'src/bamboonimation').glob('*.py')):
        engine.update(source.name.encode())
        engine.update(source.read_bytes())
    return {
        'scene_sha256': file_sha256(scene),
        'engine_sha256': engine.hexdigest(),
        'audio_assets_sha256': {source.name: file_sha256(source) for source in sorted((root / 'assets/audio').glob('*.wav'))},
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene', type=Path)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    parser.add_argument('--fps', default='24')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--end', type=float)
    parser.add_argument('--preset', default='fast', choices=('ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'))
    parser.add_argument('--crf', type=int, default=18)
    parser.add_argument('--threads', type=int, default=2)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    snapshot_before = input_snapshot(args.scene, root)
    name = f'{args.scene.stem}-{args.width}x{args.height}-{args.fps.replace("/", "_")}'
    output = args.output or Path('renders') / (name + '.mp4')
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, '-m', 'bamboonimation', 'render', str(args.scene), '-o', str(output),
               '--width', str(args.width), '--height', str(args.height), '--fps', args.fps, '--overwrite',
               '--preset', args.preset, '--crf', str(args.crf), '--threads', str(args.threads)]
    if args.end is not None:
        command += ['--end', str(args.end)]
    log = output.with_suffix('.log')
    started = time.perf_counter()
    peak = 0
    cpu = {}
    observations = 0
    with log.open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        try:
            process = psutil.Process(child.pid)
            while True:
                total_rss = 0
                try:
                    family = [process] + process.children(recursive=True)
                except psutil.Error:
                    family = []
                for member in family:
                    try:
                        total_rss += member.memory_info().rss
                        times = member.cpu_times()
                        # PID+birth prevents rare PID reuse from overwriting another process.
                        identity = member.pid, member.create_time()
                        cpu[identity] = max(cpu.get(identity, 0), times.user + times.system)
                    except psutil.Error:
                        pass
                peak = max(peak, total_rss)
                observations += 1
                if child.poll() is not None:
                    break
                time.sleep(.05)
            code = child.wait()
        finally:
            if child.poll() is None:
                try:
                    family = psutil.Process(child.pid).children(recursive=True)
                except psutil.Error:
                    family = []
                for member in reversed(family):
                    try:
                        member.terminate()
                    except psutil.Error:
                        pass
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
    elapsed = time.perf_counter() - started
    if code:
        print(log.read_text(encoding='utf-8'))
        return code
    snapshot_after = input_snapshot(args.scene, root)
    stable = snapshot_before == snapshot_after
    render_report = json.loads(output.with_suffix(output.suffix + '.json').read_text())
    # Renderer reports fields it owns; benchmark records the exact explicitly sent
    # encoding controls here as well, rather than relying on a changing CLI default.
    render_report.update(encoder_preset=args.preset, encoder_crf=args.crf, threads=args.threads)
    sampled_cpu = sum(cpu.values())
    summary = {
        'scene': args.scene.name, 'output_sha256': file_sha256(output),
        **snapshot_before,
        'input_snapshot_stable_during_render': stable,
        'input_snapshot_after_render': snapshot_after,
        'audio_asset_snapshot_scope': 'All repository assets/audio/*.wav at measurement start/end; this inventory does not assert that every file is used by this scene.',
        'environment': {'os': platform.system(), 'python': platform.python_version(),
                        'logical_cpus': psutil.cpu_count(),
                        'physical_ram_gib': round(psutil.virtual_memory().total / 1024**3, 2),
                        'dependencies': {name: importlib.metadata.version(name) for name in ('skia-python', 'numpy', 'imageio-ffmpeg')}},
        'render': render_report, 'process_wall_seconds': round(elapsed, 3),
        'peak_summed_rss_mib': round(peak / 1024**2, 2),
        'sampled_cpu_seconds': round(sampled_cpu, 3),
        'average_cpu_cores': round(sampled_cpu / elapsed, 3),
        'sampling_interval_seconds': .05, 'samples': observations,
        'method': ('One child Python process plus its FFmpeg descendants; observer process excluded. '
                   'RSS summed at observations, shared pages may be counted twice; transient peaks may be missed. '
                   'CPU is the sum of last observed cumulative user+system times per process identity, so exited/brief processes and work after their last observation may be missed. '
                   'Average CPU cores is sampled CPU seconds divided by child wall time, not machine CPU percent. '
                   'Includes import/startup; nominal50ms interval plus observation overhead. No network or generative inference.')}
    destination = Path('assets/validation') / (name + '.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))
    if not stable:
        print('Input source/audio changed during rendering; this output cannot establish a matching-source benchmark. Rerun after edits stop.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
