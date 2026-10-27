"""Behavioral checks for timeline seeking, composition and arbitrary artwork."""
import math
import numpy as np
import pytest
import skia
from bamboonimation import (Scene,Canvas,Node,Group,Rect,Ellipse,Path,Sprite,Track,
    color,svg_path,morph_path,Rig,solve_two_bone,blend_poses,LipSync,MouthCue,Layer)


def render(scene,time,w=100,h=100):
    surf=skia.Surface(w,h)
    c=Canvas(surf.getCanvas(),scene.width,scene.height)
    scene.draw(c,time)
    return np.array(surf.makeImageSnapshot())


def test_timeline_random_access_and_exact_holds():
    x=Track(10).add(0,10).add(2,30,'linear').add(3,99,'hold')
    assert x(1)==20
    assert x(2.9)==30
    assert x(3)==99
    assert x(.5)==15
    assert x(10)==99
    assert x(-1)==10
    x.add(2,50,'linear')
    assert len(x.keys)==3
    assert x(1)==30


def test_color_and_vector_channels():
    assert Track((0,4)).add(1,(10,8),'linear')(.5)==(5,6)
    assert Track('#000000').add(1,'#ffffff','linear')(.5)=='#808080ff'
    assert color('#fff')==skia.ColorWHITE
    assert color('#ff000080')==skia.ColorSetARGB(128,255,0,0)
    assert color(None)==skia.ColorTRANSPARENT


def test_nested_graph_moves_artwork_and_seeks_without_mutation():
    child=Rect(10,10,fill='#ff0000',x=5,y=5)
    parent=Group(child,x=20,y=20).animate('x',60,0,2,'linear')
    scene=Scene(100,100,2,background='#ffffff').add(parent)
    start=render(scene,0); end=render(scene,2)
    assert not np.array_equal(start,end)
    assert np.array_equal(start,render(scene,0))
    assert parent.x==20 and child.x==5
    # Skia's platform array is BGRA; red channel occupies index 2 here.
    assert start[30,30,2]>200 and start[30,30,1]<20
    assert end[30,70,2]>200 and end[30,70,1]<20


def test_opacity_applies_to_group_as_one_composite():
    a=Rect(30,30,fill='#000000'); b=Rect(30,30,fill='#000000',x=15)
    s=Scene(100,100,1,background='#ffffff').add(Group(a,b,opacity=.5))
    img=render(s,0)
    assert abs(int(img[10,10,0])-int(img[10,20,0]))<=1
    assert 125<=int(img[10,20,0])<=130


def test_scene_camera_parallax_and_fixed_overlay():
    fixed=Layer(Rect(10,10,fill='#000000',x=20,y=20),depth=0)
    s=Scene(100,100,1,background='#ffffff').add(fixed)
    a=render(s,0)
    s.camera.at(0,x=80,y=30,zoom=2)
    assert np.array_equal(a,render(s,0))


def test_graph_rejects_cycles_and_duplicate_parents():
    a,b=Group(),Group(); a.add(b)
    with pytest.raises(ValueError): b.add(a)
    with pytest.raises(ValueError): Group().add(b)
    a.add(b)
    assert len(a.children)==1


def test_svg_all_commands_and_relative_smooth_curves():
    p=svg_path('M10 10 h20 v20 l10 -10 q10 -20 20 0 t20 0 c10 0 10 10 20 10 s20 -10 20 0 a10 10 0 0 1 10 10 z')
    assert not p.isEmpty()
    assert p.getBounds().width()>100
    with pytest.raises(ValueError): svg_path('M 1 2 invalid')
    with pytest.raises(ValueError): svg_path('M0 0 C1 2')
    with pytest.raises(ValueError): svg_path('M0 0 A1 1 0 3 1 2 3')


