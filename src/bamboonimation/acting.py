"""Authored replacement drawings, variable exposures and registered attachments.

These tools control *when* and *where* authored art appears. They do not invent
poses, infer grips or automatically turn a front drawing into a back drawing.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from fractions import Fraction
import math
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping


def _finite(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def _point(value, name):
    try:
        x, y = value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain two coordinates") from exc
    return _finite(x, name), _finite(y, name)


def _name(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


@dataclass(frozen=True)
class Exposure:
    """One sampled authored exposure; all frame numbers are zero-based.

    source_frame is the current source timeline frame (clamped at the end).
    start_frame is the first frame of this drawing's hold. Rendering a moving
    replacement at ``time`` preserves its hold; ``source_time`` advances each
    source frame and is useful for independent effects.
    """
    drawing_key: str
    source_frame: int
    start_frame: int
    hold_frames: int
    fps: Fraction

    @property
    def drawing(self):
        return self.drawing_key

    @property
    def frame(self):
        return self.source_frame

    @property
    def local_frame(self):
        return self.source_frame - self.start_frame

    @property
    def local_time(self):
        return float(self.local_frame / self.fps)

    @property
    def start_time(self):
        return float(self.start_frame / self.fps)

    @property
    def time(self):
        return self.start_time

    @property
    def source_time(self):
        return float(self.source_frame / self.fps)


class ExposureSheet:
    """Append named drawing holds counted in source frames, independent of export.

    ``ExposureSheet(fps=24).add('anticipate', frames=6).add('smear', frames=1)``
    samples exact rational boundaries when t is Fraction/int. Float boundaries
    allow one ULP of multiplication rounding. The final drawing holds after the
    sheet ends; negative/nonfinite times and sampling an empty sheet are errors.
    """
    def __init__(self, fps=24, *, source_fps=None):
        if source_fps is not None:
            fps = source_fps
        try:
            self.fps = fps if isinstance(fps, Fraction) else Fraction(str(fps))
        except (ValueError, TypeError, ZeroDivisionError, OverflowError) as exc:
            raise ValueError("Source fps must be positive, e.g. 24 or '24000/1001'") from exc
        if self.fps <= 0:
            raise ValueError("Source fps must be positive")
        self._holds = []
        self._ends = []

    def add(self, drawing_key, *, frames):
        _name(drawing_key, "Drawing key")
        if isinstance(frames, bool) or not isinstance(frames, int) or frames <= 0:
            raise ValueError("Exposure frames must be a positive integer")
        start = self.total_frames
        self._holds.append((drawing_key, start, frames))
        self._ends.append(start + frames)
        return self

    @property
    def total_frames(self):
        return self._ends[-1] if self._ends else 0

    @property
    def duration(self):
        return float(self.total_frames / self.fps)

    @property
    def duration_fraction(self):
        return self.total_frames / self.fps

    def sample(self, t):
        if not self._holds:
            raise ValueError("Cannot sample an empty ExposureSheet")
        seconds = _finite(t, "Sample time")
        if seconds < 0:
            raise ValueError("Sample time must be nonnegative")
        if isinstance(t, (Fraction, int)):
            source_frame = math.floor(t * self.fps)
        else:
            frame_position = seconds * float(self.fps)
            if not math.isfinite(frame_position):
                source_frame = self.total_frames - 1
            else:
                source_frame = math.floor(math.nextafter(frame_position, math.inf))
        source_frame = min(source_frame, self.total_frames - 1)
        index = bisect_right(self._ends, source_frame)
        key, start, count = self._holds[index]
        return Exposure(key, source_frame, start, count, self.fps)

    def key(self, t):
        return self.sample(t).drawing_key

    def time(self, t):
        """Absolute source time of the selected drawing's exposure start."""
        return self.sample(t).start_time


@dataclass(frozen=True)
class RegisteredDrawing:
    drawing: Callable | str | Path
    registration: tuple[float, float]
    anchors: Mapping[str, tuple[float, float]]
    size: tuple[float, float] | None = None


