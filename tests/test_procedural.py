from dataclasses import dataclass
import math
import pytest
import skia
from bamboonimation import Scene
from bamboonimation.drawing import Canvas
from bamboonimation.procedural import ParticleSystem, PathMotion, spring, overlap
from bamboonimation.storyboard import Storyboard


def test_particles_random_access_and_bounded_lifetime():
    emitter=ParticleSystem(seed=7,rate=20,lifetime=(1,2),end=5)
    a=emitter.sample(3)
    emitter.sample(1)
    assert emitter.sample(3)==a
    assert len(a)<=40
    assert not emitter.sample(-1)
    assert not emitter.sample(8)
    assert ParticleSystem(seed=8,rate=20,lifetime=(1,2)).sample(3)!=a


def test_particles_analytic_acceleration():
    emitter=ParticleSystem(rate=1,origin=(2,3),velocity=((4,4),(5,5)),
                           acceleration=(2,-2),lifetime=(4,4),fade=False)
    p=emitter.sample(2)[0]
    assert (p.x,p.y)==pytest.approx((14,9))


def test_path_arc_length_nearly_constant_speed():
    path=PathMotion([(0,0),(0,200),(200,-200),(200,0)],samples_per_segment=500)
    points=[path.sample(i/40)[:2] for i in range(41)]
    lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
    assert max(lengths)/min(lengths)<1.03
    assert points[0]==(0,0)
    assert points[-1]==(200,0)
    assert path.sample(2)==path.sample(1)


def test_joined_path_boundary():
    path=PathMotion([(0,0),(1,0),(2,0),(3,0),(4,0),(5,0),(6,0)])
    assert path.sample(.5)==pytest.approx((3,0,0))
    assert path.length==pytest.approx(6)


def test_spring_all_damping_regimes_settle_and_rewind():
    for damping in (.4,1,1.7):
        assert spring(0,damping=damping,initial=2,target=8)==2
        assert spring(30,damping=damping,initial=2,target=8)==pytest.approx(8)
        a=spring(.2,damping=damping)
        spring(5,damping=damping)
        assert spring(.2,damping=damping)==a
    assert overlap(-1)==0
    assert abs(overlap(10))<1e-12


def pixels(board,t):
    surface=skia.Surface(10,10)
    c=Canvas(surface.getCanvas(),10,10)
    board.draw(c,t)
    return bytes(surface.makeImageSnapshot().tobytes())


def test_storyboard_boundaries_transitions_and_random_access():
    red=Scene(width=10,height=10,duration=2,background='#ff0000')
    blue=Scene(width=10,height=10,duration=2,background='#0000ff')
    board=Storyboard(width=10,height=10).add(red).add(blue,transition='dissolve',overlap=.5)
    assert board.duration==3.5
    assert pixels(board,0)!=pixels(board,2)
    a=pixels(board,1.75)
    pixels(board,3)
    assert pixels(board,1.75)==a
    assert a not in (pixels(board,0),pixels(board,3))


def test_storyboard_wipe_and_iris_reveal():
    for effect in ('wipe','iris'):
        board=Storyboard(width=10,height=10)
        board.add(Scene(width=10,height=10,duration=2,background='#000000'))
        board.add(Scene(width=10,height=10,duration=2,background='#ffffff'),transition=effect,overlap=1)
        assert pixels(board,1)!=pixels(board,1.5)!=pixels(board,2)


def test_validation():
    with pytest.raises(ValueError): ParticleSystem(rate=100000,lifetime=(10,10))
    with pytest.raises(ValueError): ParticleSystem(lifetime=(2,1))
    with pytest.raises(ValueError): PathMotion([(0,0),(1,1)])
    with pytest.raises(ValueError): spring(1,frequency=0)
    board=Storyboard().add(Scene(duration=2))
    with pytest.raises(ValueError): board.add(Scene(duration=2),transition='wipe',overlap=2)
    with pytest.raises(ValueError): board.add(Scene(duration=2),transition='cut',overlap=.5)

def test_static_layer_cache_tracks_resolution_but_not_translation():
    from bamboonimation.procedural import StaticLayer
    calls=[]
    def paint(c):
        calls.append(1)
        c.rect(0,0,10,10,'#d07466')
    layer=StaticLayer(paint,width=10,height=10,max_cache_bytes=4000)
    surface=skia.Surface(40,40)
    c=Canvas(surface.getCanvas(),10,10)
    layer(c)
    with c.transform(2,3): layer(c)
    assert len(calls)==1
    with c.transform(sx=1.1): layer(c)
    with c.transform(sx=1.2): layer(c)
    assert len(calls)==2  # same upward 1.25 scale bucket
    with c.transform(sx=2): layer(c)
    assert len(calls)==3
    assert layer.cache_info['bytes']<=4000
    layer.clear_cache()
    assert layer.cache_info['bytes']==0
    layer(c)
    assert len(calls)==4


def test_static_layer_oversize_renders_without_exceeding_cache_budget():
    from bamboonimation.procedural import StaticLayer
    layer=StaticLayer(lambda c:c.rect(0,0,10,10,'#ffffff'),width=10,height=10,max_cache_bytes=1)
    surface=skia.Surface(10,10)
    c=Canvas(surface.getCanvas(),10,10)
    layer(c)
    assert layer.cache_info['entries']==0
    assert surface.makeImageSnapshot().toarray()[5,5].tolist()==[255,255,255,255]

def test_storyboard_mixed_aspect_preserves_geometry_and_replaces_bars():
    board=Storyboard(width=20,height=10)
    board.add(Scene(width=20,height=10,duration=1,background='#ff0000'))
    board.add(Scene(width=10,height=10,duration=1,background='#ffffff'))
    surface=skia.Surface(20,10)
    canvas=Canvas(surface.getCanvas(),20,10)
    board.draw(canvas,.5)
    board.draw(canvas,1.5)
    result=surface.makeImageSnapshot().toarray()
    assert result[5,2].tolist()==[0,0,0,255]
    assert result[5,7].tolist()==[255,255,255,255]
    assert result[5,17].tolist()==[0,0,0,255]


def test_storyboard_restores_stack_after_custom_shot_leaks_save():
    class Custom:
        width=height=10
        duration=1
        seed=1
        def draw(self,c,t):
            c.save()
            c.translate(30,20)
    board=Storyboard(width=10,height=10).add(Custom())
    surface=skia.Surface(10,10)
    c=Canvas(surface.getCanvas(),10,10)
    initial=c.raw.getSaveCount()
    board.draw(c,.5)
    assert c.raw.getSaveCount()==initial
    assert c.raw.getTotalMatrix().isIdentity()
