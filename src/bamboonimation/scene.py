"""Retained scene graph with independently sampleable animation channels."""
from __future__ import annotations
from contextlib import nullcontext
import math
from numbers import Real
from typing import Callable
from .animation import Track
from .drawing import Canvas,morph_path

_TRANSFORMS={'x','y','rotation','sx','sy','opacity'}
_RESERVED={'parent','children','tracks','painter','name'}

def _check_property(prop,value):
    if prop in _TRANSFORMS and (isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value)):
        raise ValueError(f'{prop} must be a finite number')
    if prop in ('visible','hold') and not isinstance(value,bool): raise ValueError(f'{prop} must be a boolean')
    if prop=='pivot':
        try:
            valid=len(value)==2 and all(not isinstance(v,bool) and isinstance(v,Real) and math.isfinite(v) for v in value)
        except TypeError: valid=False
        if not valid: raise ValueError('pivot must contain two finite numbers')
    if prop in ('fps','zoom','depth','start'):
        if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value):
            raise ValueError(f'{prop} must be a finite number')
        if prop in ('fps','zoom') and value<=0: raise ValueError(f'{prop} must be positive')
    if prop=='frame' and value is not None and (isinstance(value,bool) or not isinstance(value,int)):
        raise ValueError('frame must be an integer or None')

class Node:
    """A drawable local coordinate system with sampleable public channels.

    Rotations are clockwise degrees. Children inherit the parent's transform.
    ``at`` stores absolute poses; ``animate`` interpolates from the current channel
    value at its start. Sampling never mutates the authored pose or channels.
    Identifiers and structural collections are static. Built-in drawing and
    transform properties are sampled by their nodes; custom painter properties
    must be read explicitly through ``value(property, time)``.
    """
    def __init__(self,*,x=0,y=0,rotation=0,sx=1,sy=1,opacity=1,pivot=(0,0),
                 visible=True,name=None,painter:Callable|None=None):
        self.x=x; self.y=y; self.rotation=rotation; self.sx=sx; self.sy=sy
        self.opacity=opacity; _check_property('pivot',pivot); self.pivot=tuple(pivot); self.visible=visible; self.name=name
        for prop in _TRANSFORMS|{'visible'}: _check_property(prop,getattr(self,prop))
        self.painter=painter; self.parent=None; self.children=[]; self.tracks={}

    def channel(self,prop):
        if prop.startswith('_') or prop in _RESERVED or prop in getattr(self,'_static_properties',()) or not hasattr(self,prop) or callable(getattr(self,prop)):
            raise ValueError(f'{type(self).__name__} has no animatable property {prop!r}')
        if prop not in self.tracks:
            self.tracks[prop]=Track(getattr(self,prop),interpolator=(lambda a,b,u:a)) if prop in ('visible','hold') else Track(getattr(self,prop))
        return self.tracks[prop]

    def at(self,time,**props):
        for prop,value in props.items():
            _check_property(prop,value)
            self.channel(prop).add(time,value)
        return self

    def animate(self,prop,to,start=0,duration=1,ease='smooth'):
        _check_property(prop,to)
        self.channel(prop).tween(to,start,duration,ease)
        return self

    def value(self,prop,time):
        return self.tracks[prop](time) if prop in self.tracks else getattr(self,prop)

    def pose(self,time):
        values={k:self.value(k,time) for k in ('x','y','rotation','sx','sy','opacity','pivot')}
        for prop,value in values.items(): _check_property(prop,value)
        return values

    def add(self,*nodes):
        for node in nodes:
            if not isinstance(node,Node): raise TypeError('Only Node instances can be added to a scene graph')
            ancestor=self
            while ancestor is not None:
                if ancestor is node: raise ValueError('A scene graph cannot contain cycles')
                ancestor=ancestor.parent
            if node.parent is self: continue
            if node.parent is not None: raise ValueError('Node already has a parent; remove it before reparenting')
            node.parent=self; self.children.append(node)
        return self

    def remove(self,node):
        self.children.remove(node); node.parent=None
        return self

    def find(self,name):
        if self.name==name: return self
        for child in self.children:
            result=child.find(name)
            if result is not None: return result
        return None

    def world_point(self,point=(0,0),time=0):
        """Transform a local point through all graph ancestors (excluding camera)."""
        x,y=point; current=self
        while current is not None:
            p=current.pose(time)
            x=(x-p['pivot'][0])*p['sx']; y=(y-p['pivot'][1])*p['sy']
            a=math.radians(p['rotation']); co,si=math.cos(a),math.sin(a)
            x,y=x*co-y*si+p['x'],x*si+y*co+p['y']
            current=current.parent
        return x,y

    def local_point(self,point,time=0):
        """Invert ``world_point``; zero-scale transforms cannot be inverted."""
        chain=[]; current=self
        while current is not None: chain.append(current); current=current.parent
        x,y=point
        for current in reversed(chain):
            p=current.pose(time)
            if p['sx']==0 or p['sy']==0: raise ValueError('Cannot invert a zero-scale transform')
            x-=p['x']; y-=p['y']
            a=math.radians(-p['rotation']); co,si=math.cos(a),math.sin(a)
            x,y=x*co-y*si,x*si+y*co
            x=x/p['sx']+p['pivot'][0]; y=y/p['sy']+p['pivot'][1]
        return x,y

    def draw(self,canvas,time):
        visible=self.value('visible',time)
        _check_property('visible',visible)
        if not visible: return
        pose=self.pose(time)
        opacity=max(0,min(1,pose['opacity']))
        if opacity<=0: return
        with canvas.transform(pose['x'],pose['y'],pose['rotation'],pose['sx'],pose['sy']):
            canvas.translate(-pose['pivot'][0],-pose['pivot'][1])
            with canvas.opacity(opacity) if opacity<1 else nullcontext():
                self.paint(canvas,time)
                for child in self.children: child.draw(canvas,time)

    def paint(self,canvas,time):
        if self.painter is not None: self.painter(canvas,time)

