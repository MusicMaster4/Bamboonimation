"""Nonmutating, artist-directed vector deformation for arbitrary 2D artwork.

Control points and explicit anchors use the same mapper. Affine maps reproduce
curves exactly. Nonlinear maps deform the control net; they are not an exact
pointwise image of every point on a Bezier or rational conic curve.
"""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass,field
from numbers import Real
from typing import Callable
import math
import skia
from .drawing import Canvas, color, svg_path


def _number(value, label):
    if isinstance(value,bool) or not isinstance(value,Real) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number')
    return float(value)


def _point(value, label='Point'):
    try:
        if len(value)!=2: raise ValueError(f'{label} must contain two finite numbers')
        return _number(value[0],label),_number(value[1],label)
    except (TypeError,IndexError):
        raise ValueError(f'{label} must contain two finite numbers') from None


def warp_path(source: str | skia.Path,
              mapper: Callable[[float,float],tuple[float,float]]) -> skia.Path:
    """Return a fresh path with its control points mapped by ``mapper(x,y)``.

    Accepts SVG path data or a native Skia path. Moves, lines, quadratic/cubic
    Beziers, rational conics and closed contours retain their original verbs;
    conics retain their weights and the fill rule is preserved. SVG elliptical
    arcs are already represented by Skia as rational conic segments.

    The source is never mutated, including paths obtained from ``svg_path``'s
    shared parse cache. Evaluate from the original source at each absolute time;
    repeatedly warping a previous output would accumulate deformation.

    A nonlinear mapper does NOT map the geometric interior of a curve exactly:
    it maps the authored control net. Raster images, text layout and automatic
    volume preservation are outside this function's contract.
    """
    if not callable(mapper): raise TypeError('mapper must be callable as mapper(x,y)')
    if isinstance(source,str): source=svg_path(source)
    if not isinstance(source,skia.Path): raise TypeError('source must be SVG path data or skia.Path')
    if not source.isFinite(): raise ValueError('Source path coordinates must be finite')
    result=skia.Path()
    result.setFillType(source.getFillType())
    result.setIsVolatile(source.isVolatile())
    iterator=skia.Path.RawIter(source)
    while True:
        verb,points=iterator.next()
        if verb==skia.Path.kDone_Verb: break
        if verb==skia.Path.kClose_Verb:
            result.close(); continue
        # RawIter includes the previous endpoint for drawing verbs. It is
        # already present in result, so map only newly authored control points.
        mapped=[_point(mapper(float(p.x()),float(p.y())),'Mapped point')
                for p in (points if verb==skia.Path.kMove_Verb else points[1:])]
        if verb==skia.Path.kMove_Verb: result.moveTo(*mapped[0])
        elif verb==skia.Path.kLine_Verb: result.lineTo(*mapped[0])
        elif verb==skia.Path.kQuad_Verb: result.quadTo(*mapped[0],*mapped[1])
        elif verb==skia.Path.kConic_Verb:
            result.conicTo(*mapped[0],*mapped[1],iterator.conicWeight())
        elif verb==skia.Path.kCubic_Verb: result.cubicTo(*mapped[0],*mapped[1],*mapped[2])
        else: raise ValueError(f'Unsupported Skia path verb: {verb}')
    return result


@dataclass(frozen=True)
class LatticeWarp:
    """Bilinear displacement grid in source coordinates.

    ``bounds`` is ``(left,top,right,bottom)`` or ``skia.Rect``. ``offsets`` is a
    rectangular grid of at least two rows and two columns of ``(dx,dy)`` values.
    The first row is the top edge; the first column is the left edge.

    ``clamp=True`` extends the nearest edge's DISPLACEMENT outside the bounds;
    it does not clip input coordinates. ``clamp=False`` extrapolates the nearest
    edge cell's bilinear displacement. ``strength`` scales displacement, with
    zero giving identity. Strength may be negative or exceed one intentionally.

    Grids and bounds are normalized to immutable tuples. Use ``with_strength``
    or construct a new grid per absolute time; no integration history is stored.
    ``map`` also accepts a single point tuple, for deforming authored anchors.
    """
    bounds: tuple[float,float,float,float] | skia.Rect
    offsets: tuple[tuple[tuple[float,float],...],...]
    clamp: bool = field(default=True,kw_only=True)
    strength: float = field(default=1.0,kw_only=True)

    def __post_init__(self):
        if isinstance(self.bounds,skia.Rect):
            raw=(self.bounds.left(),self.bounds.top(),self.bounds.right(),self.bounds.bottom())
        else: raw=self.bounds
        try:
            if len(raw)!=4: raise ValueError('Bounds must contain left, top, right, bottom')
            bounds=tuple(_number(v,'Bounds coordinate') for v in raw)
        except TypeError: raise ValueError('Bounds must contain left, top, right, bottom') from None
        left,top,right,bottom=bounds
        if right<=left or bottom<=top or not math.isfinite(right-left) or not math.isfinite(bottom-top):
            raise ValueError('Bounds must have positive finite width and height')
        try:
            rows=tuple(tuple(_point(p,'Lattice offset') for p in row) for row in self.offsets)
        except TypeError: raise ValueError('Offsets must be a rectangular grid of displacement pairs') from None
        if len(rows)<2 or len(rows[0])<2 or any(len(row)!=len(rows[0]) for row in rows):
            raise ValueError('Offsets need at least two rows and two columns with equal row lengths')
        if not isinstance(self.clamp,bool): raise ValueError('clamp must be boolean')
        object.__setattr__(self,'bounds',bounds)
        object.__setattr__(self,'offsets',rows)
        object.__setattr__(self,'strength',_number(self.strength,'Strength'))

    @property
    def rows(self): return len(self.offsets)

    @property
    def columns(self): return len(self.offsets[0])

    def with_strength(self,strength):
        """Return another immutable warp; safe for out-of-order frame sampling."""
        return LatticeWarp(self.bounds,self.offsets,clamp=self.clamp,strength=strength)

    def map(self,x,y=None):
        if y is None: x,y=_point(x)
        else: x,y=_number(x,'Point x'),_number(y,'Point y')
        if self.strength==0: return x,y
        left,top,right,bottom=self.bounds
        u=(x-left)/(right-left)*(self.columns-1)
        v=(y-top)/(bottom-top)*(self.rows-1)
        if self.clamp:
            u=max(0,min(self.columns-1,u)); v=max(0,min(self.rows-1,v))
        col=max(0,min(self.columns-2,math.floor(u)))
        row=max(0,min(self.rows-2,math.floor(v)))
        fx,fy=u-col,v-row
        a,b=self.offsets[row][col:col+2]
        c,d=self.offsets[row+1][col:col+2]
        dx=(a[0]*(1-fx)+b[0]*fx)*(1-fy)+(c[0]*(1-fx)+d[0]*fx)*fy
        dy=(a[1]*(1-fx)+b[1]*fx)*(1-fy)+(c[1]*(1-fx)+d[1]*fx)*fy
        return x+dx*self.strength,y+dy*self.strength

    __call__=map


