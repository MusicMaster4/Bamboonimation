"""Continuous head orientation and repeatable facial drawing controls."""
import numpy as np
import pytest
import skia

from bamboonimation import Canvas
from bamboonimation.cartoon import Actor, BodyPose, FacePose


def image(view, *, body=None, face=None):
    surface=skia.Surface(360,480)
    surface.getCanvas().clear(skia.ColorWHITE)
    canvas=Canvas(surface.getCanvas(),360,480)
    Actor().draw(canvas,170,450,.7,view=view,body=body,face=face,
                 look=(4,2),expression='worried',blink=False)
    assert canvas.raw.getSaveCount()==1
    return surface.makeImageSnapshot().toarray()


def test_named_views_are_shortcuts_for_one_numeric_head_model():
    for name,yaw in [('front',0),('three_quarter',.55),('profile',1)]:
        for body in (None,BodyPose()):
            assert np.array_equal(image(name,body=body),image(yaw,body=body))


def test_yaw_is_continuous_at_far_eye_occlusion_and_legacy_view_angles():
    # A change between named drawings used to replace nose/face proportions in
    # one step. Nearby angles must now change pixels by nearby amounts, including
    # where the nose joins the outline and where the far eye disappears.
    for yaw in (.25,.5,.55,.65,.75,.85,.88):
        a=image(yaw-1e-5).astype(float)
        b=image(yaw+1e-5).astype(float)
        assert np.abs(a-b).mean()<.08
    controls=FacePose(eye_open=(.2,.9),brow_offset=(-4,3),cheek=4,jaw=6)
    first=image(.63,face=controls)
    assert not np.array_equal(first,image(.63,face=FacePose()))
    image(.9)
    assert np.array_equal(first,image(.63,face=controls))


def test_numeric_head_turn_rejects_invalid_values_in_both_draw_paths():
    for value in (-.01,1.01,float('nan'),float('inf'),True,None,'back'):
        for body in (None,BodyPose()):
            with pytest.raises(ValueError,match='view'):
                image(value,body=body)


def test_named_views_keep_existing_head_override_points():
    calls=[]
    class CustomActor(Actor):
        def head(self,*args):calls.append('front')
        def profile(self,*args):calls.append('profile')
        def three_quarter(self,*args):calls.append('three_quarter')
    surface=skia.Surface(360,480)
    canvas=Canvas(surface.getCanvas(),360,480)
    for body in (None,BodyPose()):
        for view in ('front','profile','three_quarter'):
            CustomActor().draw(canvas,170,450,view=view,body=body)
    assert calls==['front','profile','three_quarter']*2
