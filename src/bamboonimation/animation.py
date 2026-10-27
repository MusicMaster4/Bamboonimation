"""Deterministic, random-access animation channels and motion helpers."""
from __future__ import annotations
from dataclasses import dataclass
from bisect import bisect_right
import math
import re
from typing import Any, Callable


def linear(t): return t

def smooth(t): return t*t*(3-2*t)

def smoother(t): return t*t*t*(t*(t*6-15)+10)

def ease_in(t): return t*t*t

def ease_out(t): return 1-(1-t)**3

def back(t):
    c=1.70158
    return 1+(c+1)*(t-1)**3+c*(t-1)**2

def elastic(t):
    if t in (0,1): return t
    return 2**(-10*t)*math.sin((t*10-.75)*(2*math.pi/3))+1

def bounce(t):
    n,d=7.5625,2.75
    if t<1/d: return n*t*t
    if t<2/d: t-=1.5/d; return n*t*t+.75
    if t<2.5/d: t-=2.25/d; return n*t*t+.9375
    t-=2.625/d; return n*t*t+.984375

EASINGS={'linear':linear,'smooth':smooth,'smoother':smoother,'in':ease_in,'out':ease_out,
         'back':back,'elastic':elastic,'bounce':bounce,'hold':lambda t:0.0,'step':lambda t:0.0}


def easing(value: str | Callable):
    if callable(value): return value
    try: return EASINGS[value]
    except KeyError: raise ValueError(f'Unknown easing {value!r}; choose {", ".join(EASINGS)}') from None


def mix(a:Any,b:Any,t:float):
    """Interpolate numbers, tuples and #RRGGBB[AA] colors; hold other values."""
    if isinstance(a,bool) or isinstance(b,bool): return b if t>=1 else a
    if isinstance(a,(int,float)) and isinstance(b,(int,float)): return a+(b-a)*t
    if isinstance(a,(tuple,list)) and isinstance(b,(tuple,list)) and len(a)==len(b):
        return tuple(mix(x,y,t) for x,y in zip(a,b))
    if isinstance(a,str) and isinstance(b,str) and re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})',a) and re.fullmatch(r'#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})',b):
        def rgba(s):
            s=s[1:]
            if len(s) in (3,4): s=''.join(c*2 for c in s)
            if len(s)==6: s+='ff'
            if len(s)!=8: raise ValueError('Colors must use #RGB, #RGBA, #RRGGBB or #RRGGBBAA')
            return [int(s[i:i+2],16) for i in range(0,8,2)]
        return '#'+''.join(f'{max(0,min(255,round(x+(y-x)*t))):02x}' for x,y in zip(rgba(a),rgba(b)))
    return b if t>=1 else a

@dataclass(frozen=True)
class Keyframe:
    time: float
    value: Any
    ease: str | Callable = 'smooth'

class Track:
    """An ordered channel. A destination key's easing controls its incoming segment."""
    def __init__(self, default=0, keys=None, interpolator=mix):
        self.default=default
        self.interpolate=interpolator
        self.keys: list[Keyframe]=[]
        if keys:
            for key in keys:
                if isinstance(key,Keyframe): self.add(key.time,key.value,key.ease)
                else: self.add(*key)

    def add(self,time,value,ease='smooth'):
        time=float(time)
        if not math.isfinite(time) or time<0: raise ValueError('Keyframe time must be finite and nonnegative')
        easing(ease)
        key=Keyframe(time,value,ease)
        times=[k.time for k in self.keys]
        i=bisect_right(times,time)
        if i and times[i-1]==time: self.keys[i-1]=key
        else: self.keys.insert(i,key)
        return self

    def value(self,time):
        if not math.isfinite(float(time)): raise ValueError('Sample time must be finite')
        if not self.keys: return self.default
        i=bisect_right([k.time for k in self.keys],time)
        if i==0:
            key=self.keys[0]
            if key.time==0 or time<=0: return self.default if key.time>0 else key.value
            return self.interpolate(self.default,key.value,easing(key.ease)(max(0,time/key.time)))
        if i==len(self.keys): return self.keys[-1].value
        a,b=self.keys[i-1:i+1]
        if time==a.time: return a.value
        return self.interpolate(a.value,b.value,easing(b.ease)((time-a.time)/(b.time-a.time)))

    __call__=value

    def tween(self,to,start,duration,ease='smooth'):
        if not math.isfinite(duration) or duration<=0: raise ValueError('Tween duration must be positive and finite')
        initial=self.value(start)
        self.add(start,initial,'linear')
        self.add(start+duration,to,ease)
        return self


def cycle(time:float,period:float,phase=0.0):
    if not math.isfinite(period) or period<=0: raise ValueError('Period must be positive and finite')
    return (time/period+phase)%1


def pingpong(time,period=1):
    p=cycle(time,period)
    return 1-abs(2*p-1)


def cubic_bezier(points,t):
    if len(points)!=4: raise ValueError('Cubic Bezier requires four points')
    p0,p1,p2,p3=points; u=1-t
    return tuple(u**3*p0[i]+3*u*u*t*p1[i]+3*u*t*t*p2[i]+t**3*p3[i] for i in (0,1))


def follow_path(points,time,start=0,duration=1,ease='smooth'):
    if duration<=0: raise ValueError('Path duration must be positive')
    return cubic_bezier(points,easing(ease)(max(0,min(1,(time-start)/duration))))


def stagger(items,delay,action,start=0):
    """Apply action(item, scheduled_time) without storing render-time state."""
    for i,item in enumerate(items): action(item,start+i*delay)
    return items
