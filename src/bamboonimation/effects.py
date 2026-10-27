"""Directed 2D ink effects: sampled poses, timed impacts and analytic motion.

These helpers execute artistic decisions. They do not automatically provide a
film's acting, replacement drawings or stylistic fidelity.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass
import math
import random
import skia
from .drawing import color, svg_path


def _finite(*values):
    if not all(math.isfinite(float(v)) for v in values):
        raise ValueError('Effect parameters must be finite')


def _alpha(value, opacity):
    base=color(value)
    return (base & 0xffffff) | (round(((base >> 24) & 255)*opacity) << 24)


def camera_shake(time, *, at=0, duration=.3, amplitude=8, frequency=24,
                 seed=1, rotation=.25):
    """Return (dx,dy,degrees), with a smooth bounded decay and no frame history.

    amplitude bounds translation independently on each axis; rotation bounds
    angle. Values are exactly zero outside [at, at+duration). frequency is Hz.
    Add the result to an authored camera rather than replacing its motion.
    """
    _finite(time,at,duration,amplitude,frequency,rotation)
    if duration<=0 or frequency<=0 or amplitude<0 or rotation<0:
        raise ValueError('Duration/frequency must be positive and amplitudes nonnegative')
    t=time-at
    if t<0 or t>=duration:
        return 0.,0.,0.
    rng=random.Random(int(seed))
    phase=[rng.uniform(0,math.tau) for _ in range(6)]
    envelope=(1-t/duration)**2
    def axis(i):
        return (.72*math.sin(math.tau*frequency*t+phase[i])+
                .28*math.sin(math.tau*frequency*1.73*t+phase[i+3]))*envelope
    return amplitude*axis(0), amplitude*axis(1), rotation*axis(2)


def speed_lines(canvas,time,*,center=(640,360),count=24,radius=(100,800),
                length=(35,150),color='#ffffff',width=(1,3),seed=1,speed=160,
                exposure=24,curve=.12,opacity=.5,angles=(0,360)):
    """Curved radial ink trails with independently varied weight and length.

    Angles are degrees; radius/length/width are (minimum,maximum). Exposure
    quantizes only the effect's drawings; 0 leaves motion continuously sampled.
    Negative speed reverses travel. Clip the canvas to keep a chosen region clear.
    This is directed motion notation, not an automatic substitute for smears.
    """
    _finite(time,*center,*radius,*length,*width,speed,exposure,curve,opacity,*angles)
    if not isinstance(count,int) or isinstance(count,bool) or not 0<=count<=10000:
        raise ValueError('count must be an integer between 0 and 10000')
    if radius[0]<0 or radius[1]<=radius[0] or length[0]<0 or width[0]<=0:
        raise ValueError('Radius must increase; lengths nonnegative and widths positive')
    if length[1]<length[0] or width[1]<width[0] or angles[1]<angles[0]:
        raise ValueError('Range maximum must not be below minimum')
    if exposure<0 or not 0<=opacity<=1:
        raise ValueError('Exposure must be nonnegative and opacity in [0,1]')
    t=math.floor(time*exposure+1e-9)/exposure if exposure else time
    rng=random.Random(int(seed))
    span=radius[1]-radius[0]
    ink=_alpha(color,opacity)
    for i in range(count):
        a=math.radians(rng.uniform(*angles))
        r=radius[0]+(rng.uniform(0,span)+speed*t)%span
        size=rng.uniform(*length)
        weight=rng.uniform(*width)
        bend=rng.uniform(-1,1)*size*curve
        dx,dy=math.cos(a),math.sin(a)
        nx,ny=-dy,dx
        x,y=center[0]+dx*r,center[1]+dy*r
        path=skia.Path(); path.moveTo(x,y)
        path.cubicTo(x+dx*size*.3+nx*bend,y+dy*size*.3+ny*bend,
                     x+dx*size*.75+nx*bend*.3,y+dy*size*.75+ny*bend*.3,
                     x+dx*size,y+dy*size)
        canvas.path(path,None,ink,weight)


@contextmanager
def _ink_layer(canvas,ink,opacity=1):
    with canvas.saved():
        paint=skia.Paint(Alphaf=opacity)
        if ink is not None:
            paint.setColorFilter(skia.ColorFilters.Blend(color(ink),skia.BlendMode.kSrcIn))
        canvas.raw.saveLayer(None,paint)
        yield canvas


def impact_flash(canvas,time,*,at,frames=2,fps=24,background='#ffffff',
                 ink='#000000',painter=None):
    """Draw a bounded impact exposure and return whether it was active.

    Call this before the ordinary frame and return early when True. painter(c,t)
    can be a dedicated replacement drawing; ink recolors its nontransparent
    pixels. Set ink=None to preserve its colors. Set background=None for alpha.
    The active interval is [at, at+frames/fps), measured in scene seconds.
    """
    _finite(time,at,fps)
    if not isinstance(frames,int) or isinstance(frames,bool) or frames<=0 or fps<=0:
        raise ValueError('frames must be a positive integer and fps positive')
    if painter is not None and not callable(painter):
        raise TypeError('painter must be callable')
    elapsed=time-at
    if elapsed<0 or elapsed*fps>=frames-1e-9:
        return False
    with canvas.saved():
        if background is not None:
            canvas.rect(0,0,canvas.width,canvas.height,background)
        if painter is not None:
            with _ink_layer(canvas,ink):
                painter(canvas,time)
    return True


def motion_echo(canvas,painter,time,*,samples=3,spacing=1/48,opacity=.16,
                offset=(0,0),ink=None):
    """Draw earlier poses behind the current one, without keeping prior frames.

    painter(canvas,sampled_time) must be deterministic and draw only the subject
    whose silhouette should trail. Call painter(canvas,time) afterwards yourself.
    offset is the additional translation per sample. Earlier echoes are fainter.
    Each echo uses a temporary compositing layer; keep samples low for speed.
    """
    _finite(time,spacing,opacity,*offset)
    if not isinstance(samples,int) or isinstance(samples,bool) or not 0<=samples<=64:
        raise ValueError('samples must be an integer between 0 and 64')
    if spacing<=0 or not 0<=opacity<=1:
        raise ValueError('spacing must be positive and opacity in [0,1]')
    if not callable(painter):
        raise TypeError('painter must be callable')
    for i in range(samples,0,-1):
        t=time-i*spacing
        if t<0:
            continue
        with canvas.saved():
            canvas.translate(offset[0]*i,offset[1]*i)
            with _ink_layer(canvas,ink,opacity*(samples-i+1)/max(1,samples)):
                painter(canvas,t)


def hatch(canvas,path,*,spacing=8,angle=-30,color='#302d3c',width=1,
          seed=1,jitter=.8):
    """Clip irregular scratch-ink strokes to any SVG/skia.Path silhouette.

    The artist supplies the shadow shape; hatching does not infer lighting.
    Seeded jitter preserves the same mark layout when drawing out of order.
    Spacing and width are logical scene units. Curves remain in the clip path.
    """
    _finite(spacing,angle,width,jitter)
    if spacing<=0 or width<=0 or jitter<0:
        raise ValueError('Spacing/width must be positive and jitter nonnegative')
    path=svg_path(path) if isinstance(path,str) else path
    bounds=path.getBounds()
    if bounds.isEmpty():
        return
    extent=math.hypot(bounds.width(),bounds.height())*.55+spacing*2
    count=math.ceil(2*extent/spacing)+1
    if count>100000:
        raise ValueError('Hatch density exceeds 100000 strokes; increase spacing')
    rng=random.Random(int(seed))
    with canvas.clip(path):
        with canvas.transform(bounds.centerX(),bounds.centerY(),rotation=angle):
            for i in range(count):
                x=-extent+i*spacing+rng.uniform(-jitter,jitter)
                y=rng.uniform(-jitter,jitter)
                canvas.line([(x,-extent+y),(x+rng.uniform(-jitter,jitter),extent+y)],
                            color,width*rng.uniform(.7,1.3))


@dataclass(frozen=True)
class FollowThrough:
    """A delayed numeric/tuple channel with a small analytic trailing overshoot.

    source(t) is sampled at t-delay and t-2*delay; no integrator state is retained.
    This is a stylized delay filter, not a physical spring. delay is seconds.
    """
    source: object
    delay: float=.08
    overlap: float=.2

    def __post_init__(self):
        _finite(self.delay,self.overlap)
        if self.delay<=0 or not callable(self.source):
            raise ValueError('source must be callable and delay positive')

    def __call__(self,time):
        _finite(time)
        a=self.source(max(0,time-self.delay))
        b=self.source(max(0,time-2*self.delay))
        def lag(x,y):
            if isinstance(x,(tuple,list)) and isinstance(y,(tuple,list)) and len(x)==len(y):
                return tuple(lag(u,v) for u,v in zip(x,y))
            if isinstance(x,(int,float)) and isinstance(y,(int,float)):
                return x+(x-y)*self.overlap
            raise TypeError('FollowThrough source must return matching numeric values or tuples')
        return lag(a,b)