class DrawingBank:
    """Named replacement drawings sharing an author-controlled registration point.

    Painters use ``painter(canvas, time)`` and keep their own local coordinates.
    Image filenames are also accepted; optional size gives their local width and
    height. Keys switch immediately: there is no interpolation or crossfade of
    incompatible drawing topology.
    """
    def __init__(self):
        self._drawings = {}

    def add(self, key, drawing, *, registration=(0, 0), anchors=None, size=None):
        _name(key, "Drawing key")
        if key in self._drawings:
            raise ValueError(f"Drawing key already registered: {key!r}")
        if not callable(drawing) and not isinstance(drawing, (str, Path)):
            raise TypeError("Drawing must be a painter(canvas,time) callable or an image path")
        registration = _point(registration, "Registration")
        copied_anchors = {}
        for name, point in (anchors or {}).items():
            copied_anchors[_name(name, "Anchor name")] = _point(point, f"Anchor {name!r}")
        if size is not None:
            size = _point(size, "Image size")
            if min(size) <= 0:
                raise ValueError("Image size must be positive")
        self._drawings[key] = RegisteredDrawing(drawing, registration, MappingProxyType(copied_anchors), size)
        return self

    def __contains__(self, key):
        return key in self._drawings

    def __len__(self):
        return len(self._drawings)

    def keys(self):
        return tuple(self._drawings)

    def get(self, key):
        try:
            return self._drawings[key]
        except KeyError:
            raise KeyError(f"Unknown drawing key {key!r}; available: {', '.join(self._drawings) or '(none)'}") from None

    @staticmethod
    def _placement(x, y, scale, rotation):
        x, y = _finite(x, "x"), _finite(y, "y")
        if isinstance(scale, (tuple, list)):
            sx, sy = _point(scale, "Scale")
        else:
            sx = sy = _finite(scale, "Scale")
        if sx == 0 or sy == 0:
            raise ValueError("Scale components must be nonzero")
        return x, y, sx, sy, _finite(rotation, "Rotation")

    def draw(self, canvas, key, x=0, y=0, *, scale=1, rotation=0, time=0):
        drawing = self.get(key)
        x, y, sx, sy, rotation = self._placement(x, y, scale, rotation)
        time = _finite(time, "Drawing time")
        with canvas.transform(x=x, y=y, rotation=rotation, sx=sx, sy=sy):
            canvas.translate(-drawing.registration[0], -drawing.registration[1])
            if callable(drawing.drawing):
                drawing.drawing(canvas, time)
            elif drawing.size is None:
                canvas.image(drawing.drawing, 0, 0)
            else:
                canvas.image(drawing.drawing, 0, 0, *drawing.size)
        return self

    def anchor(self, key, name, x=0, y=0, *, scale=1, rotation=0):
        """World anchor using the exact same transform/order as ``draw``."""
        drawing = self.get(key)
        try:
            ax, ay = drawing.anchors[name]
        except KeyError:
            raise KeyError(f"Drawing {key!r} has no anchor {name!r}; available: {', '.join(drawing.anchors) or '(none)'}") from None
        x, y, sx, sy, rotation = self._placement(x, y, scale, rotation)
        ax = (ax - drawing.registration[0]) * sx
        ay = (ay - drawing.registration[1]) * sy
        angle = math.radians(rotation)
        co, si = math.cos(angle), math.sin(angle)
        return x + ax * co - ay * si, y + ax * si + ay * co


def volume_preserving_squash(s):
    """Return (1/s, s): reciprocal 2D scales preserving *area*, not 3D volume."""
    s = _finite(s, "Squash")
    if s <= 0:
        raise ValueError("Squash must be positive")
    return 1 / s, s


def smear_path(start, end, width, curve=0):
    """SVG lens-shaped directional smear between two authored world/local points.

    Width is maximum full thickness at the midpoint; curve is signed midpoint
    displacement perpendicular to start→end. This generic silhouette is a helper,
    not a generated character pose. Author a custom path for recognizable faces,
    fingers or clothing. Expose briefly with an ExposureSheet key.
    """
    x0, y0 = _point(start, "Smear start")
    x1, y1 = _point(end, "Smear end")
    width, curve = _finite(width, "Smear width"), _finite(curve, "Smear curve")
    if width <= 0:
        raise ValueError("Smear width must be positive")
    dx, dy = x1 - x0, y1 - y0
    distance = math.hypot(dx, dy)
    if distance == 0:
        raise ValueError("Smear start and end must differ")
    nx, ny = -dy / distance, dx / distance
    upper, lower = curve * 4 / 3 + width * 2 / 3, curve * 4 / 3 - width * 2 / 3
    def point(fraction, offset):
        return f"{x0 + dx * fraction + nx * offset:.12g} {y0 + dy * fraction + ny * offset:.12g}"
    return (f"M {x0:.12g} {y0:.12g} C {point(.25, upper)} {point(.75, upper)} {x1:.12g} {y1:.12g} "
            f"C {point(.75, lower)} {point(.25, lower)} {x0:.12g} {y0:.12g} Z")
