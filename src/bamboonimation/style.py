"""Small shared art directions, independent of a scene's subject matter."""
from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping
import math
from .drawing import color


@dataclass(frozen=True)
class ArtStyle:
    """Keep palette and ink treatment consistent across arbitrary authored art.

    The palette is vocabulary, not automatic recoloring. Use style['ink'] in your
    paths and paint your own shapes. The context restores settings on exceptions.
    `zoom` compensates outline weight across camera cuts; filled geometry remains
    unchanged. Export resolution still scales every scene unit normally.
    """
    palette: Mapping[str,str] = field(default_factory=lambda:{
        'ink':'#493f4a','paper':'#f2e4cb','light':'#fff1cf',
        'warm':'#cc7053','cool':'#738e88','shadow':'#706d78'})
    roughness: float = .35
    paper_amount: float = .1
    seed: int = 1

    def __post_init__(self):
        palette=dict(self.palette)
        if not palette or not all(isinstance(k,str) and k for k in palette):
            raise ValueError('Palette needs named colors')
        for v in palette.values(): color(v)
        if not math.isfinite(self.roughness) or self.roughness<0:
            raise ValueError('Roughness must be finite and nonnegative')
        if not math.isfinite(self.paper_amount) or not 0<=self.paper_amount<=1:
            raise ValueError('Paper amount must be between zero and one')
        object.__setattr__(self,'palette',MappingProxyType(palette))

    def __getitem__(self,key): return self.palette[key]

    def derive(self,*,palette=None,**settings):
        """Create an independent direction, optionally replacing named swatches."""
        return replace(self,palette={**self.palette,**(palette or {})},**settings)

    @contextmanager
    def apply(self,canvas,*,zoom=1,boil_fps=0):
        if not math.isfinite(zoom) or zoom<=0: raise ValueError('Zoom must be positive and finite')
        with canvas.saved():
            canvas.roughness=self.roughness
            canvas.stroke_scale=1/zoom
            canvas.boil_fps=boil_fps
            yield canvas

    def finish(self,canvas):
        """Grain after drawing, outside the camera transform for uniform paper."""
        canvas.paper(self.paper_amount,seed=self.seed)


PAPER=ArtStyle()
NIGHT=ArtStyle(palette={'ink':'#20283f','paper':'#394559','light':'#f3ddb4',
                       'warm':'#d69072','cool':'#6d9c9c','shadow':'#292e48'},seed=19)
CEL=ArtStyle(palette={'ink':'#1e2444','paper':'#e9f1e8','light':'#ffffff',
                     'warm':'#ee8361','cool':'#4f98a0','shadow':'#6477a9'},roughness=0,paper_amount=0)
