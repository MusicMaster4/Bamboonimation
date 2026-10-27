"""A small antialiased drawing vocabulary backed by Skia's CPU rasterizer."""
from __future__ import annotations
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
import math
import re
import skia
import numpy as np

_NAMES={'black':'#000000','white':'#ffffff','red':'#ff0000','green':'#008000','blue':'#0000ff',
        'transparent':'#00000000','none':'#00000000','yellow':'#ffff00','gray':'#808080'}

def color(value):
    if value is None: return skia.ColorTRANSPARENT
    if isinstance(value,int): return value
    if isinstance(value,(tuple,list)):
        if len(value) not in (3,4): raise ValueError('Color tuple needs RGB or RGBA')
        return skia.ColorSetARGB(int(value[3]) if len(value)==4 else 255,*map(int,value[:3]))
    value=_NAMES.get(str(value).lower(),str(value))
    if not value.startswith('#'): raise ValueError(f'Use a hex color, got {value!r}')
    value=value[1:]
    if len(value) in (3,4): value=''.join(c*2 for c in value)
    if len(value)==6: value+='ff'
    if len(value)!=8: raise ValueError('Color must use #RGB, #RGBA, #RRGGBB or #RRGGBBAA')
    r,g,b,a=(int(value[i:i+2],16) for i in range(0,8,2))
    return skia.ColorSetARGB(a,r,g,b)

_TOKEN=re.compile(r'[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?')
_ARITY={'M':2,'L':2,'H':1,'V':1,'C':6,'S':4,'Q':4,'T':2,'A':7}

@lru_cache(maxsize=2048)
def svg_path(data:str):
    """Parse standard SVG path data, including relative and elliptical arc commands."""
    tokens=_TOKEN.findall(data)
    residue=_TOKEN.sub('',data).replace(',','').strip()
    if residue: raise ValueError(f'Invalid SVG path token: {residue[:30]!r}')
    path=skia.Path(); i=0; command=None; x=y=0.; ox=oy=0.; prev=None; control=(0.,0.)
    while i<len(tokens):
        if tokens[i].isalpha():
            command=tokens[i]; i+=1
            if command.upper()=='Z':
                path.close(); x,y=ox,oy; prev='Z'; command=None; continue
        if command is None: raise ValueError('SVG path requires a command')
        cmd=command.upper(); relative=command.islower(); n=_ARITY[cmd]
        if i+n>len(tokens) or any(t.isalpha() for t in tokens[i:i+n]):
            raise ValueError(f'SVG {cmd} requires {n} coordinates')
        v=list(map(float,tokens[i:i+n])); i+=n
        if not all(math.isfinite(z) for z in v): raise ValueError('Path coordinates must be finite')
        def point(j): return (v[j]+(x if relative else 0),v[j+1]+(y if relative else 0))
        if cmd=='M':
            x,y=point(0); path.moveTo(x,y); ox,oy=x,y; command='l' if relative else 'L'
        elif cmd=='L': x,y=point(0); path.lineTo(x,y)
        elif cmd=='H': x=v[0]+(x if relative else 0); path.lineTo(x,y)
        elif cmd=='V': y=v[0]+(y if relative else 0); path.lineTo(x,y)
        elif cmd=='C':
            a,b,c=point(0),point(2),point(4); path.cubicTo(*a,*b,*c); control=b; x,y=c
        elif cmd=='S':
            a=(2*x-control[0],2*y-control[1]) if prev in ('C','S') else (x,y)
            b,c=point(0),point(2); path.cubicTo(*a,*b,*c); control=b; x,y=c
        elif cmd=='Q':
            a,b=point(0),point(2); path.quadTo(*a,*b); control=a; x,y=b
        elif cmd=='T':
            a=(2*x-control[0],2*y-control[1]) if prev in ('Q','T') else (x,y)
            b=point(0); path.quadTo(*a,*b); control=a; x,y=b
        elif cmd=='A':
            if v[3] not in (0,1) or v[4] not in (0,1): raise ValueError('SVG arc flags must be 0 or 1')
            tx,ty=v[5]+(x if relative else 0),v[6]+(y if relative else 0)
            path.arcTo(abs(v[0]),abs(v[1]),v[2],skia.Path.ArcSize.kLarge_ArcSize if v[3] else skia.Path.ArcSize.kSmall_ArcSize,
                       skia.PathDirection.kCW if v[4] else skia.PathDirection.kCCW,tx,ty)
            x,y=tx,ty
        prev=cmd
    return path

