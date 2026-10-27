import math
import pytest
import skia
from bamboonimation.drawing import Canvas
from bamboonimation.effects import (camera_shake,speed_lines,impact_flash,motion_echo,hatch,FollowThrough)


def image(draw):
    surface=skia.Surface(80,60)
    surface.getCanvas().clear(skia.ColorTRANSPARENT)
    c=Canvas(surface.getCanvas(),80,60)
    draw(c)
    return surface.makeImageSnapshot().toarray()


def test_camera_shake_is_bounded_deterministic_and_timed():
    assert camera_shake(.9,at=1)==(0,0,0)
    assert camera_shake(1.3,at=1)==(0,0,0)
    values=[camera_shake(1+i/1000,at=1,amplitude=7,rotation=.4) for i in range(300)]
    assert all(abs(x)<=7 and abs(y)<=7 and abs(r)<=.4 for x,y,r in values)
    a=camera_shake(1.1,at=1,seed=9)
    camera_shake(8,at=1)
    assert camera_shake(1.1,at=1,seed=9)==a
    assert a!=camera_shake(1.1,at=1,seed=8)


def test_impact_frame_window_and_silhouette_recolor():
    events=[]
    def paint(c,t):
        c.ellipse(40,30,10,10,'#ff0000')
        events.append(t)
    def draw(c):
        assert not impact_flash(c,.999,at=1,painter=paint)
        assert impact_flash(c,1,at=1,frames=2,painter=paint,background='#ffffff',ink='#000000')
    pixels=image(draw)
    assert pixels[30,40].tolist()==[0,0,0,255]
    assert pixels[0,0].tolist()==[255,255,255,255]
    assert events==[1]
    image(lambda c: assert_inactive(c,paint))


def assert_inactive(c,paint):
    assert not impact_flash(c,1+2/24,at=1,frames=2,painter=paint)


def test_impact_preserves_alpha_outside_silhouette():
    pixels=image(lambda c:impact_flash(c,0,at=0,background=None,ink='#ffffff',
                               painter=lambda c,t:c.rect(20,20,20,20,'#ff0000')))
    assert pixels[25,25].tolist()==[255,255,255,255]
    assert pixels[0,0,3]==0


def test_impact_isolated_from_unbalanced_painter_save():
    def draw(c):
        initial=c.raw.getSaveCount()
        def leaky(c,t):
            c.save();c.translate(20,20)
            c.roughness=7
            c.rect(0,0,10,10,'#ffffff')
        impact_flash(c,0,at=0,painter=leaky)
        assert c.raw.getSaveCount()==initial
        assert c.raw.getTotalMatrix().isIdentity()
        assert c.roughness==0
    image(draw)


def test_speed_lines_determinism_and_exposure():
    def draw(c,t):
        speed_lines(c,t,center=(40,30),radius=(5,30),length=(3,15),
                    count=20,seed=7,exposure=12)
    a=image(lambda c:draw(c,.5))
    b=image(lambda c:draw(c,.54))
    assert (a==b).all()
    assert not (a==image(lambda c:draw(c,.7))).all()
    assert a[:,:,3].max()>0


def test_hatching_stays_inside_arbitrary_clip():
    pixels=image(lambda c:hatch(c,'M20 10 L60 10 L40 50Z',spacing=3,width=1,seed=7))
    assert pixels[:,:,3].sum()>0
    assert pixels[:8,:,3].sum()==0
    assert pixels[:,:18,3].sum()==0
    assert pixels[:,62:,3].sum()==0
    assert (pixels==image(lambda c:hatch(c,'M20 10 L60 10 L40 50Z',spacing=3,width=1,seed=7))).all()


def test_motion_echo_samples_poses_in_order_without_negative_time():
    calls=[]
    def draw(c):
        motion_echo(c,lambda c,t:(calls.append(t),c.ellipse(t*30,20,3,3,'#ffffff')),
                    .5,samples=3,spacing=.1)
    pixels=image(draw)
    assert calls==pytest.approx([.2,.3,.4])
    assert pixels[:,:,3].sum()>0
    calls.clear()
    image(lambda c:motion_echo(c,lambda c,t:calls.append(t),.05,samples=3,spacing=.1))
    assert calls==[]


def test_followthrough_constant_and_delayed_channels():
    constant=FollowThrough(lambda t:(4,8))
    assert constant(2)==(4,8)
    lag=FollowThrough(lambda t:t,delay=.1,overlap=.2)
    assert lag(1)==pytest.approx(.92)
    assert lag(0)==0
    assert lag(1)==pytest.approx(.92)
    with pytest.raises(TypeError):FollowThrough(lambda t:'no')(1)


def test_effect_validation_rejects_unbounded_work():
    with pytest.raises(ValueError):camera_shake(0,duration=0)
    with pytest.raises(ValueError):image(lambda c:speed_lines(c,0,count=10001))
    with pytest.raises(ValueError):image(lambda c:speed_lines(c,0,opacity=2))
    with pytest.raises(ValueError):image(lambda c:impact_flash(c,0,at=0,frames=0))
    with pytest.raises(ValueError):image(lambda c:motion_echo(c,lambda c,t:None,0,samples=65))
    with pytest.raises(ValueError):image(lambda c:hatch(c,'M0 0L80 0L80 60Z',spacing=.00001))
    with pytest.raises(ValueError):FollowThrough(lambda t:t,delay=0)