class Group(Node):
    def __init__(self,*children,**kwargs):
        super().__init__(**kwargs); self.add(*children)

class Path(Node):
    def __init__(self,data,fill=None,stroke='#302d3c',width=3,**kwargs):
        super().__init__(**kwargs); self.data=data; self.fill=fill; self.stroke=stroke; self.width=width
    def channel(self,prop):
        if prop=='data':
            if prop not in self.tracks: self.tracks[prop]=Track(self.data,interpolator=morph_path)
            return self.tracks[prop]
        return super().channel(prop)
    def morph(self,data,start=0,duration=1,ease='smooth'):
        morph_path(self.value('data',start),data,0)
        return self.animate('data',data,start,duration,ease)
    def paint(self,c,t): c.path(self.value('data',t),self.value('fill',t),self.value('stroke',t),self.value('width',t))

class Ellipse(Node):
    def __init__(self,rx=20,ry=None,fill='#eebc72',stroke=None,width=3,**kwargs):
        super().__init__(**kwargs); self.rx=rx; self.ry=rx if ry is None else ry
        self.fill=fill; self.stroke=stroke; self.width=width
    def paint(self,c,t): c.ellipse(0,0,self.value('rx',t),self.value('ry',t),self.value('fill',t),self.value('stroke',t),self.value('width',t))

class Rect(Node):
    def __init__(self,width=100,height=100,fill='#eebc72',stroke=None,stroke_width=3,radius=0,**kwargs):
        super().__init__(**kwargs); self.width=width; self.height=height
        self.fill=fill; self.stroke=stroke; self.stroke_width=stroke_width; self.radius=radius
    def paint(self,c,t): c.rect(0,0,self.value('width',t),self.value('height',t),self.value('fill',t),self.value('stroke',t),self.value('stroke_width',t),self.value('radius',t))

class Text(Node):
    def __init__(self,text,size=24,fill='#302d3c',font=None,**kwargs):
        super().__init__(**kwargs); self.text=text; self.size=size; self.fill=fill; self.font=font
    def paint(self,c,t): c.text(self.value('text',t),0,0,self.value('size',t),self.value('fill',t),self.value('font',t))

class Image(Node):
    def __init__(self,source,width=None,height=None,**kwargs):
        super().__init__(**kwargs); self.source=str(source); self.width=width; self.height=height
    def paint(self,c,t): c.image(self.value('source',t),0,0,self.value('width',t),self.value('height',t))

