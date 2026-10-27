"""Contracts for arbitrary vector control-net deformation and shared anchors."""
import math
import pytest
import skia
from bamboonimation import Track,svg_path
from bamboonimation.deformation import LatticeWarp,WarpCanvas,warp_path


def commands(path):
    iterator=skia.Path.RawIter(path); result=[]
    while True:
        verb,points=iterator.next()
        if verb==skia.Path.kDone_Verb: break
        weight=iterator.conicWeight() if verb==skia.Path.kConic_Verb else None
        result.append((verb,[tuple(p) for p in points],weight))
    return result


def test_identity_preserves_every_verb_contours_fill_rule_and_source():
    source=svg_path('M1 2 L3 4 Q5 8 9 2 C11 3 12 7 14 2 Z M20 20 A8 5 25 1 1 35 24 Z')
    source=skia.Path(source)
    source.setFillType(skia.PathFillType.kEvenOdd)
    source.setIsVolatile(True)
    baseline=skia.Path(source)
    result=warp_path(source,lambda x,y:(x,y))
    assert result==source==baseline
    assert result is not source
    assert result.isVolatile() and result.getFillType()==source.getFillType()
    result.offset(100,100)
    assert source==baseline


def test_affine_map_matches_native_cubic_and_quadratic_transform():
    source=svg_path('M1 2 Q5 8 9 2 C11 3 12 7 14 2 L18 9 Z')
    affine=lambda x,y:(2*x+.5*y+3,-x+3*y+7)
    result=warp_path(source,affine)
    expected=skia.Path(source)
    expected.transform(skia.Matrix.MakeAll(2,.5,3,-1,3,7,0,0,1))
    assert result==expected
    before=commands(source); after=commands(result)
    assert [c[0] for c in before]==[c[0] for c in after]
    assert after[1][1][1:]==[(17.,26.),(22.,4.)]
    assert after[2][1][1:]==[(26.5,5.),(30.5,16.),(32.,-1.)]


def test_circle_rational_conics_keep_weights_and_affine_geometry():
    source=skia.Path(); source.addCircle(12,20,8)
    warped=warp_path(source,lambda x,y:(x*2+5,y*.5-3))
    old,new=commands(source),commands(warped)
    assert [c[0] for c in old]==[c[0] for c in new]
    weights=[c[2] for c in new if c[2] is not None]
    assert len(weights)==4
    assert weights==[c[2] for c in old if c[2] is not None]
    assert weights==pytest.approx([math.sqrt(.5)]*4)
    expected=skia.Path(source);expected.transform(skia.Matrix.MakeAll(2,0,5,0,.5,-3,0,0,1))
    assert warped==expected


def test_bilinear_lattice_corner_center_and_cell_sampling():
    warp=LatticeWarp((0,0,100,100),[[(0,0),(10,0)],[(0,20),(20,40)]])
    assert warp.map(0,0)==(0,0)
    assert warp.map(100,0)==(110,0)
    assert warp.map(0,100)==(0,120)
    assert warp.map(100,100)==(120,140)
    assert warp.map((50,50))==(57.5,65)
    assert warp(25,75)==pytest.approx((29.375,93.75))
    # A larger grid samples its own internal control vertices exactly.
    grid=LatticeWarp(skia.Rect.MakeLTRB(0,0,100,100),
                     [[(0,0),(0,0),(0,0)],[(0,0),(15,-10),(0,0)],[(0,0),(0,0),(0,0)]])
    assert grid.rows==grid.columns==3
    assert grid(50,50)==(65,40)
    assert grid(25,25)==(28.75,22.5)


def test_clamping_extends_displacement_without_clipping_point_and_extrapolation():
    offsets=[[(0,0),(10,0)],[(0,0),(10,0)]]
    clamp=LatticeWarp((0,0,100,100),offsets)
    extra=LatticeWarp((0,0,100,100),offsets,clamp=False)
    assert clamp(150,50)==(160,50)
    assert clamp(-50,50)==(-50,50)
    assert extra(150,50)==(165,50)
    assert extra(-50,50)==(-55,50)


def test_deformed_endpoint_and_prop_anchor_share_one_mapping():
    source=svg_path('M0 0 Q25 60 100 100')
    warp=LatticeWarp((0,0,100,100),[[(0,0),(5,-20)],[(0,0),(25,10)]])
    result=warp_path(source,warp)
    deformed_contact=tuple(result.getPoints(result.countPoints())[-1])
    anchor=warp.map((100,100))
    assert deformed_contact==anchor==(125,110)
    assert tuple(source.getPoints(source.countPoints())[-1])==(100,100)


