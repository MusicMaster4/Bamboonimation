# English quickstart

Bamboonimation is a Python framework for original 2D cartoon animation. Draw any subject with paths, images, sprites and custom callbacks, animate local hierarchies or rigs, and render through Skia on CPU and FFmpeg. Example characters are optional starting points, not a restriction on what you can draw.

The software is **source-available under the PolyForm Noncommercial License 1.0.0**, not OSI open source. Commercial use of the software or a fork requires separate permission. See [LICENSE](../LICENSE).

## Install

On Ubuntu/Debian, install the Skia wheel's system runtime library first, including on headless machines:

```bash
sudo apt-get update
sudo apt-get install --yes libegl1
```

Rendering still uses the CPU. Other Linux distributions need the equivalent package providing `libEGL.so.1`; this step does not apply to macOS or Windows.

```bash
git clone https://github.com/MusicMaster4/Bamboonimation.git
cd Bamboonimation
python -m venv .venv
```

Use `.venv/bin/python` on Linux/macOS or `.venv\Scripts\python.exe` on Windows for the following commands:

```bash
python -m pip install -e .
python -m bamboonimation doctor
python -m bamboonimation frame examples/tea_for_two.py --time 3 -o renders/pose.png
python -m bamboonimation render examples/tea_for_two.py -o renders/tea.mp4 --width 1280 --height 720 --fps 24
```

Python 3.11+ is required. Python 3.12 is a conservative starting point when dependency wheels for a newer version are unavailable.

## Author a scene

```python
import math
from bamboonimation import Scene

def draw(c, t):
    c.rect(0, 500, 1280, 220, fill="#d4b990")
    with c.transform(x=640, y=380 + 18 * math.sin(t * 2)):
        c.ellipse(0, 0, 90, 100, fill="#eec576", stroke="#403944", width=4)
        c.ellipse(-28, -15, 9, 14, fill="#403944")
        c.ellipse(28, -15, 9, 14, fill="#403944")
        c.path("M -25 28 Q 0 53 25 28", stroke="#403944", width=4)

scene = Scene(width=1280, height=720, duration=12, painter=draw)
```

Save it as `scene.py`. The loader accepts a module-level `scene` or `make_scene()` factory. Use absolute time in seconds, not accumulated per-frame state. Output resolution and FPS can change independently of the logical canvas. Different aspect ratios are fitted with letterboxing; author a new composition when vertical framing requires it.

```bash
python -m bamboonimation render scene.py -o renders/scene.mp4 --fps 24000/1001
python -m bamboonimation preview scene.py
python -m bamboonimation render --help
```

A scene is unrestricted Python code and is **not sandboxed**. Only run trusted scripts. Keep preview on localhost. Rendering needs no paid AI service, but CPU time, RAM, disk space and optional external authoring tools still have costs. See [measured validation](validation.md), [API](api.md), [agent guide](agent-guide.md) and [best practices](best-practices.md) for details; these longer documents are in Portuguese.

The browser preview is silent: it scrubs and plays requested PNG frames, without scene audio. Under load it can skip requested times. Review the exported video at normal speed to assess timing and sound; the preview is not a real-time playback benchmark.