def morph_path(a,b,amount):
    """Interpolate matching SVG path command topology (including Bezier handles).

    Both paths must use identical commands, coordinate counts and arc flags.
    The paths may represent any subject; no built-in character is required.
    """
    if not isinstance(a,str) or not isinstance(b,str): raise TypeError('Path morphing requires SVG path strings')
    aa,bb=_TOKEN.findall(a),_TOKEN.findall(b)
    if len(aa)!=len(bb): raise ValueError('Morph paths must have identical command topology')
    result=[]; command=None; offset=0
    for x,y in zip(aa,bb):
        if x.isalpha() or y.isalpha():
            if x!=y: raise ValueError('Morph paths must use identical SVG commands')
            command=x.upper(); offset=0; result.append(x)
        else:
            if command=='A' and offset%7 in (3,4):
                if x!=y: raise ValueError('Arc flags must match between morph paths')
                result.append(x)
            else: result.append(f'{float(x)+(float(y)-float(x))*amount:.8g}')
            offset+=1
    # Parse both endpoints at authoring/sample time to reject malformed input.
    svg_path(a); svg_path(b)
    return ' '.join(result)

@lru_cache(maxsize=64)
def _raster_image(path,mtime):
    image=skia.Image.MakeFromEncoded(skia.Data.MakeFromFileName(path))
    if image is None: raise ValueError(f'Cannot decode image: {path}')
    return image

@lru_cache(maxsize=32)
def _svg_picture(path,mtime,viewport_width=None,viewport_height=None):
    """Cache immutable vector recordings, never a mutable shared SVG DOM.

    A dimensionless document without a supplied viewport returns a cached marker;
    its explicitly sized recording has a separate cache key. Pictures remain
    vector commands, so scaling does not rasterize an asset at authoring size.
    """
    dom=skia.SVGDOM.MakeFromStream(skia.FILEStream(path))
    if dom is None: raise ValueError(f'Cannot decode SVG: {path}')
    dimensions=dom.containerSize(); iw,ih=dimensions.width(),dimensions.height()
    if iw<=0 or ih<=0:
        if viewport_width is None or viewport_height is None: return None,0,0
        dom.setContainerSize(skia.Size(viewport_width,viewport_height))
        iw,ih=viewport_width,viewport_height
    recorder=skia.PictureRecorder()
    canvas=recorder.beginRecording(skia.Rect.MakeWH(iw,ih))
    canvas.clipRect(skia.Rect.MakeWH(iw,ih))
    dom.render(canvas)
    return recorder.finishRecordingAsPicture(),iw,ih

@lru_cache(maxsize=32)
def _font(family,size):
    manager=skia.FontMgr.RefDefault()
    face=manager.matchFamilyStyle(family or 'sans-serif',skia.FontStyle())
    return skia.Font(face,float(size))

@lru_cache(maxsize=16)
def _paper(seed,size,amount):
    rng=np.random.default_rng(seed)
    gray=np.clip(rng.normal(218,27,(size,size)),90,255).astype(np.uint8)
    # Multiplying opaque artwork by gray with opacity a is equivalent to
    # compositing black with alpha a*(1-gray). SrcOver is substantially faster
    # in Skia's CPU rasterizer and lets this grain be cached on transparency.
    rgba=np.zeros((size,size,4),np.uint8)
    rgba[:,:,3]=np.rint((255-gray.astype(np.float32))*amount).astype(np.uint8)
    return skia.Image.fromarray(rgba,colorType=skia.ColorType.kN32_ColorType,alphaType=skia.AlphaType.kPremul_AlphaType)