def test_reverse_seek_uses_unchanged_baseline_and_immutable_grid():
    offsets=[[(0,0),(15,-10)],[(0,0),(0,0)]]
    warp=LatticeWarp((0,0,100,100),offsets)
    offsets[0][1]=(999,999)
    assert warp.offsets[0][1]==(15,-10)
    source=svg_path('M0 0 C25 0 75 100 100 100 Z')
    baseline=skia.Path(source)
    amount=Track(0).add(0,0).add(1,1).add(2,-.3).add(3,0)
    def sample(t): return warp_path(source,warp.with_strength(amount(t)))
    first=sample(.5)
    sample(2);sample(3)
    assert sample(.5)==first
    assert sample(0)==source==baseline
    assert warp.strength==1
    assert sample(1)!=sample(0)


@pytest.mark.parametrize('bounds,offsets',[
    ((0,0,0,10),[[(0,0)]*2]*2),
    ((0,10,10,0),[[(0,0)]*2]*2),
    ((0,0,float('inf'),10),[[(0,0)]*2]*2),
    ((0,0,10),[[(0,0)]*2]*2),
    ((0,0,10,10),[]),
    ((0,0,10,10),[[(0,0)]]),
    ((0,0,10,10),[[(0,0),(1,1)],[(0,0)]]),
    ((0,0,10,10),[[(0,0),(1,float('nan'))],[(0,0),(0,0)]]),
])
def test_invalid_bounds_or_grids_rejected(bounds,offsets):
    with pytest.raises(ValueError):LatticeWarp(bounds,offsets)


def test_invalid_mapper_inputs_and_nonfinite_output_are_rejected():
    with pytest.raises(TypeError):warp_path('M0 0 L1 1',None)
    with pytest.raises(TypeError):warp_path([],lambda x,y:(x,y))
    for output in ((1,),None,(float('nan'),0),(0,float('inf')),('left',0)):
        with pytest.raises(ValueError):warp_path('M0 0 L1 1',lambda x,y:output)
    with pytest.raises(ValueError):LatticeWarp((0,0,1,1),[[(0,0)]*2]*2,strength=float('nan'))
    with pytest.raises(ValueError):LatticeWarp((0,0,1,1),[[(0,0)]*2]*2,clamp='yes')


@pytest.fixture
def drawn_paths(monkeypatch):
    """Observe actual output geometry in device space before Skia rasterization."""
    from bamboonimation import Canvas
    paths=[]
    original=Canvas.path
    def capture(canvas,data,*args,**kwargs):
        path=skia.Path(svg_path(data) if isinstance(data,str) else data)
        path.transform(canvas.raw.getTotalMatrix())
        paths.append(path)
        return original(canvas,data,*args,**kwargs)
    monkeypatch.setattr(Canvas,'path',capture)
    return paths


def test_warp_canvas_nested_translation_uses_shared_space_and_anchor(drawn_paths):
    from bamboonimation import Canvas
    surface=skia.Surface(200,200)
    c=Canvas(surface.getCanvas(),200,200)
    warp=LatticeWarp((0,0,100,100),[[(0,0),(20,-10)],[(0,0),(40,30)]])
    with c.transform(30,40):
        deformed=WarpCanvas(c,warp)
        # Endpoint (5,10) after a nested joint translation is anchor (65,50).
        with deformed.transform(60,40):
            deformed.path('M0 0 L5 10',None,'#000',1)
        # A second surface detail authored directly in the parent space meets it.
        deformed.path('M65 50 L66 51',None,'#000',1)
        contact=warp(65,50)
        expected=(contact[0]+30,contact[1]+40)
    a=drawn_paths[0].getPoints(drawn_paths[0].countPoints())[-1]
    b=drawn_paths[1].getPoints(drawn_paths[1].countPoints())[0]
    assert tuple(a)==pytest.approx(expected,abs=2e-5)
    assert tuple(b)==pytest.approx(expected,abs=2e-5)


def test_warp_canvas_rotation_scale_and_affine_mapper_match_native_geometry(drawn_paths):
    from bamboonimation import Canvas
    surface=skia.Surface(300,300)
    c=Canvas(surface.getCanvas(),300,300)
    affine=skia.Matrix.MakeAll(1.2,.3,7,-.2,.8,11,0,0,1)
    mapper=lambda x,y:tuple(affine.mapXY(x,y))
    source=svg_path('M0 0 Q3 12 20 7 C25 8 29 -2 32 9 Z')
    with c.transform(80,90,rotation=17,sx=1.3,sy=.8):
        base=c.raw.getTotalMatrix()
        warped=WarpCanvas(c,mapper)
        with warped.transform(18,23,rotation=-32,sx=.7,sy=1.4):
            current=c.raw.getTotalMatrix()
            warped.path(source,'#000',None)
        base_inverse=skia.Matrix(); assert base.invert(base_inverse)
        relative=skia.Matrix.Concat(base_inverse,current)
        expected=skia.Path(source)
        expected.transform(skia.Matrix.Concat(base,skia.Matrix.Concat(affine,relative)))
    actual=drawn_paths[0]
    assert [x[0] for x in commands(actual)]==[x[0] for x in commands(expected)]
    for a,b in zip(actual.getPoints(actual.countPoints()),expected.getPoints(expected.countPoints())):
        assert tuple(a)==pytest.approx(tuple(b),abs=1e-4)


