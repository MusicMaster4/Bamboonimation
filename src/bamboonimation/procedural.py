"""Stateless building blocks for arbitrary 2D worlds, effects and motion."""
from __future__ import annotations
from dataclasses import dataclass
from bisect import bisect_left
import math
import random
from typing import Callable


def _finite(*values):
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('Parameters must be finite')


def spring(time: float, *, frequency: float = 2.0, damping: float = .55,
           initial: float = 0.0, target: float = 1.0, velocity: float = 0.0) -> float:
    """Analytic damped spring step. Frequency is Hz; velocity is units/second.

    Supports under-, critically- and over-damped motion without integration or
    previous-frame state. Before time zero, returns the initial value.
    """
    _finite(time, frequency, damping, initial, target, velocity)
    if frequency <= 0 or damping < 0:
        raise ValueError('Frequency must be positive and damping nonnegative')
    if time <= 0:
        return initial
    w = math.tau * frequency
    y = initial - target
    if damping < 1:
        wd = w * math.sqrt(1 - damping * damping)
        z = math.exp(-damping * w * time)
        return target + z * (y * math.cos(wd * time) +
                            (velocity + damping * w * y) / wd * math.sin(wd * time))
    if damping == 1:
        return target + math.exp(-w * time) * (y + (velocity + w * y) * time)
    q = math.sqrt(damping * damping - 1)
    r1, r2 = -w * (damping - q), -w * (damping + q)
    a = (velocity - r2 * y) / (r1 - r2)
    return target + a * math.exp(r1 * time) + (y - a) * math.exp(r2 * time)


def overlap(time: float, *, start: float = 0, amplitude: float = 1,
            frequency: float = 3, decay: float = 5) -> float:
    """A settling secondary-motion impulse for ears, hair, antennae or cloth."""
    _finite(time, start, amplitude, frequency, decay)
    if frequency <= 0 or decay < 0:
        raise ValueError('Frequency must be positive and decay nonnegative')
    t = time - start
    return 0.0 if t < 0 else amplitude * math.exp(-decay * t) * math.sin(math.tau * frequency * t)


