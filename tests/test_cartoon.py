"""Contact placement through an actor's actual nested draw transforms."""
import math
import random

import numpy as np
import pytest
import skia

from bamboonimation import Canvas
from bamboonimation.cartoon import Actor, FacePose, Pose, BodyPose, BODY_POSES, blend_body


def test_palm_constraint_reaches_world_target_under_nested_actor_transforms():
    actor=Actor()
    rng=random.Random(827)
    for side in ('left','right'):
        for _ in range(40):
            p=Pose(left=(-73,-152),right=(91,-169),tilt=11,
                   lean=rng.uniform(-25,25),crouch=rng.uniform(-12,24))
            target=(rng.uniform(100,800),rng.uniform(150,600))
            x,y=rng.uniform(200,600),rng.uniform(300,650)
            time,walk=rng.uniform(0,15),rng.uniform(-4,4)
            scale,squash=rng.uniform(.5,2.5),rng.uniform(.7,1.3)
            facing=rng.choice((-1,1));rotation=rng.uniform(-75,75)
            placed=actor.pose_for_hand(side,target,x,y,time,scale=scale,pose=p,
                walk=walk,facing=facing,squash=squash,rotation=rotation)
            # hand_anchor excludes the outer rotation by contract. Compose the
            # real enclosing Canvas transform, as a caller drawing a prop does.
            px,py,_=actor.hand_anchor(side,x,y,time,scale=scale,pose=placed,
                walk=walk,facing=facing,squash=squash)
            angle=math.radians(rotation);co,si=math.cos(angle),math.sin(angle)
            actual=(x+(px-x)*co-(py-y)*si,y+(px-x)*si+(py-y)*co)
            assert actual==pytest.approx(target,abs=1e-9)
            assert getattr(placed,'right' if side=='left' else 'left')==getattr(p,'right' if side=='left' else 'left')
            assert (p.left,p.right)==((-73,-152),(91,-169))
            assert (placed.lean,placed.tilt,placed.crouch)==(p.lean,p.tilt,p.crouch)


def test_three_quarter_acting_rewinds_without_mutating_pose_or_canvas():
    actor=Actor()
    surface=skia.Surface(280,400)
    c=Canvas(surface.getCanvas(),280,400)
    pose=Pose(left=(-61,-146),right=(80,-164),tilt=-7,lean=5)
    face=FacePose(eye_open=(.4,.85),brow_offset=(-3,2),cheek=4,jaw=3)
    def sample(expression,controls,turn):
        c.raw.clear(skia.ColorWHITE)
        actor.draw(c,140,385,.7,view='three_quarter',face=controls,
                   pose=pose,look=(4,2),blink=False,expression=expression,
                   shoulder_turn=turn)
        assert c.raw.getSaveCount()==1
        return np.array(surface.makeImageSnapshot())
    first=sample('curious',face,-.6)
    other=sample('worried',FacePose(eye_open=(.9,.6),jaw=9),.7)
    assert not np.array_equal(first,other)
    assert np.array_equal(first,sample('curious',face,-.6))
    assert face==FacePose(eye_open=(.4,.85),brow_offset=(-3,2),cheek=4,jaw=3)
    with pytest.raises(ValueError,match='squash'):
        actor.pose_for_hand('right',(1,2),0,0,squash=0)


@pytest.mark.parametrize('side', ['left','right'])
def test_body_palm_constraint_matches_actual_drawn_hand_and_foreground_redraw(monkeypatch,side):
    import bamboonimation.cartoon as cartoon
    from dataclasses import replace
    actor=Actor();surface=skia.Surface(600,600)
    canvas=Canvas(surface.getCanvas(),600,600)
    recorded=[]
    original=cartoon.hand
    def record(c,x,y,angle=0):
        recorded.append(tuple(c.raw.getTotalMatrix().mapXY(x,y)))
        original(c,x,y,angle)
    monkeypatch.setattr(cartoon,'hand',record)
    rng=random.Random(391)
    for _ in range(20):
        body=blend_body('reach','catch',rng.random())
        body=replace(body,chest_angle=rng.uniform(-25,25),chest=(rng.uniform(-15,15),rng.uniform(-10,20)))
        pose=Pose(lean=rng.uniform(-15,15),crouch=rng.uniform(-6,14))
        target=(rng.uniform(100,450),rng.uniform(100,450))
        x,y=280,500;rotation=rng.uniform(-30,30)
        scale=rng.uniform(.7,1.3);squash=rng.uniform(.8,1.2);facing=rng.choice((-1,1))
        t,walk=.7,.4
        solved=actor.pose_for_hand(side,target,x,y,t,pose=pose,body=body,
            scale=scale,squash=squash,facing=facing,walk=walk,rotation=rotation)
        recorded.clear()
        with canvas.transform(x,y,rotation=rotation):
            actor.draw(canvas,0,0,t,pose=solved,body=body,scale=scale,
                squash=squash,facing=facing,walk=walk,blink=False)
        assert recorded[0 if side=='left' else 1]==pytest.approx(target,abs=1e-4)
        recorded.clear()
        with canvas.transform(x,y,rotation=rotation):
            actor.draw_arm(canvas,side,0,0,t,pose=solved,body=body,scale=scale,
                squash=squash,facing=facing,walk=walk)
        assert recorded[0]==pytest.approx(target,abs=1e-4)
        px,py,_=actor.hand_anchor(side,x,y,t,pose=solved,body=body,scale=scale,
            squash=squash,facing=facing,walk=walk)
        a=math.radians(rotation);co,si=math.cos(a),math.sin(a)
        assert (x+(px-x)*co-(py-y)*si,y+(px-x)*si+(py-y)*co)==pytest.approx(target,abs=1e-9)
    assert canvas.raw.getSaveCount()==1


