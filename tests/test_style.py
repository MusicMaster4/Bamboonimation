import pytest
import skia
from bamboonimation.style import PAPER, CEL
from bamboonimation.drawing import Canvas


def test_art_direction_copies_palette_and_restores_canvas_after_error():
    palette={'warm':'#ff0000'}
    customized=PAPER.derive(palette=palette)
    palette['warm']='#00ff00'
    assert customized['warm']=='#ff0000' and PAPER['warm']=='#cc7053'
    with pytest.raises(TypeError): customized.palette['warm']='#000'
    c=Canvas(skia.Surface(40,40).getCanvas(),40,40)
    c.roughness=.8;c.stroke_scale=.7;c.boil_fps=6
    with pytest.raises(RuntimeError):
        with CEL.apply(c,zoom=2,boil_fps=12):
            assert c.roughness==0 and c.stroke_scale==.5 and c.boil_fps==12
            raise RuntimeError('artist interrupted')
    assert (c.roughness,c.stroke_scale,c.boil_fps)==(.8,.7,6)
