"""Integration contracts for the four complete, repository-owned short films.

These smoke checks catch broken drawing branches and mutable frame history;
artistic quality is evaluated separately by sequential visual review.
"""
from pathlib import Path
import wave

import numpy as np
import pytest

from bamboonimation.cli import load_scene
from bamboonimation.render import frame


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = [
    # Include hand inserts, the connected smear, catches, and final acting.
    ("tea_for_two", (0.5, 40 / 24, 44 / 24, 116 / 24, 130 / 24, 139 / 24, 149 / 24, 154 / 24, 184 / 24, 10.0, 14.0), True),
    ("the_last_cookie", (0.5, 3.3, 6.6, 8.3, 13.5), True),
    # Both authored graphic impact exposures must also survive random access.
    ("paper_moon", (0.5, 75 / 24, 76 / 24, 6.0, 10.2, 14.0), True),
    # Each sample lies inside a different world, away from transitions.
    ("versatility", (1.0, 5.5, 11.0), False),
]


def pixels(scene, time):
    return frame(scene, time, width=320, height=180).toarray()


@pytest.mark.parametrize("name,times,has_score", EXAMPLES, ids=[x[0] for x in EXAMPLES])
def test_final_examples_load_outside_project_render_and_rewind(name, times, has_score, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scene = load_scene(ROOT / "examples" / f"{name}.py")
    assert Path.cwd() == tmp_path
    assert scene.duration == pytest.approx(15)
    assert (scene.width, scene.height) == (1280, 720)

    # Opening the resolved WAV from another cwd exercises the actual asset path,
    # including optional score detection in scenes that support silent fallback.
    assert bool(scene.audio) is has_score
    for clip in scene.audio:
        audio = Path(clip.path)
        assert audio.is_absolute() and audio.is_file()
        assert audio.parent == ROOT / "assets" / "audio"
        with wave.open(str(audio), "rb") as wav:
            assert wav.getnframes() / wav.getframerate() == pytest.approx(15)
            assert any(wav.readframes(wav.getnframes()))

    samples = [pixels(scene, t) for t in times]
    for image in samples:
        assert image.shape == (180, 320, 4)
        rgb = image[:, :, :3].astype(np.int16)
        assert rgb.max() - rgb.min() > 50
        assert rgb.std() > 8
        assert np.all(image[:, :, 3] == 255)

    # Shots/worlds must contain visibly different compositions, rather than one
    # held placeholder exported for fifteen seconds. Avoid pixel-golden files.
    for a, b in zip(samples, samples[1:]):
        difference = np.abs(a[:, :, :3].astype(float) - b[:, :, :3]).mean()
        assert difference > (10 if name == "versatility" else 1)

    # Seek to the ending first, then revisit every inspected shot in reverse.
    # Byte-identical output detects mutable drawing banks, simulation history,
    # leaked Canvas style/transforms, and stale effect/camera cache state.
    pixels(scene, scene.duration)
    for time, expected in reversed(list(zip(times, samples))):
        assert np.array_equal(pixels(scene, time), expected)