class PathMotion:
    """Constant-distance travel on one or more joined cubic Bézier segments.

    Supply four points for one cubic, seven for two, and so on. Arc length is a
    polyline approximation controlled by samples_per_segment. No Skia required.
    sample(progress) returns (x, y, tangent_angle_degrees); progress is clamped.
    """
    def __init__(self, points, *, samples_per_segment: int = 120):
        self.points = tuple(tuple(map(float, p)) for p in points)
        if len(self.points) < 4 or (len(self.points) - 1) % 3:
            raise ValueError('Use 3*n+1 points for joined cubic segments')
        if any(len(p) != 2 for p in self.points):
            raise ValueError('Path points must be 2D')
        _finite(*(v for p in self.points for v in p))
        if isinstance(samples_per_segment, bool) or not isinstance(samples_per_segment, int) or samples_per_segment < 4:
            raise ValueError('samples_per_segment must be an integer >= 4')
        self._samples = []
        self._lengths = [0.0]
        for segment in range((len(self.points) - 1) // 3):
            for i in range(samples_per_segment + 1):
                if segment and i == 0:
                    continue
                t = i / samples_per_segment
                p = self._point(segment, t)
                if self._samples:
                    prev = self._samples[-1][2]
                    self._lengths.append(self._lengths[-1] + math.dist(prev, p))
                self._samples.append((segment, t, p))
        self.length = self._lengths[-1]

    def _point(self, segment, t):
        p = self.points[segment * 3:segment * 3 + 4]
        u = 1 - t
        return tuple(u**3 * p[0][j] + 3*u*u*t*p[1][j] + 3*u*t*t*p[2][j] + t**3*p[3][j] for j in (0, 1))

    def sample(self, progress):
        _finite(progress)
        distance = min(1, max(0, progress)) * self.length
        i = min(len(self._samples) - 1, bisect_left(self._lengths, distance))
        if i == 0 or self.length == 0:
            segment, t, p = self._samples[i]
        else:
            a, b = self._samples[i-1], self._samples[i]
            fraction = (distance - self._lengths[i-1]) / max(1e-12, self._lengths[i] - self._lengths[i-1])
            segment = b[0]
            t = (a[1] if a[0] == b[0] else 0) * (1 - fraction) + b[1] * fraction
            p = self._point(segment, t)
        q = self.points[segment*3:segment*3+4]
        u = 1 - t
        dx, dy = (3*u*u*(q[1][j]-q[0][j])+6*u*t*(q[2][j]-q[1][j])+3*t*t*(q[3][j]-q[2][j]) for j in (0, 1))
        return p[0], p[1], math.degrees(math.atan2(dy, dx))

    __call__ = sample


@dataclass(frozen=True)
class Particle:
    index: int
    x: float
    y: float
    age: float
    life: float
    size: float
    rotation: float
    opacity: float
    color: str


class ParticleSystem:
    """Seeded, random-access emitter: smoke, rain, sparks, bubbles, dust, etc.

    Each particle's birth and initial state depends only on seed/index. Sampling
    t=5, t=1, t=5 yields identical states, including after seeking or parallel work.
    A custom painter(canvas, particle) can draw any shape instead of a dot.
    """
    def __init__(self, *, seed=1, rate=12, origin=(0, 0), spread=(0, 0),
                 velocity=((0, 0), (-60, -20)), acceleration=(0, 0),
                 lifetime=(1, 3), size=(2, 6), colors=('#fff3c4',),
                 start=0, end=None, fade=True, max_particles=10000):
        _finite(rate, *origin, *spread, *acceleration, *lifetime, *size, start,
                *(v for pair in velocity for v in pair))
        if rate <= 0 or min(lifetime) <= 0 or min(size) < 0 or start < 0:
            raise ValueError('Rate/lifetime must be positive; size/start nonnegative')
        if any(v < 0 for v in spread) or not colors:
            raise ValueError('Spread must be nonnegative and colors nonempty')
        if any(a > b for a, b in (lifetime, size, *velocity)):
            raise ValueError('Range minimum cannot exceed maximum')
        if end is not None and (not math.isfinite(end) or end < start):
            raise ValueError('End must be finite and >= start')
        if not isinstance(max_particles, int) or max_particles <= 0:
            raise ValueError('max_particles must be a positive integer')
        if math.ceil(max(lifetime) * rate) > max_particles:
            raise ValueError('Emitter exceeds max_particles; lower rate/lifetime or raise limit')
        self.seed, self.rate, self.origin, self.spread = int(seed), rate, origin, spread
        self.velocity, self.acceleration, self.lifetime, self.size = velocity, acceleration, lifetime, size
        self.colors, self.start, self.end, self.fade = tuple(colors), start, end, fade

    def sample(self, time):
        _finite(time)
        if time < self.start:
            return ()
        first = max(0, math.ceil((time - self.start - max(self.lifetime)) * self.rate))
        last_time = min(time, self.end) if self.end is not None else time
        last = math.floor((last_time - self.start) * self.rate)
        result = []
        for i in range(first, last + 1):
            rng = random.Random((self.seed * 0x9E3779B1 + i * 0x85EBCA77) & 0xffffffffffffffff)
            age = time - (self.start + i / self.rate)
            life = rng.uniform(*self.lifetime)
            if age < 0 or age >= life:
                continue
            x = self.origin[0] + rng.uniform(-self.spread[0], self.spread[0])
            y = self.origin[1] + rng.uniform(-self.spread[1], self.spread[1])
            vx, vy = (rng.uniform(*pair) for pair in self.velocity)
            x += vx*age + .5*self.acceleration[0]*age*age
            y += vy*age + .5*self.acceleration[1]*age*age
            size = rng.uniform(*self.size)
            rotation = rng.uniform(0, 360) + age*rng.uniform(-80, 80)
            alpha = min(1, age/.12, (life-age)/.4) if self.fade else 1
            result.append(Particle(i, x, y, age, life, size, rotation, max(0, alpha), rng.choice(self.colors)))
        return tuple(result)

    def draw(self, canvas, time, painter: Callable | None = None):
        from .drawing import color
        for p in self.sample(time):
            if painter:
                with canvas.opacity(p.opacity):
                    painter(canvas, p)
            else:
                base = color(p.color)
                alpha = round(((base >> 24) & 255) * p.opacity)
                canvas.ellipse(p.x, p.y, p.size, p.size, (base & 0xffffff) | (alpha << 24))

class StaticLayer:
    """Cache a time-independent painter at an output-aware raster resolution.

    ``layer = StaticLayer(painter, width=1280, height=720)``; call ``layer(c)``
    inside your scene. painter receives a fresh Canvas and must be independent of
    time. Scale is rounded UP in quarter-step buckets by default, preserving
    detail during modest camera zooms without rebuilding for every frame.
    Translation/rotation do not invalidate the layer. The LRU pixel budget is
    per layer. Layers larger than the budget still draw but are not retained.
    For a paper overlay use painter=lambda c: c.paper(.12) on the default
    transparent layer. Canvas.paper uses inexpensive black source-over grain.
    """
    def __init__(self, painter, *, width=1280, height=720, seed=1,
                 blend_mode='src_over', scale_step=.25,
                 max_cache_bytes=64 * 1024 * 1024):
        from collections import OrderedDict
        _finite(width, height, scale_step)
        if min(width, height, scale_step) <= 0:
            raise ValueError('Layer dimensions and scale_step must be positive')
        if not isinstance(max_cache_bytes, int) or max_cache_bytes < 0:
            raise ValueError('max_cache_bytes must be a nonnegative integer')
        if blend_mode not in ('src_over', 'multiply', 'screen', 'plus'):
            raise ValueError('Unknown StaticLayer blend mode')
        if not callable(painter):
            raise TypeError('Layer painter must be callable')
        self.painter, self.width, self.height, self.seed = painter, width, height, seed
        self.blend_mode, self.scale_step, self.max_cache_bytes = blend_mode, scale_step, max_cache_bytes
        self._cache, self._bytes = OrderedDict(), 0
        self.hits = self.misses = 0

    def clear_cache(self):
        self._cache.clear()
        self._bytes = 0

    @property
    def cache_info(self):
        return {'entries': len(self._cache), 'bytes': self._bytes,
                'hits': self.hits, 'misses': self.misses}

    def draw(self, canvas, time=0):
        import skia
        from .drawing import Canvas
        m = canvas.raw.getTotalMatrix().get9()
        if any(abs(v)>1e-12 for v in (m[6],m[7])):
            raise ValueError('StaticLayer requires an affine Canvas transform')
        # Largest singular value of the affine linear part: sufficient pixel
        # density for anisotropic scale, skew and rotation alike.
        a,b,d,e=m[0],m[1],m[3],m[4]
        trace=a*a+b*b+d*d+e*e
        determinant=(a*e-b*d)**2
        scale=math.sqrt(max(0,(trace+math.sqrt(max(0,trace*trace-4*determinant)))/2))
        if scale==0:
            return
        scale=math.ceil(scale/self.scale_step-1e-10)*self.scale_step
        w,h=max(1,math.ceil(self.width*scale)),max(1,math.ceil(self.height*scale))
        key=(w,h,canvas.roughness,canvas.stroke_scale)
        if key in self._cache:
            self.hits+=1
            image=self._cache.pop(key)
            self._cache[key]=image
        else:
            self.misses+=1
            surface=skia.Surface(w,h)
            if surface is None:
                raise MemoryError(f'Unable to allocate static layer {w}x{h}')
            raw=surface.getCanvas()
            raw.clear(skia.ColorTRANSPARENT)
            raw.scale(w/self.width,h/self.height)
            child=Canvas(raw,self.width,self.height,time=0,seed=self.seed)
            child.roughness=canvas.roughness
            child.stroke_scale=canvas.stroke_scale
            self.painter(child)
            image=surface.makeImageSnapshot()
            size=w*h*4
            if size<=self.max_cache_bytes:
                while self._cache and self._bytes+size>self.max_cache_bytes:
                    old_key,_=self._cache.popitem(last=False)
                    self._bytes-=old_key[0]*old_key[1]*4
                self._cache[key]=image
                self._bytes+=size
        modes={'src_over':skia.BlendMode.kSrcOver,'multiply':skia.BlendMode.kMultiply,
               'screen':skia.BlendMode.kScreen,'plus':skia.BlendMode.kPlus}
        paint=skia.Paint(AntiAlias=True,BlendMode=modes[self.blend_mode])
        canvas.raw.drawImageRect(image,skia.Rect.MakeWH(self.width,self.height),
                                 skia.SamplingOptions(skia.FilterMode.kLinear),paint)

    __call__=draw