def test_bezier_morph_supports_arbitrary_shape_and_independent_seek():
    a='M0 0 C0 10 10 10 10 0 Z'; b='M0 0 C0 30 30 30 30 0 Z'
    p=Path(a,fill='#000000').morph(b,start=0,duration=2,ease='linear')
    halfway=p.value('data',1)
    assert svg_path(halfway).getBounds().width()==20
    assert svg_path(p.value('data',2)).getBounds().width()==30
    assert p.value('data',0)==a
    scene=Scene(100,100,2,background='#ffffff').add(p)
    first=render(scene,0)
    assert not np.array_equal(first,render(scene,2))
    assert np.array_equal(first,render(scene,0))
    assert p.data==a
    with pytest.raises(ValueError): morph_path(a,'M0 0 L2 2 Z',.5)


def test_two_bone_ik_targets_and_unreachable_clamping():
    for target in ((60,60),(80,-20),(1000,0),(0,0)):
        a,b=solve_two_bone(50,50,target)
        x=50*math.cos(math.radians(a))+50*math.cos(math.radians(a+b))
        y=50*math.sin(math.radians(a))+50*math.sin(math.radians(a+b))
        if math.hypot(*target)<=100:
            assert (x,y)==pytest.approx(target,abs=1e-6)
        else: assert math.hypot(x,y)==pytest.approx(100,abs=1e-6)
    rig=Rig(); arm=rig.bone('upper',50); lower=rig.bone('lower',50,parent='upper')
    rig.ik('upper','lower',(60,60),time=1)
    assert arm.value('rotation',1)==pytest.approx(13.05194,abs=1e-4)
    assert lower.x==50
    assert blend_poses({'head':350},{'head':10},.5)['head']['rotation']==360


def test_sprite_replacement_drawings_and_lip_sync_boundaries():
    calls=[]
    def drawing(i): return lambda c,t:calls.append(i)
    s=Scene(100,100,1).add(Sprite([drawing(0),drawing(1),drawing(2)],fps=2))
    for t in (0,.7,1.2,1.5): render(s,t)
    assert calls==[0,1,2,0]
    lip=LipSync([MouthCue(0,.5,'A'),MouthCue(.5,1,'B')])
    assert [lip(t) for t in (0,.499,.5,1)]==['A','A','B','X']
    with pytest.raises(ValueError): LipSync([MouthCue(0,1,'A'),MouthCue(.9,2,'B')])


def test_paper_and_rough_lines_reproducible():
    def paint(c,t):
        c.roughness=.8; c.boil_fps=12
        c.path('M10 10 Q50 90 90 10','#f4c887','#222222',3)
        c.paper(.2)
    scene=Scene(100,100,1,painter=paint,seed=12)
    a=render(scene,.2)
    render(scene,.8)
    assert np.array_equal(a,render(scene,.2))
    assert not np.array_equal(a,render(scene,.8))


def test_invalid_scene_and_keyframe_inputs():
    with pytest.raises(ValueError): Scene(duration=0)
    with pytest.raises(ValueError): Track().add(float('nan'),1)
    with pytest.raises(ValueError): Track().tween(2,0,0)
    with pytest.raises(ValueError): Rect().animate('typo',1)


def test_world_local_coordinates_support_nested_rotations_and_pivots():
    child=Node(x=30,y=10,rotation=-25,sx=1.2,sy=.8,pivot=(4,6))
    parent=Group(child,x=15,y=30,rotation=72,sx=2,sy=3)
    child.animate('rotation',75,start=0,duration=2)
    for time in (0,.7,2):
        for point in ((0,0),(10,25),(-30,-40)):
            assert child.local_point(child.world_point(point,time),time)==pytest.approx(point)
    parent.sx=0
    with pytest.raises(ValueError): child.local_point((1,1))


def test_replacement_frame_channel_is_discrete():
    sprite=Sprite([lambda c,t:None]*4)
    sprite.at(0,frame=0).at(1,frame=3)
    assert sprite.value('frame',.8)==0
    assert sprite.value('frame',1)==3


