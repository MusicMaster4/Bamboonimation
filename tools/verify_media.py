"""Verify the four final fifteen-second previews and build a review contact sheet.

Uses ffprobe on PATH and the renderer's FFmpeg resolver. Every video frame is
actually decoded and hashed. This verifies media integrity and simple liveness,
not cartoon quality, acting equivalence, or perceptual audio/video synchronization.
Only relative output filenames and technical media measurements are published.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np
import skia

from bamboonimation.render import ffmpeg_executable

NAMES = ("tea_for_two", "the_last_cookie", "versatility", "paper_moon")
SAMPLE_TIMES = (0, 3.5, 6.25, 9.75, 13.5)
EXPECTED_FRAMES = 360
EXPECTED_DURATION = 15.0


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _read_exact(pipe, length):
    data = bytearray()
    while len(data) < length:
        chunk = pipe.read(length - len(data))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def inspect_video(video):
    expect_audio = video.stem != "versatility"
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("Final media verification requires ffprobe on PATH")
    metadata = json.loads(subprocess.check_output(
        [ffprobe, "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(video)],
        text=True))
    streams = metadata.get("streams", [])
    videos = [stream for stream in streams if stream.get("codec_type") == "video"]
    audios = [stream for stream in streams if stream.get("codec_type") == "audio"]
    _require(len(videos) == 1, f"{video.name}: expected one video stream")
    _require(len(audios) == (1 if expect_audio else 0),
             f"{video.name}: expected " + ("one audio stream" if expect_audio else "intentionally silent video"))
    stream = videos[0]
    sound = audios[0] if audios else None
    _require((stream.get("width"), stream.get("height")) == (1280, 720), f"{video.name}: expected1280x720")
    _require(stream.get("codec_name") == "h264", f"{video.name}: expected H264")
    _require(Fraction(stream["r_frame_rate"]) == 24 and Fraction(stream["avg_frame_rate"]) == 24,
             f"{video.name}: expected constant24fps")
    _require(int(stream["nb_read_frames"]) == EXPECTED_FRAMES, f"{video.name}: expected360decodedframes")
    durations = [("container", metadata["format"].get("duration")), ("video", stream.get("duration"))]
    if sound is not None:
        durations.append(("audio", sound.get("duration")))
    for label, duration in durations:
        _require(duration is not None and abs(float(duration) - EXPECTED_DURATION) <= .05,
                 f"{video.name}: {label} duration is not15seconds")
    if sound is not None:
        _require(sound.get("codec_name") == "aac", f"{video.name}: expectedAACaudio")
        _require(int(sound["sample_rate"]) == 48000, f"{video.name}: expected48kHzaudio")
        _require(int(sound["channels"]) == 1, f"{video.name}: expectedmonoaudio")

    hashes, differences, frames = [], [], []
    selected = {round(t * 24): t for t in SAMPLE_TIMES}
    # Native frames are all decoded; thumbnails only limit audit/hash memory use.
    command = [ffmpeg_executable(), "-v", "error", "-i", str(video), "-map", "0:v:0", "-an",
               "-vf", "scale=320:180", "-vsync", "0", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    previous = None
    with tempfile.TemporaryFile() as diagnostics:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=diagnostics)
        try:
            while True:
                raw = _read_exact(process.stdout, 320 * 180 * 3)
                if not raw:
                    break
                _require(len(raw) == 320 * 180 * 3, f"{video.name}: truncateddecodedframe")
                index = len(hashes)
                hashes.append(hashlib.sha256(raw).hexdigest())
                pixels = np.frombuffer(raw, dtype=np.uint8).reshape(180, 320, 3)
                if previous is not None:
                    differences.append(float(np.mean(np.abs(pixels.astype(np.int16) - previous))))
                if index in selected:
                    frames.append((selected[index], pixels.copy()))
                previous = pixels.astype(np.int16)
            code = process.wait()
        except BaseException:
            process.kill()
            process.wait()
            raise
        finally:
            process.stdout.close()
        diagnostics.seek(0)
        error = diagnostics.read().decode("utf-8", errors="replace").strip()
        _require(code == 0 and not error, f"{video.name}: decodedvideoerror {error}")
    _require(len(hashes) == EXPECTED_FRAMES, f"{video.name}: full decode yielded{len(hashes)}frames")
    sample_hashes = [hashes[round(t * 24)] for t in SAMPLE_TIMES]
    _require(len(set(sample_hashes)) == len(SAMPLE_TIMES), f"{video.name}: story samples are frozen")

    audio_report = {"silent": True, "intentional": True}
    if sound is not None:
        command = [ffmpeg_executable(), "-v", "error", "-i", str(video), "-map", "0:a:0", "-vn",
                   "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "1", "-ar", "48000", "pipe:1"]
        decoded = subprocess.run(command, capture_output=True, check=True)
        _require(not decoded.stderr.strip(), f"{video.name}: audio decode warning/error")
        samples = np.frombuffer(decoded.stdout, dtype="<f4")
        _require(len(samples) >= 15 * 48000, f"{video.name}: truncatedaudio")
        samples = samples[:15 * 48000]
        _require(bool(np.all(np.isfinite(samples))), f"{video.name}: nonfiniteaudio")
        peak = float(np.max(np.abs(samples)))
        rms = float(np.sqrt(np.mean(samples.astype(np.float64) ** 2)))
        _require(0 < peak <= .98, f"{video.name}: silentorclippingaudiosamplespeak{peak}")
        _require(rms > .0001, f"{video.name}: unexpectedlysilentaudio")
        ending_rms = float(np.sqrt(np.mean(samples[12 * 48000:].astype(np.float64) ** 2)))
        _require(ending_rms > .0001, f"{video.name}: silentpaddingat12..15seconds")
        audio_report = {"silent": False, "codec": sound["codec_name"], "sample_rate": 48000, "channels": 1,
                        "duration_seconds": float(sound["duration"]), "decoded_peak": peak,
                        "decoded_rms": rms, "ending_12_to_15_seconds_rms": ending_rms}
    return {
        "file": video.name, "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
        "bytes": video.stat().st_size, "codec": stream["codec_name"], "width": 1280, "height": 720,
        "fps": "24/1", "frames": len(hashes), "duration_seconds": float(metadata["format"]["duration"]),
        "every_frame_decoded": True, "frame_hash_resolution": [320, 180],
        "decoded_frame_sha256": hashes, "mean_adjacent_frame_delta": float(np.mean(differences)),
        "sample_times": list(SAMPLE_TIMES), "sampled_frame_sha256": sample_hashes,
        "audio": audio_report,
    }, frames


def main(argv=None):
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gallery", type=Path, default=root / "assets" / "gallery")
    parser.add_argument("--report", type=Path, default=root / "assets" / "validation" / "media.json")
    args = parser.parse_args(argv)
    for name in NAMES:
        _require((args.gallery / f"{name}.mp4").is_file(), f"Final preview missing: {name}.mp4")
    surface = skia.Surface(1600, len(NAMES) * 240)
    canvas = surface.getCanvas()
    canvas.clear(skia.ColorSetRGB(242, 235, 220))
    face = skia.FontMgr.RefDefault().matchFamilyStyle("sans-serif", skia.FontStyle())
    font = skia.Font(face, 16)
    paint = skia.Paint(Color=skia.ColorSetRGB(65, 58, 64), AntiAlias=True)
    reports = []
    for row, name in enumerate(NAMES):
        report, frames = inspect_video(args.gallery / f"{name}.mp4")
        reports.append(report)
        for column, (time, pixels) in enumerate(frames):
            image = skia.Image.fromarray(
                np.dstack((pixels, np.full((180, 320), 255, dtype=np.uint8))), colorType=skia.ColorType.kRGBA_8888_ColorType)
            canvas.drawImage(image, column * 320, row * 240 + 8)
            canvas.drawString(f"{name.replace('_', ' ')}  {time:g}s", column * 320 + 10, row * 240 + 213, font, paint)
        audio_status = "intentionally silent" if report["audio"]["silent"] else "AAC 48 kHz mono"
        print(f"Verified {name}: 360/360 frames, 15 seconds, {audio_status}")
    args.gallery.mkdir(parents=True, exist_ok=True)
    (args.gallery / "storyboard.jpg").write_bytes(bytes(surface.makeImageSnapshot().encodeToData(skia.kJPEG, 92)))
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(reports, indent=2) + "\n", encoding="utf-8")
    print(f"Verified 4 complete videos; decoded 1440 frames and 20 story samples; wrote {args.report.name}")


if __name__ == "__main__":
    main()