def test_warp_canvas_affine_without_skew_matches_direct_old_artwork(drawn_paths):
    from bamboonimation import Canvas
    surface=skia.Surface(200,200)
    c=Canvas(surface.getCanvas(),200,200)
    def artwork(canvas):
        canvas.ellipse(3,4,8,6,'#000')
        with canvas.transform(15,20,sx=2,sy=.5):
            canvas.rect(0,0,8,12,'#000',radius=2)
            canvas.line([(0,0),(8,12)])
            canvas.polygon([(0,0),(3,4),(7,2)],'#000')
    with c.transform(10,15):
        artwork(WarpCanvas(c,lambda x,y:(x*1.5+4,y*.8-3)))
    with c.transform(10,15):
        with c.transform(4,-3,sx=1.5,sy=.8):
            artwork(c)
    assert len(drawn_paths)==8
    for actual,expected in zip(drawn_paths[:4],drawn_paths[4:]):
        for a,b in zip(actual.getPoints(actual.countPoints()),expected.getPoints(expected.countPoints())):
            assert tuple(a)==pytest.approx(tuple(b),abs=3e-5)


def test_warp_canvas_style_is_independent_and_sampling_deterministic():
    import numpy as np
    from bamboonimation import Canvas
    surface=skia.Surface(100,100)
    c=Canvas(surface.getCanvas(),100,100,time=.25,seed=73)
    c.roughness=.8; c.boil_fps=12; c.stroke_scale=.7
    original=(c.roughness,c.boil_fps,c.stroke_scale,c.time,c.seed)
    warp=LatticeWarp((0,0,100,100),[[(0,0),(15,-10)],[(0,0),(0,0)]])
    def sample(t):
        surface.getCanvas().clear(skia.ColorWHITE)
        c.time=t
        proxy=WarpCanvas(c,warp)
        assert (proxy.width,proxy.height,proxy.time,proxy.seed)==(100,100,t,73)
        with proxy.saved():
            proxy.roughness=1.5; proxy.boil_fps=8; proxy.stroke_scale=.9
            proxy.rect(10,20,65,55,'#f80','#123',3,radius=7)
        assert (proxy.roughness,proxy.boil_fps,proxy.stroke_scale)==original[:3]
        proxy.roughness=9; proxy.boil_fps=99; proxy.stroke_scale=2
        assert (c.roughness,c.boil_fps,c.stroke_scale)==original[:3]
        return np.array(surface.makeImageSnapshot())
    first=sample(.25)
    sample(2)
    assert np.array_equal(first,sample(.25))
    assert c.raw.getSaveCount()==1


def test_warp_canvas_rejects_singular_transforms_and_unsupported_content():
    from bamboonimation import Canvas
    surface=skia.Surface(40,40)
    c=Canvas(surface.getCanvas(),40,40)
    identity=lambda x,y:(x,y)
    with c.transform(sx=0):
        with pytest.raises(ValueError,match='parent transform.*invertible'):
            WarpCanvas(c,identity)
    warped=WarpCanvas(c,identity)
    with warped.transform(sx=0):
        with pytest.raises(ValueError,match='nested transform.*zero scale'):
            warped.rect(0,0,10,10,'#000')
    with pytest.raises(NotImplementedError,match='vector outlines'):
        warped.text('hello',0,0)
    with pytest.raises(NotImplementedError,match='vector outlines'):
        warped.image('not-opened.svg',0,0)
    with pytest.raises(TypeError):WarpCanvas(c,None)
    with pytest.raises(TypeError):WarpCanvas(None,identity)
    with pytest.raises(ValueError,match='finite'):
        WarpCanvas(c,lambda x,y:(math.nan,y)).rect(0,0,10,10,'#000')


def test_warp_canvas_clip_and_gradient_boundaries_deform():
    import numpy as np
    from bamboonimation import Canvas
    surface=skia.Surface(60,40)
    surface.getCanvas().clear(skia.ColorWHITE)
    c=Canvas(surface.getCanvas(),60,40)
    proxy=WarpCanvas(c,lambda x,y:(x+20,y))
    with proxy.clip('M0 0 H10 V20 H0 Z'):
        proxy.gradient_rect(0,0,20,20,['#000','#000'])
    pixels=np.array(surface.makeImageSnapshot())
    assert all(pixels[10,25,:3]==0)
    assert all(pixels[10,5,:3]==255)
    assert all(pixels[10,35,:3]==255)