class Canvas:
    """Draw in logical scene units. Output resolution is owned by the renderer.

    ``roughness`` adds seeded pencil-like outline variation. It never changes fills.
    ``paper`` overlays repeatable grain; call once after the completed composition.
    ``stroke_scale`` explicitly scales outline widths and rough displacement.
    Set it to inverse camera zoom for an approximately stable screen outline;
    filled geometry is unaffected. Imported SVG/images and direct raw drawing
    retain their own artwork styling and bypass this wrapper's stroke control.
    """
    def __init__(self,raw,width,height,time=0,seed=1):
        self.raw=raw; self.width=width; self.height=height; self.time=time; self.seed=seed
        self.roughness=0.0; self.boil_fps=0; self._stroke_scale=1.0

    @property
    def stroke_scale(self): return self._stroke_scale

    @stroke_scale.setter
    def stroke_scale(self,value):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:
            raise ValueError('stroke_scale must be a positive finite number')
        self._stroke_scale=float(value)

    def save(self): return self.raw.save()
    def restore(self): self.raw.restore()
    def translate(self,x,y): self.raw.translate(x,y)
    def rotate(self,degrees): self.raw.rotate(degrees)
    def scale(self,x,y=None): self.raw.scale(x,x if y is None else y)

    @contextmanager
    def saved(self):
        """Isolate drawing state, including outline style and unbalanced user saves."""
        count=self.raw.getSaveCount()
        roughness,boil_fps,stroke_scale=self.roughness,self.boil_fps,self.stroke_scale
        self.raw.save()
        try: yield self
        finally:
            self.raw.restoreToCount(count)
            self.roughness,self.boil_fps,self.stroke_scale=roughness,boil_fps,stroke_scale

    @contextmanager
    def transform(self,x=0,y=0,rotation=0,sx=1,sy=None):
        with self.saved():
            self.translate(x,y); self.rotate(rotation); self.scale(sx,sx if sy is None else sy)
            yield self

    @contextmanager
    def opacity(self,value):
        if not math.isfinite(value) or not 0<=value<=1: raise ValueError('Opacity must be between 0 and 1')
        count=self.raw.getSaveCount()
        self.raw.saveLayerAlpha(None,round(value*255))
        try: yield self
        finally: self.raw.restoreToCount(count)

    @contextmanager
    def clip(self,path):
        parsed=svg_path(path) if isinstance(path,str) else path
        with self.saved():
            self.raw.clipPath(parsed,doAntiAlias=True)
            yield self

    def _paint(self,fill,stroke=False,width=3,rough=None):
        p=skia.Paint(AntiAlias=True,Color=color(fill))
        if stroke:
            width*=self.stroke_scale
            p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(width)
            p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
            rough=self.roughness if rough is None else rough
            if rough:
                seed=(int(self.seed)+int(self.time*self.boil_fps))%4294967295
                p.setPathEffect(skia.DiscretePathEffect.Make(max(2*self.stroke_scale,width*2),rough*self.stroke_scale,seed))
        return p

    def path(self,data,fill=None,stroke='#302d3c',width=3,rough=None):
        p=svg_path(data) if isinstance(data,str) else data
        if fill is not None: self.raw.drawPath(p,self._paint(fill))
        if stroke is not None and width>0: self.raw.drawPath(p,self._paint(stroke,True,width,rough))

    def ellipse(self,x,y,rx,ry,fill=None,stroke=None,width=3):
        if rx<0 or ry<0: raise ValueError('Ellipse radii cannot be negative')
        p=skia.Path(); p.addOval(skia.Rect.MakeLTRB(x-rx,y-ry,x+rx,y+ry))
        self.path(p,fill,stroke,width)

    def rect(self,x,y,w,h,fill=None,stroke=None,width=3,radius=0):
        p=skia.Path()
        if radius: p.addRoundRect(skia.Rect.MakeXYWH(x,y,w,h),radius,radius)
        else: p.addRect(skia.Rect.MakeXYWH(x,y,w,h))
        self.path(p,fill,stroke,width)

    def line(self,points,stroke='#302d3c',width=3):
        points=list(points)
        if not points: return
        p=skia.Path(); p.moveTo(*points[0])
        for point in points[1:]: p.lineTo(*point)
        self.path(p,None,stroke,width)

    def polygon(self,points,fill=None,stroke=None,width=3):
        points=list(points)
        if not points: return
        p=skia.Path(); p.moveTo(*points[0])
        for point in points[1:]: p.lineTo(*point)
        p.close(); self.path(p,fill,stroke,width)

    def text(self,text,x,y,size=24,fill='#302d3c',font=None):
        self.raw.drawString(str(text),x,y,_font(font,size),self._paint(fill))

    def text_width(self,text,size=24,font=None): return _font(font,size).measureText(str(text))

    def image(self,path,x,y,w=None,h=None,opacity=1):
        if not math.isfinite(opacity) or not 0<=opacity<=1:
            raise ValueError('Image opacity must be between 0 and 1')
        for value in (w,h):
            if value is not None and (not math.isfinite(value) or value<=0):
                raise ValueError('Image dimensions must be positive and finite')
        file=Path(path).resolve()
        if not file.is_file(): raise FileNotFoundError(file)
        mtime=file.stat().st_mtime_ns
        if file.suffix.lower()=='.svg':
            picture,iw,ih=_svg_picture(str(file),mtime)
            if picture is None:
                if w is None or h is None: raise ValueError('SVG without intrinsic dimensions requires w and h')
                picture,iw,ih=_svg_picture(str(file),mtime,w,h)
            if w is None and h is None: w,h=iw,ih
            elif w is None: w=iw*h/ih
            elif h is None: h=ih*w/iw
            with self.transform(x,y,sx=w/iw,sy=h/ih):
                if opacity==1: self.raw.drawPicture(picture)
                else:
                    with self.opacity(opacity): self.raw.drawPicture(picture)
            return
        img=_raster_image(str(file),mtime)
        iw,ih=img.width(),img.height()
        if w is None and h is None: w,h=iw,ih
        elif w is None: w=iw*h/ih
        elif h is None: h=ih*w/iw
        p=skia.Paint(Alphaf=opacity,AntiAlias=True)
        self.raw.drawImageRect(img,skia.Rect.MakeXYWH(x,y,w,h),skia.SamplingOptions(skia.FilterMode.kLinear),p)

    def gradient_rect(self,x,y,w,h,colors,start=None,end=None,positions=None):
        """Linear gradient over a rectangle; coordinates share the scene space."""
        start=(x,y) if start is None else start; end=(x,y+h) if end is None else end
        p=skia.Paint(AntiAlias=True)
        p.setShader(skia.GradientShader.MakeLinear([start,end],[color(c) for c in colors],positions))
        self.raw.drawRect(skia.Rect.MakeXYWH(x,y,w,h),p)

    def paper(self,amount=.12,seed=None,size=256):
        if not 0<=amount<=1: raise ValueError('Paper amount must be between 0 and 1')
        if not isinstance(size,int) or isinstance(size,bool) or size<=0:
            raise ValueError('Paper tile size must be a positive integer')
        if amount==0: return
        img=_paper(self.seed if seed is None else seed,size,amount)
        # Native image blits keep the fast SrcOver raster path. A repeat image
        # shader can force Skia's slower general raster pipeline on Windows.
        with self.saved():
            self.raw.clipRect(skia.Rect.MakeWH(self.width,self.height))
            for y in range(0,math.ceil(self.height),size):
                for x in range(0,math.ceil(self.width),size):
                    self.raw.drawImage(img,x,y)

    def shadow(self,x,y,rx,ry,opacity=.14,fill='#302d3c'):
        with self.opacity(opacity): self.ellipse(x,y,rx,ry,fill)