def test_svg_and_png_height_only_sizing_alpha_and_transforms(tmp_path):
    svg=tmp_path/'art.svg'
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="20" height="10"><rect width="20" height="10" fill="red" fill-opacity="0.5"/></svg>')
    raster=skia.Surface(20,10)
    raster.getCanvas().clear(skia.ColorSetARGB(128,255,0,0))
    png=tmp_path/'art.png'; png.write_bytes(bytes(raster.makeImageSnapshot().encodeToData()))
    def compose(path):
        def paint(c,t):
            with c.transform(70,10,rotation=90): c.image(path,0,0,h=20,opacity=.5)
        return Scene(100,100,1,background=None,painter=paint)
    a=render(compose(svg),0); b=render(compose(png),0)
    for img in (a,b):
        assert 63<=img[20,60,3]<=65
        assert img[45,60,3]>0
        assert img[55,60,3]==0
        assert img[20,40,3]==0
    # The raster source may differ at the scaled edge, but covered interiors agree.
    assert np.max(np.abs(a[15:45,55:65].astype(int)-b[15:45,55:65].astype(int)))<=1


def test_svg_vector_cache_dimensionless_viewports_and_file_changes(tmp_path):
    from bamboonimation.drawing import _svg_picture
    svg=tmp_path/'responsive.svg'
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><rect width="20" height="10" fill="red"/></svg>')
    def paint(c,t):
        c.image(svg,0,0,w=40,h=20)
        c.image(svg,50,50,w=20,h=10)
    scene=Scene(100,100,1,background=None,painter=paint)
    _svg_picture.cache_clear()
    a=render(scene,0); info=_svg_picture.cache_info()
    assert a[10,20,3]==255 and a[55,60,3]==255
    assert a[30,20,3]==0 and a[65,60,3]==0
    assert np.array_equal(a,render(scene,0))
    assert _svg_picture.cache_info().misses==info.misses
    assert _svg_picture.cache_info().hits>info.hits
    assert _svg_picture.cache_info().maxsize==32
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 10"><rect width="20" height="10" fill="blue"/></svg>')
    import os
    old=svg.stat().st_mtime_ns
    os.utime(svg,ns=(old+1_000_000,old+1_000_000))
    assert not np.array_equal(a,render(scene,0))


def test_canvas_scopes_restore_after_unbalanced_user_save_and_failure():
    surf=skia.Surface(100,100); raw=surf.getCanvas(); c=Canvas(raw,100,100)
    initial=raw.getSaveCount()
    def failing(c,t):
        c.save(); c.translate(20,30); c.roughness=9
        raise RuntimeError('artist error')
    for scene in (Scene(painter=failing),Scene(post_painter=failing),
                  Scene().add(Node(painter=failing))):
        with pytest.raises(RuntimeError): scene.draw(c,0)
        assert raw.getSaveCount()==initial
        assert raw.getTotalMatrix().isIdentity()
        assert c.roughness==0
    with pytest.raises(ValueError):
        with c.clip('bad SVG'): pass
    assert raw.getSaveCount()==initial
    with pytest.raises(RuntimeError):
        with c.opacity(.5):
            c.save(); c.translate(2,4)
            raise RuntimeError('layer failure')
    assert raw.getSaveCount()==initial
    assert raw.getTotalMatrix().isIdentity()


def test_visibility_keys_hold_even_with_overshooting_easing():
    node=Rect(10,10).at(0,visible=False).animate('visible',True,0,1,'back')
    assert node.value('visible',.8) is False
    assert node.value('visible',1) is True
    for bad in (None,'false',float('nan'),.5):
        with pytest.raises(ValueError): node.at(0,visible=bad)
    for bad in ('half',float('nan'),float('inf')):
        with pytest.raises(ValueError): Node(opacity=bad)
        with pytest.raises(ValueError): node.at(0,opacity=bad)
    with pytest.raises(ValueError): node.animate('children',[])
    # A user bypassing .at via channel must still get a helpful render error.
    node.channel('opacity').add(0,float('nan'))
    surface=skia.Surface(10,10)
    with pytest.raises(ValueError): node.draw(Canvas(surface.getCanvas(),10,10),1)


def test_scene_duration_and_dimensions_reject_invalid_numbers():
    for bad in (0,-1,float('nan'),float('inf'),'12',True,None):
        with pytest.raises(ValueError): Scene(duration=bad)
        with pytest.raises(ValueError): Scene(width=bad)


def test_generic_text_starting_hash_is_not_mistaken_for_a_hex_color():
    text=Track('#title').add(1,'#chapter')
    assert text(.5)=='#title'
    assert text(1)=='#chapter'


