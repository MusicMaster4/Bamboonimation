"""Shot sequencing with deterministic cuts, dissolves, wipes and iris reveals."""
from __future__ import annotations
from dataclasses import dataclass, replace
import math
import skia
from .drawing import Canvas


@dataclass(frozen=True)
class Shot:
    scene: object
    start: float
    transition: str = 'cut'
    overlap: float = 0

    @property
    def end(self):
        return self.start + self.scene.duration


class Storyboard:
    """A renderable sequence of arbitrary Scene-compatible compositions.

    add(scene) cuts to the next scene. add(scene, transition='dissolve',
    overlap=.4) starts the next scene .4 seconds before the preceding shot ends.
    Each shot receives its own local time, seed and logical viewport. Shots
    fit inside the board without distortion; background fills any letterboxing.
    Set background=None for transparent bars.
    """
    def __init__(self, *, width=1280, height=720, seed=1, background='#000000'):
        if not all(math.isfinite(v) and v > 0 for v in (width, height)):
            raise ValueError('Dimensions must be positive and finite')
        self.width, self.height, self.seed = width, height, seed
        self.background = background
        self.shots = []
        self.metadata = {}
        self.audio = []

    @property
    def duration(self):
        return self.shots[-1].end if self.shots else 0

    def add(self, scene, *, transition='cut', overlap=0):
        if transition not in ('cut', 'dissolve', 'wipe', 'iris'):
            raise ValueError('Transition must be cut, dissolve, wipe or iris')
        if not math.isfinite(overlap) or overlap < 0:
            raise ValueError('Overlap must be finite and nonnegative')
        if not all(math.isfinite(v) and v > 0 for v in (scene.width, scene.height, scene.duration)):
            raise ValueError('Shot dimensions and duration must be positive and finite')
        if transition == 'cut' and overlap:
            raise ValueError('A cut has no overlap')
        if not self.shots:
            if overlap:
                raise ValueError('First shot cannot overlap')
            transition = 'cut'
        elif overlap >= min(scene.duration, self.shots[-1].scene.duration - self.shots[-1].overlap):
            raise ValueError('Overlap cannot cover an entire shot or overlap another transition')
        elif transition != 'cut' and overlap == 0:
            raise ValueError('A transition needs a positive overlap')
        shot = Shot(scene, self.duration - overlap, transition, overlap)
        self.shots.append(shot)
        for clip in getattr(scene, 'audio', ()):
            self.audio.append(replace(clip, start=clip.start + shot.start))
        return self

    def _paint(self, canvas, shot, time):
        with canvas.saved():
            canvas.raw.clipRect(skia.Rect.MakeWH(self.width, self.height))
            if self.background is not None:
                canvas.rect(0, 0, self.width, self.height, self.background)
            scale = min(self.width / shot.scene.width, self.height / shot.scene.height)
            canvas.translate((self.width - shot.scene.width * scale) / 2,
                             (self.height - shot.scene.height * scale) / 2)
            canvas.scale(scale)
            canvas.raw.clipRect(skia.Rect.MakeWH(shot.scene.width, shot.scene.height))
            child = Canvas(canvas.raw, shot.scene.width, shot.scene.height,
                           time=time-shot.start, seed=shot.scene.seed)
            child.roughness, child.boil_fps = canvas.roughness, canvas.boil_fps
            shot.scene.draw(child, time-shot.start)

    def draw(self, canvas, time):
        if not math.isfinite(time):
            raise ValueError('Time must be finite')
        if not self.shots:
            raise ValueError('Storyboard needs at least one shot')
        # Selection depends only on time; no current-shot cursor survives a seek.
        index = max(0, max((i for i, s in enumerate(self.shots) if s.start <= time), default=0))
        shot = self.shots[index]
        p = (time-shot.start)/shot.overlap if shot.overlap else 1
        if index == 0 or p >= 1 or shot.transition == 'cut':
            self._paint(canvas, shot, time)
            return
        self._paint(canvas, self.shots[index-1], time)
        p = max(0, min(1, p))
        p = p*p*(3-2*p)
        if shot.transition == 'dissolve':
            with canvas.opacity(p):
                self._paint(canvas, shot, time)
        else:
            with canvas.saved():
                if shot.transition == 'wipe':
                    canvas.raw.clipRect(skia.Rect.MakeXYWH(0, 0, self.width*p, self.height), doAntiAlias=True)
                else:
                    path = skia.Path()
                    radius = math.hypot(self.width, self.height)*.5*p
                    path.addCircle(self.width/2, self.height/2, radius)
                    canvas.raw.clipPath(path, doAntiAlias=True)
                self._paint(canvas, shot, time)