class WarpCanvas(Canvas):
    """Draw vector artwork through one mapper in a captured parent space.

    Construct inside the desired parent transform. Subsequent nested transforms
    are converted back to that coordinate system before mapping, so a head,
    face, clothing details and hands all share the same deformation. The raw
    Skia canvas and dimensions/time/seed are shared; outline style is copied and
    can be changed independently from the source ``Canvas``.

    Like ``warp_path``, this deforms control nets, not every point along curves.
    Text and imported images (including complete SVG documents) must first be
    supplied as vector outlines; those drawing methods raise explicitly. Direct
    ``raw`` calls remain an intentional, unwarped escape hatch. Stroke widths
    retain Canvas styling rather than following nonlinear stretch.
    """
    def __init__(self,canvas: Canvas,mapper: Callable[[float,float],tuple[float,float]]):
        if not isinstance(canvas,Canvas): raise TypeError('WarpCanvas requires a Canvas')
        if not callable(mapper): raise TypeError('mapper must be callable as mapper(x,y)')
        super().__init__(canvas.raw,canvas.width,canvas.height,canvas.time,canvas.seed)
        self.roughness=canvas.roughness
        self.boil_fps=canvas.boil_fps
        self.stroke_scale=canvas.stroke_scale
        self.mapper=mapper
        self._base_matrix=self.raw.getTotalMatrix()
        self._base_inverse=skia.Matrix()
        if not self._base_matrix.isFinite() or not self._base_matrix.invert(self._base_inverse) or not self._base_inverse.isFinite():
            raise ValueError('WarpCanvas parent transform must be finite and invertible; construct before a zero scale')

    def _warped_path(self,data):
        # B maps the captured parent coordinates to device coordinates. M maps
        # the current shape's local coordinates to device coordinates. Thus
        # P = inverse(B) * M maps local points into the common mapper space.
        current=self.raw.getTotalMatrix()
        relative=skia.Matrix.Concat(self._base_inverse,current)
        inverse=skia.Matrix()
        if not relative.isFinite() or not relative.invert(inverse) or not inverse.isFinite():
            raise ValueError('WarpCanvas nested transform must be finite and invertible; skip drawing at zero scale')
        def local_mapper(x,y):
            parent=_point(tuple(relative.mapXY(x,y)),'Parent-space point')
            mapped=_point(self.mapper(*parent),'Mapped point')
            return tuple(inverse.mapXY(*mapped))
        return warp_path(data,local_mapper)

    def path(self,data,fill=None,stroke='#302d3c',width=3,rough=None):
        super().path(self._warped_path(data),fill,stroke,width,rough)

    @contextmanager
    def clip(self,path):
        """Clip with a path deformed in the same space as the artwork."""
        with self.saved():
            self.raw.clipPath(self._warped_path(path),doAntiAlias=True)
            yield self

    def gradient_rect(self,x,y,w,h,colors,start=None,end=None,positions=None):
        """Warp the rectangle boundary; the gradient stays in local coordinates."""
        start=(x,y) if start is None else start
        end=(x,y+h) if end is None else end
        paint=skia.Paint(AntiAlias=True)
        paint.setShader(skia.GradientShader.MakeLinear([start,end],[color(c) for c in colors],positions))
        path=skia.Path(); path.addRect(skia.Rect.MakeXYWH(x,y,w,h))
        self.raw.drawPath(self._warped_path(path),paint)

    def image(self,path,x,y,w=None,h=None,opacity=1):
        raise NotImplementedError('WarpCanvas cannot deform imported images or SVG documents; draw vector outlines with path()')

    def text(self,text,x,y,size=24,fill='#302d3c',font=None):
        raise NotImplementedError('WarpCanvas cannot deform text layout; draw glyph vector outlines with path()')