def test_src_over_paper_matches_opaque_multiply_and_caches_black_alpha():
    from bamboonimation.drawing import _paper
    size,seed=32,17
    gray=np.clip(np.random.default_rng(seed).normal(218,27,(size,size)),90,255).astype(np.uint8)
    rgba=np.empty((size,size,4),np.uint8); rgba[:,:,:3]=gray[:,:,None]; rgba[:,:,3]=255
    old_tile=skia.Image.fromarray(rgba,colorType=skia.ColorType.kRGBA_8888_ColorType)
    for amount in (.085,.12,.75,1):
        old=skia.Surface(100,100); new=skia.Surface(100,100)
        for surf in (old,new): surf.getCanvas().clear(color('#c8a976'))
        p=skia.Paint(Alphaf=amount,BlendMode=skia.BlendMode.kMultiply)
        p.setShader(old_tile.makeShader(skia.TileMode.kRepeat,skia.TileMode.kRepeat,skia.SamplingOptions()))
        old.getCanvas().drawRect(skia.Rect.MakeWH(100,100),p)
        Canvas(new.getCanvas(),100,100).paper(amount,seed=seed,size=size)
        a=np.array(old.makeImageSnapshot()).astype(int)
        b=np.array(new.makeImageSnapshot()).astype(int)
        assert np.max(np.abs(a-b))<=1
        grain=np.array(_paper(seed,size,amount))
        assert np.all(grain[:,:,:3]==0)
        assert grain[:,:,3].max()<255
    assert _paper.cache_info().maxsize==16


def test_explicit_stroke_scale_keeps_camera_closeup_outline_weight():
    def normal(c,t): c.line([(30,30),(30,70)],'#000000',4)
    def closeup(c,t):
        c.stroke_scale=.5
        c.line([(40,40),(40,60)],'#000000',4)
    a=Scene(100,100,1,background=None,painter=normal)
    b=Scene(100,100,1,background=None,painter=closeup)
    b.camera.at(0,zoom=2)
    assert np.array_equal(render(a,0),render(b,0))
    # Filled geometry uses its authored dimensions rather than outline styling.
    surface=skia.Surface(100,100); c=Canvas(surface.getCanvas(),100,100)
    assert c.stroke_scale==1
    c.stroke_scale=.5
    assert c._paint('#000000',True,6).getStrokeWidth()==3
    with c.saved():
        c.stroke_scale=2
        c.roughness=3
    assert c.stroke_scale==.5 and c.roughness==0
    with pytest.raises(RuntimeError):
        with c.transform(x=5):
            c.stroke_scale=3
            raise RuntimeError('scope error')
    assert c.stroke_scale==.5
    for bad in (0,-1,float('nan'),float('inf'),'half',True):
        with pytest.raises(ValueError): c.stroke_scale=bad


def test_animated_pivot_matches_drawing_anchor_and_inverse_at_each_time():
    marker=Rect(8,8,fill='#ff0000',x=30,y=40,pivot=(0,0))
    marker.at(0,pivot=(0,0)).animate('pivot',(10,20),0,2,'linear')
    moving=Scene(100,100,2,background='#ffffff').add(marker)
    first=render(moving,0)
    for time,expected_pivot in ((0,(0,0)),(1,(5,10)),(2,(10,20))):
        expected=Scene(100,100,2,background='#ffffff').add(
            Rect(8,8,fill='#ff0000',x=30,y=40,pivot=expected_pivot))
        assert np.array_equal(render(moving,time),render(expected,time))
        assert marker.world_point((0,0),time)==(30-expected_pivot[0],40-expected_pivot[1])
        assert marker.local_point(marker.world_point((4,7),time),time)==pytest.approx((4,7))
    assert np.array_equal(first,render(moving,0))
    assert marker.pivot==(0,0)
    moving.root.remove(marker)
    parent=Group(marker,x=20,y=30,rotation=30,sx=1.2,sy=.8)
    parent.at(0,pivot=(0,0)).animate('pivot',(8,12),0,2)
    for time in (0,.7,2):
        point=marker.world_point((4,7),time)
        assert marker.local_point(point,time)==pytest.approx((4,7))
    for bad in (None,(1,),('x',0),(float('nan'),0),(True,0)):
        with pytest.raises(ValueError): marker.at(0,pivot=bad)
        with pytest.raises(ValueError): Node(pivot=bad)
    marker.channel('pivot').add(0,(float('inf'),0))
    with pytest.raises(ValueError): marker.world_point(time=0)