def test_authored_body_keeps_toe_support_while_chest_and_pelvis_counterpose(monkeypatch):
    from dataclasses import replace
    actor=Actor();surface=skia.Surface(500,500);canvas=Canvas(surface.getCanvas(),500,500)
    toes=[];original=canvas.line
    def record(points,stroke='#302d3c',width=3):
        points=list(points)
        if stroke=='#c78f69':
            toes.append(tuple(canvas.raw.getTotalMatrix().mapXY(*points[-1])))
        original(points,stroke,width)
    monkeypatch.setattr(canvas,'line',record)
    left,right=(-39,-9),(43,-9)
    for u in (0,.25,.5,.75,1):
        body=replace(blend_body('brace','reach',u),left_foot=left,right_foot=right,
                     heel_lift=(u*12,(1-u)*10))
        toes.clear()
        actor.draw(canvas,200,420,.7,body=body,pose=Pose(lean=13,crouch=9),blink=False)
        for actual,expected in zip(toes,[(200+left[0]+22,420+left[1]+6),(200+right[0]+22,420+right[1]+6)]):
            assert actual==pytest.approx(expected,abs=1e-4)


def test_body_plane_blend_has_no_midpoint_pop_and_random_access_is_stable():
    actor=Actor();surface=skia.Surface(320,440);canvas=Canvas(surface.getCanvas(),320,440)
    pose=Pose(left=(-70,-175),right=(120,-174),tilt=4)
    def sample(u):
        canvas.raw.clear(skia.ColorWHITE)
        actor.draw(canvas,135,425,.6,body=blend_body('brace','airborne',u),pose=pose,
                   view='three_quarter',blink=False)
        return np.array(surface.makeImageSnapshot())
    a,b=sample(.4999),sample(.5001)
    # Nearby geometric states remain nearby even across the nominal midpoint.
    assert np.abs(a[:,:,:3].astype(float)-b[:,:,:3]).mean()<.2
    extremes=np.abs(sample(0)[:,:,:3].astype(float)-sample(1)[:,:,:3]).mean()
    assert extremes>1
    assert np.array_equal(a,sample(.4999))
    assert canvas.raw.getSaveCount()==1


@pytest.mark.parametrize('side',['left','right'])
def test_foreground_sleeve_preserves_coat_pixels_and_keeps_hand_visible(monkeypatch,side):
    import bamboonimation.cartoon as cartoon
    actor=Actor();surface=skia.Surface(420,460);c=Canvas(surface.getCanvas(),420,460)
    body=BODY_POSES['reach'];pose=Pose(left=(-105,-145),right=(112,-145))
    c.raw.clear(skia.ColorWHITE)
    actor.draw(c,210,440,0,body=body,pose=pose,blink=False)
    before=np.array(surface.makeImageSnapshot())
    actor.draw_arm(c,side,210,440,0,body=body,pose=pose,occlude_root=True)
    after=np.array(surface.makeImageSnapshot())
    # Blue bib/pocket and gold button interiors must survive the foreground arm
    # pass; the former full root cap painted directly over these completed planes.
    colors=[np.array([0x75,0x6b,0x56]),np.array([0x8a,0x84,0x70]),np.array([0x6c,0xb5,0xe0])]
    mask=np.logical_or.reduce([np.all(before[:,:,:3]==rgb,axis=2) for rgb in colors])
    assert mask.sum()>500
    assert np.array_equal(before[mask],after[mask])
    recorded=[]
    original=cartoon.hand
    def record(cv,x,y,angle=0):
        recorded.append(tuple(cv.raw.getTotalMatrix().mapXY(x,y)))
        original(cv,x,y,angle)
    monkeypatch.setattr(cartoon,'hand',record)
    # Even a deliberate hand-over-chest target must not disappear in the sleeve
    # root mask. Its palm remains registered in both clipped and unclipped modes.
    target=(210,240)
    solved=actor.pose_for_hand(side,target,210,440,0,body=body,pose=pose)
    c.raw.clear(skia.ColorWHITE)
    actor.draw_arm(c,side,210,440,0,body=body,pose=solved,occlude_root=True)
    assert recorded[-1]==pytest.approx(target,abs=1e-4)
    pixels=np.array(surface.makeImageSnapshot())
    assert not np.all(pixels[240,210,:3]==255)
    assert c.raw.getSaveCount()==1