class Sprite(Node):
    """Replacement drawings sampled at a fixed exposure rate, or explicit keyframes.

    Each frame is an image filename or a ``painter(canvas, time)`` callable.
    ``hold=False`` loops; ``hold=True`` keeps the final drawing after the cycle.
    """
    _static_properties={'frames'}

    def __init__(self,frames,fps=12,start=0,hold=False,width=None,height=None,**kwargs):
        super().__init__(**kwargs)
        if not frames: raise ValueError('Sprite requires at least one drawing')
        _check_property('fps',fps); _check_property('start',start); _check_property('hold',hold)
        self.frames=list(frames); self.fps=fps; self.start=start; self.hold=hold; self.width=width; self.height=height
        self.frame=None
    def channel(self,prop):
        if prop=='frame':
            if prop not in self.tracks: self.tracks[prop]=Track(self.frame,interpolator=lambda a,b,u:a)
            return self.tracks[prop]
        return super().channel(prop)
    def paint(self,c,t):
        index=self.value('frame',t)
        _check_property('frame',index)
        if index is None:
            fps,start,hold=(self.value(p,t) for p in ('fps','start','hold'))
            for prop,value in (('fps',fps),('start',start),('hold',hold)): _check_property(prop,value)
            # fps is an instantaneous sampling rate, not a speed integrated
            # across earlier keys. Use explicit frame keys for exact timing.
            index=max(0,math.floor((t-start)*fps))
            index=min(index,len(self.frames)-1) if hold else index%len(self.frames)
        if not 0<=index<len(self.frames): raise ValueError(f'Sprite frame {index} is out of range')
        frame=self.frames[index]
        if callable(frame): frame(c,t)
        else: c.image(frame,0,0,self.value('width',t),self.value('height',t))

class Camera:
    """Center-based camera with zoom, rotation and parallax for layered shots."""
    def __init__(self,x=0,y=0,zoom=1,rotation=0):
        self.x=x; self.y=y; self.zoom=zoom; self.rotation=rotation; self.tracks={}
        for prop in ('x','y','zoom','rotation'): _check_property(prop,getattr(self,prop))
    channel=Node.channel
    at=Node.at
    animate=Node.animate
    value=Node.value

    def apply(self,c,t,width,height,depth=1):
        zoom=self.value('zoom',t)
        for prop,value in (('zoom',zoom),('x',self.value('x',t)),('y',self.value('y',t)),('rotation',self.value('rotation',t)),('depth',depth)): _check_property(prop,value)
        c.translate(width/2,height/2)
        c.scale(1+(zoom-1)*depth)
        c.rotate(-self.value('rotation',t)*depth)
        c.translate(-(width/2+(self.value('x',t)-width/2)*depth),
                    -(height/2+(self.value('y',t)-height/2)*depth))

class Layer(Group):
    """A top-level group with camera parallax. Zero depth is screen-fixed."""
    def __init__(self,*children,depth=1,**kwargs):
        super().__init__(*children,**kwargs); _check_property('depth',depth); self.depth=depth

class Scene:
    """One timed composition with a graph, optional direct painter, and audio clips."""
    def __init__(self,width=1280,height=720,duration=12,background='#f2e4cb',seed=1,
                 painter=None,post_painter=None):
        if not all(isinstance(v,Real) and not isinstance(v,bool) and math.isfinite(v) and v>0 for v in (width,height,duration)):
            raise ValueError('Scene width, height and duration must be positive and finite')
        self.width=width; self.height=height; self.duration=duration; self.background=background
        self.seed=seed; self.painter=painter; self.post_painter=post_painter
        self.root=Group(name='root'); self.camera=Camera(width/2,height/2)
        self.audio=[]; self.metadata={}

    @property
    def nodes(self): return self.root.children

    def add(self,*nodes): self.root.add(*nodes); return self

    def find(self,name): return self.root.find(name)

    def draw(self,canvas:Canvas,time:float):
        if not math.isfinite(time): raise ValueError('Scene time must be finite')
        canvas.time=time; canvas.seed=self.seed
        if self.background is not None: canvas.rect(0,0,self.width,self.height,self.background)
        for node in self.nodes:
            with canvas.saved():
                self.camera.apply(canvas,time,self.width,self.height,node.value('depth',time) if isinstance(node,Layer) else 1)
                node.draw(canvas,time)
        if self.painter:
            with canvas.saved():
                self.camera.apply(canvas,time,self.width,self.height)
                self.painter(canvas,time)
        if self.post_painter:
            with canvas.saved(): self.post_painter(canvas,time)