def test_bone_tip_and_ik_use_sampled_pivot_and_reject_structural_channels():
    from bamboonimation import Bone
    bone=Bone(10,x=20,y=30,rotation=90)
    bone.at(0,pivot=(0,0)).at(1,pivot=(2,3))
    assert bone.tip(0)==pytest.approx((20,40))
    assert bone.tip(1)==pytest.approx((23,38))
    assert bone.tip(1)==pytest.approx(bone.world_point((10,0),1))
    with pytest.raises(ValueError): bone.at(0,length=20)
    rig=Rig(); upper=rig.bone('upper',40); lower=rig.bone('lower',40,parent='upper')
    upper.at(0,pivot=(0,0)).at(1,pivot=(1,0))
    rig.ik('upper','lower',(50,20),time=0)
    with pytest.raises(ValueError): rig.ik('upper','lower',(50,20),time=1)
    for node,prop,value in ((Node(),'name','other'),(rig,'bones',{}),(rig,'poses',{})):
        with pytest.raises(ValueError): node.at(0,**{prop:value})


def test_layer_depth_channel_changes_camera_parallax_at_sample_time():
    overlay=Layer(Rect(10,10,fill='#000000',x=30,y=30),depth=0)
    overlay.at(0,depth=0).at(1,depth=1)
    scene=Scene(100,100,1,background='#ffffff').add(overlay)
    scene.camera.at(0,x=70)
    first=render(scene,0); last=render(scene,1)
    assert not np.array_equal(first,last)
    expected=Scene(100,100,1,background='#ffffff').add(Rect(10,10,fill='#000000',x=10,y=30))
    assert np.array_equal(last,render(expected,1))
    assert np.array_equal(first,render(scene,0))


def test_text_font_and_sprite_image_dimensions_use_channels(tmp_path):
    from bamboonimation import Text
    surface=skia.Surface(100,100); canvas=Canvas(surface.getCanvas(),100,100)
    calls=[]
    canvas.text=lambda text,x,y,size,fill,font:calls.append(font)
    text=Text('sample',font='serif').at(0,font='serif').at(1,font='monospace')
    text.draw(canvas,0); text.draw(canvas,1); text.draw(canvas,0)
    assert calls==['serif','monospace','serif']
    raster=skia.Surface(2,1);raster.getCanvas().clear(color('#ff0000'))
    png=tmp_path/'sprite.png';png.write_bytes(bytes(raster.makeImageSnapshot().encodeToData()))
    sprite=Sprite([png],width=10,height=10,x=10,y=10).at(0,width=10,height=10).at(1,width=20,height=20)
    scene=Scene(100,100,1,background=None).add(sprite)
    small,big=render(scene,0),render(scene,1)
    assert small[25,25,3]==0 and big[25,25,3]==255
    assert sprite.width==10 and sprite.height==10


def test_sprite_rate_start_and_hold_channels_are_sampled_without_integration():
    drawn=[]
    sprite=Sprite([lambda c,t:drawn.append(0),lambda c,t:drawn.append(1),lambda c,t:drawn.append(2)],fps=2)
    sprite.at(0,fps=2,start=0,hold=False).at(1,fps=4,start=.5,hold=True)
    scene=Scene(100,100,2).add(sprite)
    for time in (0,.5,1,2,.5): render(scene,time)
    assert drawn==[0,0,2,2,0]
    assert sprite.value('fps',.5)==3 and sprite.value('start',.5)==.25
    with pytest.raises(ValueError): sprite.at(0,frames=[])
    with pytest.raises(ValueError): sprite.at(0,frame=.5)
    with pytest.raises(ValueError): sprite.at(0,fps=0)
    with pytest.raises(ValueError): sprite.at(0,hold='yes')
