"""Optional original cut-out actors and painted sets. The engine has no theme restriction.

Everything here uses the public Canvas API. Subclass Actor or replace its drawing
methods to create a different design; poses are plain data and timings are seconds.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from functools import lru_cache
import math
import skia
from .drawing import Canvas, color, svg_path
from .procedural import StaticLayer
from .deformation import LatticeWarp, warp_path

INK = '#493f4a'
CREAM = '#fff1cf'
SKIN = '#eeb28f'
HAIR = '#35495b'
RUST = '#cc7053'


def smooth(a, b, t):
    """Smooth unit ramp between two times, including exact endpoint holds."""
    u = max(0., min(1., (t-a)/(b-a)))
    return u*u*(3-2*u)


def cue(t, *keys):
    """Interpolate (seconds, value) pairs with held endpoints and smooth easing."""
    if t <= keys[0][0]: return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t <= b: return x+(y-x)*smooth(a,b,t)
    return keys[-1][1]


def limb(c, points, fill, width):
    # The tube is geometry; its ink border can keep a consistent screen weight.
    center=skia.Path(); center.moveTo(*points[0])
    for point in points[1:]: center.lineTo(*point)
    pen=skia.Paint(Style=skia.Paint.kStroke_Style,StrokeWidth=width,
                   StrokeCap=skia.Paint.kRound_Cap,StrokeJoin=skia.Paint.kRound_Join)
    outline=skia.Path(); pen.getFillPath(center,outline)
    c.path(skia.Simplify(outline),fill,INK,2)


def hand(c, x, y, angle=0):
    with c.transform(x=x,y=y,rotation=angle):
        c.path('M -10 5 C -17 -2 -15 -11 -9 -13 L -4 -18 Q 0 -21 2 -14 '
               'Q 8 -22 12 -14 L 17 -4 Q 21 7 12 14 Q 0 19 -10 5 Z',SKIN,INK,2)
        c.path('M 0 -9 Q 4 -5 3 0 M 7 -9 L 10 -2',None,'#bf7f72',1.3)


@dataclass(frozen=True)
class Pose:
    """Actor-local hand positions, head tilt and body lean; feet are the origin."""
    left: tuple = (-70,-130)
    right: tuple = (70,-130)
    tilt: float = 0
    lean: float = 0
    crouch: float = 0


@dataclass(frozen=True)
class FacePose:
    """Independent facial acting controls in head-local logical units.

    eye_open is (screen-left, screen-right), from closed 0 to fully open 1.
    brow_offset uses the same order; negative values raise a brow. cheek raises
    the near cheek and mouth corner; jaw lowers the chin independently. These
    controls apply across the continuous head turn from front to profile.
    """
    eye_open: tuple = (1.,1.)
    brow_offset: tuple = (0.,0.)
    cheek: float = 0.
    jaw: float = 0.

    def __post_init__(self):
        for name,low,high in (('eye_open',0,1),('brow_offset',-14,14)):
            value=getattr(self,name)
            try:
                if len(value)!=2: raise ValueError()
                value=tuple(float(v) for v in value)
                if any(not math.isfinite(v) or not low<=v<=high for v in value): raise ValueError()
            except (TypeError,ValueError):
                raise ValueError(f'{name} must be two finite numbers in [{low}, {high}]') from None
            object.__setattr__(self,name,value)
        for name,low,high in (('cheek',-8,8),('jaw',-12,20)):
            value=float(getattr(self,name))
            if not math.isfinite(value) or not low<=value<=high:
                raise ValueError(f'{name} must be finite and in [{low}, {high}]')
            object.__setattr__(self,name,value)


def _shoulder(side,turn):
    return (side*36*(1-.2*abs(turn))-turn*8,-182+side*turn*8)


POSES = {
    'idle': Pose(),
    'offer': Pose(left=(-61,-140),right=(106,-172),tilt=-5,lean=4),
    'surprise': Pose(left=(-95,-226),right=(100,-222),tilt=-10,lean=-8,crouch=8),
    'think': Pose(left=(-57,-132),right=(27,-223),tilt=8,lean=-3),
    'celebrate': Pose(left=(-98,-288),right=(99,-290),tilt=-8,lean=2),
    'sneak': Pose(left=(-70,-177),right=(95,-170),tilt=9,lean=16,crouch=20),
}


def blend_pose(a: Pose, b: Pose, amount: float) -> Pose:
    v = max(0.,min(1.,amount))
    def mix(x,y): return x+(y-x)*v
    return Pose(tuple(mix(x,y) for x,y in zip(a.left,b.left)),
                tuple(mix(x,y) for x,y in zip(a.right,b.right)),
                mix(a.tilt,b.tilt),mix(a.lean,b.lean),mix(a.crouch,b.crouch))


@dataclass(frozen=True)
class BodyPose:
    """Authored body planes and support points, all in actor-local units.

    Offsets are relative to the resting model. Chest rotation pivots at (0,-182),
    pelvis rotation at (0,-104); head offset/angle acts independently at the neck.
    Feet and knees are absolute local points before actor placement/squash.
    A positive heel_lift rolls a shoe onto its toe. ``planes`` mixes the authored
    reach/brace/airborne/catch contour decisions, so blend_body never switches
    drawing geometry halfway through an interpolation. mode is only a label.
    """
    mode: str = 'neutral'
    chest: tuple = (0.,0.)
    pelvis: tuple = (0.,0.)
    head: tuple = (0.,0.)
    chest_angle: float = 0.
    pelvis_angle: float = 0.
    head_angle: float = 0.
    left_foot: tuple = (-29.,-9.)
    right_foot: tuple = (29.,-9.)
    left_knee: tuple = (-24.,-43.)
    right_knee: tuple = (24.,-43.)
    heel_lift: tuple = (0.,0.)
    elbow_bias: tuple = (0.,0.)
    planes: tuple | None = None

    def __post_init__(self):
        modes=('neutral','reach','brace','airborne','catch')
        if self.mode not in modes: raise ValueError('Body mode must be neutral, reach, brace, airborne or catch')
        for name in ('chest','pelvis','head','left_foot','right_foot','left_knee','right_knee','heel_lift','elbow_bias'):
            try:
                value=tuple(float(v) for v in getattr(self,name))
                if len(value)!=2 or not all(math.isfinite(v) for v in value): raise ValueError()
            except (TypeError,ValueError): raise ValueError(f'{name} must contain two finite coordinates') from None
            object.__setattr__(self,name,value)
        for name in ('chest_angle','pelvis_angle','head_angle'):
            value=float(getattr(self,name))
            if not math.isfinite(value): raise ValueError(f'{name} must be finite')
            object.__setattr__(self,name,value)
        weights=tuple(float(self.mode==name) for name in modes[1:]) if self.planes is None else tuple(self.planes)
        if len(weights)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in weights):
            raise ValueError('planes must contain four finite contour weights')
        object.__setattr__(self,'planes',weights)


BODY_POSES = {
    'neutral': BodyPose(),
    'reach': BodyPose('reach',chest=(12,0),pelvis=(-6,0),head=(-2,0),
        chest_angle=6,pelvis_angle=-4,head_angle=-6,
        left_foot=(-31,-9),right_foot=(35,-9),left_knee=(-27,-44),right_knee=(24,-47),heel_lift=(7,0),elbow_bias=(-3,-5)),
    'brace': BodyPose('brace',chest=(-8,16),pelvis=(7,10),head=(4,-3),
        chest_angle=-9,pelvis_angle=5,head_angle=8,
        left_foot=(-47,-9),right_foot=(42,-9),left_knee=(-60,-43),right_knee=(58,-42),heel_lift=(0,5),elbow_bias=(-7,6)),
    'airborne': BodyPose('airborne',chest=(-8,-10),pelvis=(12,-10),head=(7,-3),
        chest_angle=-12,pelvis_angle=8,head_angle=10,
        left_foot=(-19,-45),right_foot=(25,-69),left_knee=(-53,-88),right_knee=(52,-99),heel_lift=(8,12),elbow_bias=(-9,8)),
    'catch': BodyPose('catch',chest=(14,8),pelvis=(-9,7),head=(-4,-4),
        chest_angle=12,pelvis_angle=-7,head_angle=-8,
        left_foot=(-43,-9),right_foot=(39,-9),left_knee=(-47,-43),right_knee=(51,-42),heel_lift=(0,8),elbow_bias=(-4,4)),
}


def _body_pose(body):
    if body is None or isinstance(body,BodyPose): return body
    if isinstance(body,str) and body in BODY_POSES:return BODY_POSES[body]
    raise ValueError('body must be a BodyPose or a BODY_POSES preset name')


def blend_body(a,b,amount):
    """Interpolate support points, articulation and contour weights continuously."""
    a,b=_body_pose(a),_body_pose(b)
    if a is None or b is None: raise ValueError('Blend two BodyPose objects, using neutral instead of None')
    if not math.isfinite(amount): raise ValueError('Body blend amount must be finite')
    u=max(0.,min(1.,amount))
    changes={}
    for name in ('chest','pelvis','head','left_foot','right_foot','left_knee','right_knee','heel_lift','elbow_bias','planes'):
        changes[name]=tuple(x+(y-x)*u for x,y in zip(getattr(a,name),getattr(b,name)))
    for name in ('chest_angle','pelvis_angle','head_angle'):
        changes[name]=getattr(a,name)+(getattr(b,name)-getattr(a,name))*u
    return replace(a,**changes)


def _rotate_point(point,angle,pivot=(0,0),offset=(0,0)):
    x,y=point[0]-pivot[0],point[1]-pivot[1]
    a=math.radians(angle);co,si=math.cos(a),math.sin(a)
    return (x*co-y*si+pivot[0]+offset[0],x*si+y*co+pivot[1]+offset[1])


def _chest_point(point,body):
    return _rotate_point(point,body.chest_angle,(0,-182),body.chest) if body is not None else point


def _ribbon(start,bend,end,start_width,bend_width,end_width):
    """Continuous tapered contour passing through the actual elbow/knee plane."""
    def direction(a,b):
        dx,dy=b[0]-a[0],b[1]-a[1];length=max(1e-9,math.hypot(dx,dy))
        return (dx/length,dy/length),length
    ds,ls=direction(start,bend);de,le=direction(bend,end);dm,_=direction(start,end)
    ns,ne,nm=(-ds[1],ds[0]),(-de[1],de[0]),(-dm[1],dm[0])
    def edge(point,n,w,side):return (point[0]+n[0]*w*.5*side,point[1]+n[1]*w*.5*side)
    def shift(point,d,amount):return point[0]+d[0]*amount,point[1]+d[1]*amount
    sl,bl,el=[edge(p,n,w,1) for p,n,w in ((start,ns,start_width),(bend,nm,bend_width),(end,ne,end_width))]
    sr,br,er=[edge(p,n,w,-1) for p,n,w in ((start,ns,start_width),(bend,nm,bend_width),(end,ne,end_width))]
    path=skia.Path();path.moveTo(*sl)
    path.cubicTo(*shift(sl,ds,ls*.4),*shift(bl,dm,-ls*.25),*bl)
    path.cubicTo(*shift(bl,dm,le*.25),*shift(el,de,-le*.4),*el)
    path.lineTo(*er)
    path.cubicTo(*shift(er,de,-le*.4),*shift(br,dm,le*.25),*br)
    path.cubicTo(*shift(br,dm,-ls*.25),*shift(sr,ds,ls*.4),*sr)
    path.close();return path


def _body_coat(body,shoulder_turn=0):
    """Exact shared coat boundary and landmarks in the posed torso space."""
    reach,brace,air,catch=body.planes
    def hip(point):return _rotate_point(point,body.pelvis_angle,(0,-104),body.pelvis)
    left_shoulder=_chest_point((-36-shoulder_turn*8,-199-shoulder_turn*7),body)
    right_shoulder=_chest_point((35-shoulder_turn*8,-198+shoulder_turn*7),body)
    neck=_chest_point((5,-212),body)
    left_hip=hip((-44-5*brace-3*air,-106))
    right_hip=hip((43+4*catch,-106))
    lmid=((left_shoulder[0]+left_hip[0])*.5-13-5*reach,
          (left_shoulder[1]+left_hip[1])*.5+6*brace)
    rmid=((right_shoulder[0]+right_hip[0])*.5+13+5*catch,
          (right_shoulder[1]+right_hip[1])*.5-6*air)
    coat=skia.Path();coat.moveTo(*left_shoulder)
    coat.quadTo(*lmid,*left_hip)
    bottom=hip((0,-94+6*brace-5*air))
    coat.quadTo(*bottom,*right_hip)
    coat.quadTo(*rmid,*right_shoulder)
    coat.quadTo(neck[0]+10,neck[1]-2,*neck)
    coat.quadTo(neck[0]-24,neck[1]+5,*left_shoulder);coat.close()
    return coat,(left_shoulder,right_shoulder,neck,left_hip,right_hip,lmid,rmid,bottom)



def _legacy_coat(shoulder_turn=0):
    """Shared visible coat boundary for the unarticulated actor and arm mask."""
    if shoulder_turn==0:
        return svg_path('M -36 -198 Q -51 -164 -47 -109 Q -31 -92 4 -98 '
                        'L 46 -103 Q 55 -144 35 -197 L 12 -212 Z')
    u=shoulder_turn;near=-38-7*u;far=34-10*u
    return svg_path(f'M {near} {-198-8*u} Q {-54-4*u} -163 {-45-3*u} -108 '
                    f'Q {-26-2*u} -92 {7-7*u} -99 L {43-9*u} -104 '
                    f'Q {53-11*u} -147 {far} {-197+8*u} L {8-8*u} -211 Z')


class Actor:
    """Mira, an original articulated actor with replaceable head/body drawing.

    ``draw`` is stateless: seeking directly to any time produces the same frame.
    Expression names: content, curious, surprise, delighted, worried, sleepy.
    ``body=None`` retains the original model. BodyPose/BODY_POSES add authored
    chest/pelvis counteraction, curved sleeves, folded legs and toe supports.
    Pass the same body to draw and all hand helpers. ``shadow=False`` allows
    a scene to draw a separate world-ground shadow during airborne motion.
    An actor is a convenience, not a required superclass for framework content.
    """
    def __init__(self, shirt=RUST, hair=HAIR, skin=SKIN):
        self.shirt,self.hair,self.skin=shirt,hair,skin

    def hand_anchor(self,side,x,y,t=0,scale=1,pose='idle',walk=0,facing=1,squash=1,body=None):
        """Return a palm's world (x,y,rotation) using the actor's exact transforms.

        This is useful for props drawn after the torso. If an enclosing Canvas
        transform exists, the returned coordinates are in that parent's space.
        ``body`` includes the posed chest transform; offsets/rotation of the head
        and pelvis do not move an authored palm target.
        """
        if side not in ('left','right'): raise ValueError('Hand must be left or right')
        p=POSES[pose] if isinstance(pose,str) else pose
        target=p.left if side=='left' else p.right
        body=_body_pose(body)
        target=_chest_point(target,body)
        bob=math.sin(t*2.4)*1.2+abs(math.sin(walk))*4
        theta=math.radians(-p.lean*.15);co,si=math.cos(theta),math.sin(theta)
        px=p.lean+target[0]*co-target[1]*si
        py=p.crouch+bob+target[0]*si+target[1]*co
        return (x+scale*facing*px/squash,y+scale*py*squash,
                -p.lean*.15+(body.chest_angle if body is not None else 0)+(-12 if side=='left' else 12))

    def pose_for_hand(self,side,target,x,y,t=0,scale=1,pose='idle',walk=0,
                      facing=1,squash=1,rotation=0,body=None):
        """Return a new Pose whose palm meets a target in the actor parent's space.

        This is the pure inverse of ``hand_anchor`` including the actor's bob,
        squash, facing and pose lean. ``rotation`` is an optional outer clockwise
        Canvas rotation about (x,y), as in ``with c.transform(x,y,rotation=...)``
        followed by ``draw(c,0,0,...)``. Target excludes camera/export transforms.
        Pass the same returned pose and transform arguments to draw/hand_anchor.
        ``body`` must match draw: its chest offset and angle are also inverted.
        Hand orientation and fingers remain artist-directed; this solves position.
        """
        if side not in ('left','right'): raise ValueError('Hand must be left or right')
        if not all(math.isfinite(v) for v in (scale,facing,squash,rotation)) or scale==0 or facing==0 or squash<=0:
            raise ValueError('Hand placement needs finite, nonzero scale/facing and positive squash')
        if len(target)!=2 or not all(math.isfinite(v) for v in (*target,x,y,t,walk)):
            raise ValueError('Hand target, placement and time must be finite')
        p=POSES[pose] if isinstance(pose,str) else pose
        angle=math.radians(-rotation); co,si=math.cos(angle),math.sin(angle)
        dx,dy=target[0]-x,target[1]-y
        px=(dx*co-dy*si)*squash/(scale*facing)-p.lean
        py=(dx*si+dy*co)/(scale*squash)-p.crouch-math.sin(t*2.4)*1.2-abs(math.sin(walk))*4
        angle=math.radians(p.lean*.15);co,si=math.cos(angle),math.sin(angle)
        local=(px*co-py*si,px*si+py*co)
        body=_body_pose(body)
        if body is not None:
            local=_rotate_point((local[0]-body.chest[0],local[1]-body.chest[1]),-body.chest_angle,(0,-182))
        return replace(p,**{side:local})

    def draw(self,c,x,y,t=0,scale=1,pose='idle',expression='content',
             look=(0,0),blink=None,walk=0,facing=1,squash=1,view='front',front_hands=(),knee_bend=0,hand_shapes=None,
             face=None,shoulder_turn=0,body=None,shadow=True):
        p=POSES[pose] if isinstance(pose,str) else pose
        if not isinstance(shadow,bool): raise ValueError('shadow must be boolean')
        if face is not None and not isinstance(face,FacePose): raise TypeError('face must be a FacePose')
        if not math.isfinite(shoulder_turn) or not -1<=shoulder_turn<=1: raise ValueError('shoulder_turn must be in [-1, 1]')
        hand_shapes=hand_shapes or {}
        if any(side not in ('left','right') or shape not in ('fist','open','none') for side,shape in hand_shapes.items()):
            raise ValueError('hand_shapes maps left/right to fist/open/none')
        def draw_hand(side,target):
            name='left' if side<0 else 'right'
            if hand_shapes.get(name)=='open': open_hand(c,*target,rotation=side*12)
            elif hand_shapes.get(name)!='none': hand(c,*target,angle=side*12)
        blink = (abs((t+0.3)%3.7-1.2)<.065) if blink is None else blink
        bob=math.sin(t*2.4)*1.2 + abs(math.sin(walk))*4
        body=_body_pose(body)
        if body is not None:
            return self._draw_posed(c,x,y,t,scale,p,expression,look,blink,walk,
                facing,squash,view,front_hands,hand_shapes,face,shoulder_turn,body,shadow)
        with c.transform(x=x,y=y, sx=scale*facing/squash, sy=scale*squash):
            # Soft ground contact, then boots and trousers behind coat.
            if shadow:c.ellipse(0,1,58,8,'#493f4a20')
            for side in (-1,1):
                swing=math.sin(walk)*side*24
                limb(c,[(side*19,-92),(side*24+swing*.6+knee_bend*(1 if side<0 else -.65),-43-abs(knee_bend)*.28),(side*29+swing,-9)],'#65787a',24)
                with c.transform(x=side*29+swing,y=-8,rotation=side*3):
                    c.path('M -17 -6 Q -5 -20 7 -10 L 26 -1 Q 31 9 18 10 L -19 8 Z','#51434a',INK,2)
                    c.line([(-18,6),(22,6)],'#c78f69',2)
            with c.transform(x=p.lean,y=p.crouch+bob,rotation=-p.lean*.15):
                # Sleeve arms with bent elbows; actual hand targets are authorable.
                for side,target in ((-1,p.left),(1,p.right)):
                    shoulder=_shoulder(side,shoulder_turn)
                    elbow=((shoulder[0]+target[0])*.52+side*17,
                           (shoulder[1]+target[1])*.5+19)
                    limb(c,[shoulder,elbow,target],self.shirt,24)
                    draw_hand(side,target)
                if shoulder_turn==0:
                    c.path(_legacy_coat(shoulder_turn),self.shirt,INK,1.8)
                    c.path('M -35 -184 Q -26 -143 -33 -107 L -15 -101 L -7 -196 Z','#e18b60',None)
                    c.path('M 8 -199 L 5 -104 M -19 -145 Q -6 -140 0 -144',None,'#96574d',1.5)
                    c.path('M -30 -111 L -20 -178 L 28 -179 L 34 -111 Z','#566b75',INK,2)
                    c.path('M -24 -174 L -29 -201 M 23 -175 L 23 -203',None,'#526470',8)
                    c.ellipse(-23,-178,3,3,'#e0b56c'); c.ellipse(25,-178,3,3,'#e0b56c')
                    c.path('M -14 -147 Q 0 -141 17 -147 L 15 -126 Q 0 -119 -12 -127 Z','#70848a',INK,1.5)
                else:
                    # A turned coat has a near side plane, uneven shoulders and
                    # displaced bib/seams, rather than a rotated frontal panel.
                    u=shoulder_turn; near=-38-7*u; far=34-10*u
                    c.path(_legacy_coat(shoulder_turn),self.shirt,INK,1.8)
                    c.path(f'M {near+1} -185 Q {-39-8*u} -137 {-38-4*u} -109 L {-18-8*u} -102 L {-14-9*u} -196 Z','#e18b60',None)
                    c.path(f'M {13-16*u} -198 L {8-12*u} -104',None,'#96574d',1.5)
                    c.path(f'M {-30-5*u} -111 L {-22-7*u} {-179-4*u} L {26-9*u} {-177+4*u} L {30-7*u} -112 Z','#566b75',INK,2)
                    c.path(f'M {-24-7*u} -174 L {-28-7*u} {-201-5*u} M {21-9*u} -175 L {24-9*u} {-202+5*u}',None,'#526470',8)
                    c.ellipse(-23-7*u,-178-4*u,3,3,'#e0b56c');c.ellipse(23-9*u,-177+4*u,3,3,'#e0b56c')
                    c.path(f'M {-15-7*u} -147 Q {-7*u} -141 {14-7*u} -147 L {12-7*u} -127 Q {-7*u} -121 {-13-7*u} -128 Z','#70848a',INK,1.5)
                c.path('M -12 -243 L -13 -193 Q 2 -185 16 -198 L 18 -243 Z',self.skin,INK,2)
                with c.transform(x=0,y=-237,rotation=p.tilt):
                    if view=='front' and face is None:self.head(c,t,expression,look,blink)
                    elif view=='profile' and face is None:self.profile(c,t,expression,look,blink)
                    elif view=='three_quarter':self.three_quarter(c,t,expression,look,blink,face)
                    else:self.draw_head(c,t,expression,look,blink,view,face)
                # Gesture arms can pass in front of the coat and face.
                for side_name in front_hands:
                    side=-1 if side_name=='left' else 1
                    target=p.left if side_name=='left' else p.right
                    shoulder=_shoulder(side,shoulder_turn)
                    elbow=((shoulder[0]+target[0])*.52+side*17,(shoulder[1]+target[1])*.5+19)
                    limb(c,[shoulder,elbow,target],self.shirt,24)
                    draw_hand(side,target)

    def draw_arm(self,c,side,x,y,t=0,scale=1,pose='idle',walk=0,facing=1,squash=1,shape='fist',shoulder_turn=0,body=None,occlude_root=False):
        """Redraw one registered arm above an intervening prop or foreground.

        Match the actor's transform arguments, then draw the foreground object
        and call this method, including the same body and shoulder_turn. Draw
        the held object and its near fingers last. With occlude_root=True,
        the proximal sleeve stays behind the coat boundary, while its distal
        portion can cover a prop. The hand itself is never masked. Keep False
        for a gesture intentionally crossing in front of the torso.
        """
        if not isinstance(occlude_root,bool): raise ValueError('occlude_root must be boolean')
        if side not in ('left','right') or shape not in ('fist','open','none'):
            raise ValueError('Use left/right arm and fist/open/none hand shape')
        p=POSES[pose] if isinstance(pose,str) else pose
        sign=-1 if side=='left' else 1
        body=_body_pose(body)
        if body is not None:
            bob=math.sin(t*2.4)*1.2+abs(math.sin(walk))*4
            with c.transform(x=x,y=y,sx=scale*facing/squash,sy=scale*squash):
                with c.transform(x=p.lean,y=p.crouch+bob,rotation=-p.lean*.15):
                    target=p.left if sign<0 else p.right
                    with c.saved():
                        if occlude_root:
                            coat,_=_body_coat(body,shoulder_turn)
                            root=_chest_point(_shoulder(sign,shoulder_turn),body)
                            neighborhood=skia.Path();neighborhood.addCircle(*root,45)
                            mask=skia.Op(coat,neighborhood,skia.PathOp.kIntersect_PathOp)
                            c.raw.clipPath(mask,skia.ClipOp.kDifference,doAntiAlias=True)
                        with c.transform(x=body.chest[0],y=body.chest[1]-182,rotation=body.chest_angle):
                            c.translate(0,182)
                            self._posed_arm(c,sign,target,body,shape,shoulder_turn,draw_hand=False)
                    # Hands are independent of the proximal sleeve mask, even
                    # when a folded hand target lies directly over the coat.
                    with c.transform(x=body.chest[0],y=body.chest[1]-182,rotation=body.chest_angle):
                        c.translate(0,182)
                        if shape=='open':open_hand(c,*target,rotation=sign*12)
                        elif shape!='none':hand(c,*target,angle=sign*12)
            return
        target=p.left if sign<0 else p.right
        bob=math.sin(t*2.4)*1.2+abs(math.sin(walk))*4
        with c.transform(x=x,y=y,sx=scale*facing/squash,sy=scale*squash):
            with c.transform(x=p.lean,y=p.crouch+bob,rotation=-p.lean*.15):
                shoulder=_shoulder(sign,shoulder_turn)
                elbow=((shoulder[0]+target[0])*.52+sign*17,(shoulder[1]+target[1])*.5+19)
                with c.saved():
                    if occlude_root:
                        neighborhood=skia.Path();neighborhood.addCircle(*shoulder,45)
                        mask=skia.Op(_legacy_coat(shoulder_turn),neighborhood,skia.PathOp.kIntersect_PathOp)
                        c.raw.clipPath(mask,skia.ClipOp.kDifference,doAntiAlias=True)
                    limb(c,[shoulder,elbow,target],self.shirt,24)
                if shape=='open': open_hand(c,*target,rotation=sign*12)
                elif shape!='none': hand(c,*target,angle=sign*12)

    def _posed_arm(self,c,side,target,body,shape,shoulder_turn=0,draw_hand=True):
        """A curved, tapered sleeve with a cuff plane; one continuous outline."""
        shoulder=_shoulder(side,shoulder_turn)
        bias=body.elbow_bias[0 if side<0 else 1]
        elbow=((shoulder[0]+target[0])*.5+side*22+bias,
               (shoulder[1]+target[1])*.5+18+abs(bias)*.35)
        # Bury the capped sleeve origin inside the coat. Its visible contour
        # emerges at the shoulder boundary instead of exposing a diagonal slab.
        buried=(shoulder[0]-side*19,shoulder[1])
        sleeve=_ribbon(buried,elbow,target,27,22,18)
        c.path(sleeve,self.shirt,INK,1.8)
        # The underside broadens at a bent elbow; it is a clothing side plane,
        # not another outlined limb segment or a seam at a joint.
        with c.clip(sleeve):
            c.path(f'M {shoulder[0]-side*8} {shoulder[1]+4} '
                   f'Q {elbow[0]-side*5} {elbow[1]+8} {target[0]-side*5} {target[1]+5} '
                   f'L {target[0]+side*11} {target[1]+15} '
                   f'Q {elbow[0]+side*11} {elbow[1]+18} {shoulder[0]+side*14} {shoulder[1]+10} Z','#ac614f',None)
        dx,dy=target[0]-elbow[0],target[1]-elbow[1]
        angle=math.degrees(math.atan2(dy,dx))+90
        with c.transform(*target,rotation=angle):
            c.ellipse(0,0,9,3.2,'#a85d4d',INK,1.1)
            c.path('M -7 -2 Q 0 -4 7 -2',None,'#e18b60',1)
        # A short elbow fold follows the inside bend and stays inside the tube.
        vx,vy=target[0]-shoulder[0],target[1]-shoulder[1]
        length=max(1,math.hypot(vx,vy));nx,ny=-vy/length,vx/length
        center=((shoulder[0]+2*elbow[0]+target[0])/4,(shoulder[1]+2*elbow[1]+target[1])/4)
        c.path(f'M {center[0]-nx*5} {center[1]-ny*5} Q {center[0]+vx*.025} {center[1]+vy*.025} {center[0]+nx*4} {center[1]+ny*4}',None,'#96574d',1.1)
        if draw_hand:
            if shape=='open':open_hand(c,*target,rotation=side*12)
            elif shape!='none':hand(c,*target,angle=side*12)

    def _draw_posed(self,c,x,y,t,scale,p,expression,look,blink,walk,facing,squash,
                    view,front_hands,hand_shapes,face,shoulder_turn,body,shadow):
        bob=math.sin(t*2.4)*1.2+abs(math.sin(walk))*4
        base_angle=-p.lean*.15
        reach,brace,air,catch=body.planes
        def base(point):return _rotate_point(point,base_angle,offset=(p.lean,p.crouch+bob))
        def hip(point):return _rotate_point(point,body.pelvis_angle,(0,-104),body.pelvis)
        with c.transform(x=x,y=y,sx=scale*facing/squash,sy=scale*squash):
            if shadow:c.ellipse(0,1,58,8,'#493f4a20')
            # Feet stay in their authored support space while chest/hips move.
            # Each trouser leg is one curved taper, without knee join outlines.
            for index,side in enumerate((-1,1)):
                foot=body.left_foot if side<0 else body.right_foot
                knee=body.left_knee if side<0 else body.right_knee
                heel=body.heel_lift[index]
                foot_angle=side*3+math.degrees(math.atan2(heel,45))
                ankle=_rotate_point((0,-5),foot_angle,(22,6),foot)
                top=base(hip((side*18,-104)))
                leg=_ribbon(top,knee,ankle,29,23,18)
                c.path(leg,'#65787a',INK,1.8)
                with c.clip(leg):
                    c.path(f'M {top[0]+side*5} {top[1]} Q {knee[0]+side*5} {knee[1]} {ankle[0]+side*3} {ankle[1]} '
                           f'L {ankle[0]+side*14} {ankle[1]+4} Q {knee[0]+side*18} {knee[1]+2} {top[0]+side*19} {top[1]} Z','#52696e',None)
                # Curved shin crease adds a plane but no dark knee ring.
                c.path(f'M {knee[0]+side*4} {knee[1]-4} Q {knee[0]+side*9} {knee[1]+3} {knee[0]+side*5} {knee[1]+8}',None,'#52666b',1)
                with c.transform(foot[0]+22,foot[1]+6,rotation=foot_angle):
                    c.translate(-22,-6)
                    c.path('M -17 -6 Q -5 -20 7 -10 L 26 -1 Q 31 9 18 10 L -19 8 Z','#51434a',INK,1.8)
                    c.line([(-18,6),(22,6)],'#c78f69',2)
            with c.transform(x=p.lean,y=p.crouch+bob,rotation=base_angle):
                # Sleeves share the exact chest mapping used by palm helpers.
                with c.transform(body.chest[0],body.chest[1]-182,rotation=body.chest_angle):
                    c.translate(0,182)
                    for side,target in ((-1,p.left),(1,p.right)):
                        self._posed_arm(c,side,target,body,hand_shapes.get('left' if side<0 else 'right','fist'),shoulder_turn)
                coat,landmarks=_body_coat(body,shoulder_turn)
                left_shoulder,right_shoulder,neck,left_hip,right_hip,lmid,rmid,bottom=landmarks
                c.path(coat,self.shirt,INK,1.8)
                with c.clip(coat):
                    # Broad near side, compressed far side and sweeping wrinkles
                    # are drawn from separate chest/pelvis landmarks.
                    inner_top=_chest_point((-17-12*reach+5*brace,-198),body)
                    inner_bottom=hip((-18-7*catch,-100))
                    c.path(f'M {left_shoulder[0]} {left_shoulder[1]} Q {lmid[0]} {lmid[1]} {left_hip[0]} {left_hip[1]} '
                           f'L {inner_bottom[0]} {inner_bottom[1]} Q {inner_top[0]-6*brace} -147 {inner_top[0]} {inner_top[1]} Z','#e18b60',None)
                    far_top=_chest_point((26,-192),body);far_bottom=hip((30,-105))
                    c.path(f'M {far_top[0]} {far_top[1]} Q {rmid[0]+5} {rmid[1]} {right_hip[0]} {right_hip[1]} '
                           f'L {far_bottom[0]} {far_bottom[1]} Q {far_top[0]-1} -148 {far_top[0]} {far_top[1]} Z','#ac614f',None)
                # Bib is an independently registered curved panel, its upper and
                # lower edges attached to chest and pelvis, not one rigid quad.
                tl=_chest_point((-22-4*reach,-179-3*brace),body)
                tr=_chest_point((25-3*catch,-179+3*brace),body)
                bl=hip((-28,-110));br=hip((31,-111))
                bib=skia.Path();bib.moveTo(*bl);bib.quadTo(tl[0]-3,tl[1]+29,*tl)
                bib.quadTo((tl[0]+tr[0])/2,tl[1]+5+6*brace,*tr)
                bib.quadTo(tr[0]+5,tr[1]+35,*br)
                bib.quadTo((bl[0]+br[0])/2,bottom[1]-7,*bl);bib.close()
                c.path(bib,'#566b75',INK,1.6)
                for side,button in ((-1,tl),(1,tr)):
                    strap=_chest_point((side*27,-202+side*shoulder_turn*5),body)
                    c.line([button,strap],'#526470',7)
                    c.ellipse(*button,3,3,'#e0b56c')
                pocket_top=(tl[0]*.55+bl[0]*.45+6,tl[1]*.5+bl[1]*.5)
                pocket_right=(tr[0]*.5+br[0]*.5-6,tr[1]*.5+br[1]*.5)
                c.path(f'M {pocket_top[0]} {pocket_top[1]} Q {(pocket_top[0]+pocket_right[0])/2} {pocket_top[1]+6} {pocket_right[0]} {pocket_right[1]} '
                       f'L {pocket_right[0]-1} {pocket_right[1]+17} Q {(pocket_top[0]+pocket_right[0])/2} {pocket_top[1]+25} {pocket_top[0]+1} {pocket_top[1]+17} Z','#70848a',INK,1.3)
                # Diagonal compression folds follow the hip/chest counterpose.
                for side,amount in ((-1,brace+catch*.5),(1,reach+air*.7)):
                    crease=hip((side*35,-119))
                    end=_chest_point((side*(29-amount*6),-146),body)
                    c.path(f'M {crease[0]} {crease[1]} Q {crease[0]-side*(9+amount*3)} {crease[1]-5} {end[0]} {end[1]}',None,'#96574d',1.2)
                with c.transform(body.chest[0],body.chest[1]-182,rotation=body.chest_angle):
                    c.translate(0,182)
                    # The neck overlaps inside the coat; head shift changes its
                    # curve and top edge, preserving attachment through extremes.
                    hx,hy=body.head
                    c.path(f'M {-12+hx*.6} {-243+hy} Q -13 -218 -13 -195 Q 2 -188 16 -198 '
                           f'Q {17+hx*.35} -221 {18+hx*.6} {-243+hy} Z',self.skin,INK,1.8)
                    with c.transform(hx,-237+hy,rotation=p.tilt+body.head_angle):
                        if view=='front' and face is None:self.head(c,t,expression,look,blink)
                        elif view=='profile' and face is None:self.profile(c,t,expression,look,blink)
                        elif view=='three_quarter':self.three_quarter(c,t,expression,look,blink,face)
                        else:self.draw_head(c,t,expression,look,blink,view,face)
                    for side_name in front_hands:
                        side=-1 if side_name=='left' else 1
                        target=p.left if side<0 else p.right
                        self._posed_arm(c,side,target,body,hand_shapes.get(side_name,'fist'),shoulder_turn)

    def draw_head(self,c,t,expression,look,blink,view='front',face=None):
        """Draw one continuous head model, with yaw 0 (front) through 1 (profile).

        String views remain shortcuts: front=0, three_quarter=.55, profile=1.
        Numeric yaw moves the actual contours and facial landmarks; it never
        overlays/crossfades two drawings. The same far-eye visibility also gates
        its eyebrow, and the nose is a single unioned form at every angle.
        """
        views={'front':0.,'three_quarter':.55,'profile':1.}
        if isinstance(view,str):
            if view not in views:raise ValueError('Actor view must be front, profile, three_quarter or numeric yaw in [0, 1]')
            yaw=views[view]
        else:
            if isinstance(view,bool) or not isinstance(view,(int,float)) or not math.isfinite(view) or not 0<=view<=1:
                raise ValueError('Actor numeric view yaw must be finite and in [0, 1]')
            yaw=float(view)
        face=face or FacePose()
        if not isinstance(face,FacePose):raise TypeError('face must be a FacePose')
        self._turned_head(c,t,expression,look,blink,yaw,face)

    def three_quarter(self,c,t,expression,look,blink,face=None):
        self.draw_head(c,t,expression,look,blink,.55,face)

    def profile(self,c,t,expression,look,blink):
        self.draw_head(c,t,expression,look,blink,1.)

    def head(self,c,t,expression,look,blink):
        self.draw_head(c,t,expression,look,blink,0.)

    def _turned_head(self,c,t,expression,look,blink,yaw,face):
        from .drawing import svg_path
        # All contours share front/profile correspondence. One set of drawing
        # commands carries the skull, forelock, cheek, mouth and nose through a
        # turn; changing view cannot replace the character's proportions.
        def mix(a,b):return a+(b-a)*yaw
        def pt(a,b):return f'{mix(a[0],b[0])} {mix(a[1],b[1])}'
        cheek=face.cheek
        jaw=face.jaw+(30 if expression=='shout' else 5 if expression=='surprise' else 0)
        c.path('M '+pt((-47,-21),(-48,-28))+' C '+pt((-71,-43),(-65,-45))+' '+pt((-66,-84),(-64,-83))+' '+pt((-37,-91),(-39,-91))+
               ' Q '+pt((-13,-115),(-13,-112))+' '+pt((13,-94),(11,-94))+
               ' Q '+pt((46,-108),(32,-101))+' '+pt((59,-78),(45,-78))+
               ' L '+pt((68,-61),(52,-66))+' L '+pt((49,-54),(34,-53))+' L '+pt((52,-10),(14,-15))+' Z',self.hair,INK,1.8)
        ex=mix(-50,-33);ey=mix(-27,-25)
        c.path(f'M {ex+8} {ey-9} Q {ex-13} {ey-20} {ex-13} {ey+1} Q {ex-10} {ey+18} {ex+9} {ey+12}',self.skin,INK,1.7)
        c.path(f'M {ex-5} {ey-4} Q {ex+3} {ey-8} {ex+2} {ey+4}',None,'#b77970',1.3)
        # A base face has no artificial nose notch. Unioning the projecting nose
        # removes the cheek outline behind it when the tip reaches the silhouette.
        outline=('M '+pt((-43,-64),(-31,-69))+' Q '+pt((-7,-86),(-1,-83))+' '+pt((32,-66),(25,-61))+
                 ' Q '+pt((44,-53),(29,-47))+' '+pt((43,-31),(29,-32))+
                 f' Q {mix(47,34)} {-9-4*yaw+jaw*.15} {mix(37,31)} {mix(5,6)+jaw*.3}'+
                 f' Q {mix(25,16)} {mix(21,24)+jaw*.55} {mix(-3,-8)} {mix(23,12)+jaw*.8}'+
                 f' Q {mix(-31,-20)-cheek*.15} {mix(16,10)+jaw*.5} {mix(-41,-25)} -9'+
                 ' Q '+pt((-47,-35),(-34,-39))+' '+pt((-43,-64),(-31,-69))+' Z')
        bridge=mix(0,28);tip=mix(7,47);under=mix(3,35);root=mix(-4,29)
        nose=f'M {bridge} -31 L {tip} -21 Q {tip+4} -15 {under} -12 Q {root} -8 {root} -14 Z'
        silhouette=skia.Op(svg_path(outline),svg_path(nose),skia.PathOp.kUnion_PathOp)
        c.path(silhouette,self.skin,INK,1.8)
        with c.clip(silhouette):
            c.path(f'M {mix(30,25)} -54 Q {mix(48,37)} -25 {mix(35,26)} 0 Q {mix(22,12)} {18+jaw*.6} {mix(2,-7)} {20+jaw*.7} '
                   f'Q {mix(31,18)} {24+jaw*.6} {mix(42,33)} {3+jaw*.25} L {mix(46,31)} -43 Z','#db947f',None)
            nearx=mix(-29,6)
            c.ellipse(nearx,-8-cheek,mix(12,9),mix(6,5),'#e29583')
            far_width=1-smooth(.55,.88,yaw)
            if far_width>.01:c.ellipse(mix(30,34),-10-cheek*.3,10*far_width,5*far_width,'#e29583')
            for xx,yy in [(-5,-4),(3,-2),(0,-7)]:c.ellipse(nearx+xx,-8+yy-cheek*.5,.9,1,INK)
            lx=max(-4,min(4,look[0]));ly=max(-5,min(5,look[1]))
            surprised=expression in ('surprise','shout')
            # Near/far eye use the SAME visibility and width as their brows.
            eyes=[(mix(-20,14),mix(-28,-32),mix(13,10),mix(18,17),1.),
                  (mix(17,33),mix(-31,-34),14*far_width,mix(20,15),far_width)]
            for i,(x,y,rx,ry,visible) in enumerate(eyes):
                if visible<=.025:continue
                opening=0 if blink or expression=='sleepy' else face.eye_open[i]
                mid=y+ry*.15
                if opening<.035:
                    c.path(f'M {x-rx} {mid} Q {x} {mid+4} {x+rx} {mid-1}',None,INK,1.8)
                else:
                    top=y-ry*opening*(1.1 if surprised else 1)
                    bottom=y+ry*(.25+.75*opening)
                    eye=f'M {x-rx} {mid} Q {x-2} {2*top-mid} {x+rx} {mid-1} Q {x+2} {2*bottom-mid} {x-rx} {mid} Z'
                    c.path(eye,CREAM,None)
                    with c.clip(eye):
                        px=x+lx*(1-.5*i)+mix(2,1)
                        c.ellipse(px,y+ly+3,(3.5 if surprised else 4.6)*min(1,visible*1.5),5 if surprised else 6.8,INK)
                        c.ellipse(px+1,y+ly,1.2*min(1,visible*1.5),1.7,CREAM)
                    c.path(eye,None,INK,1.6)
                by=y-ry-5+face.brow_offset[i]-(4 if surprised else 0)
                slope=(5 if i==0 else -4) if expression=='worried' else 0
                c.path(f'M {x-rx} {by+2+slope} Q {x} {by-5} {x+rx} {by+1-slope}',None,INK,2.6 if i==0 else 2.2)
        # A single right-facing bridge/tip/underside, not an inside nose pointing
        # in the opposite direction to a second nose in the outer contour.
        c.path(nose,self.skin,None)
        c.path(f'M {bridge} -31 L {tip} -21 Q {tip+4} -15 {under} -12 Q {root} -8 {root} -14',None,'#ad7168',1.5)
        mx=mix(4,22);my=5+jaw*.26
        with c.clip(silhouette), c.transform(mx,my,sx=mix(1,.58)):
            if expression=='shout':
                c.path('M -22 -5 C -17 -21 15 -20 24 -8 Q 32 10 19 26 Q -6 35 -21 16 Z',INK,INK,1.3)
                c.path('M -16 -8 Q 1 -15 20 -6 L 16 1 L 7 -1 L 0 4 L -7 0 L -14 3 Z',CREAM,None)
                c.path('M -5 22 Q 3 13 13 20 Q 6 29 -5 22 Z','#d98982',None)
            elif expression=='surprise':
                c.ellipse(2,4,7,12,INK);c.ellipse(3,11,4.5,3,'#cf817e')
            elif expression=='worried':
                c.path(f'M -12 3 Q 1 -6 15 {1-cheek*.25}',None,INK,1.8)
            elif expression=='delighted':
                c.path(f'M -16 -6 Q 0 1 17 {-10-cheek*.2} Q 15 15 0 15 Q -12 13 -16 -6 Z',INK,INK,1.3)
                c.path('M -12 -4 Q 1 1 13 -7 L 11 0 Q -1 6 -10 1 Z',CREAM,None)
                c.path('M -5 11 Q 3 5 10 11 Q 2 17 -5 11 Z','#d98982',None)
            else:
                c.path(f'M -13 0 Q 1 {12-cheek*.2} 16 {-3-cheek*.35}',None,INK,1.8)
                c.path(f'M 15 {-6-cheek*.35} L 19 {-1-cheek*.35}',None,INK,1.2)
        # Forelock is last so eyebrows/eyes cannot accidentally be inked over the
        # hair. Its control-point correspondence is shared at every yaw.
        c.path('M '+pt((-50,-57),(-48,-50))+' Q '+pt((-62,-78),(-62,-82))+' '+pt((-38,-84),(-34,-90))+
               ' L '+pt((-48,-99),(-41,-102))+' Q '+pt((-17,-106),(-9,-106))+' '+pt((0,-88),(7,-90))+
               ' Q '+pt((19,-108),(28,-99))+' '+pt((46,-87),(45,-78))+
               ' L '+pt((65,-81),(52,-68))+' L '+pt((44,-60),(27,-57))+
               ' Q '+pt((20,-52),(18,-61))+' '+pt((6,-68),(11,-69))+
               ' Q '+pt((-7,-42),(-3,-43))+' '+pt((-27,-41),(-22,-41))+
               ' L '+pt((-20,-69),(-19,-66))+' Q '+pt((-33,-51),(-36,-48))+' '+pt((-50,-47),(-48,-50))+' Z',self.hair,INK,1.8)
        c.path('M '+pt((-37,-85),(-36,-83))+' Q '+pt((-13,-95),(-15,-93))+' '+pt((1,-80),(3,-79))+
               ' M '+pt((20,-86),(22,-85))+' Q '+pt((37,-87),(35,-84))+' '+pt((47,-76),(44,-77)),None,'#58717c',1.8)


class Rabbit:
    """Pip, a squashable companion. Can serve as a custom actor authoring example."""
    def draw(self,c,x,y,t=0,scale=1,expression='content',look=(0,0),squash=1):
        with c.transform(x=x,y=y,sx=scale/squash,sy=scale*squash):
            c.ellipse(0,3,41,6,'#493f4a22')
            c.ellipse(33,-28,14,15,'#fff0cc',INK,2)
            c.path('M -29 -57 Q -37 -103 -16 -107 Q -2 -101 -9 -63 '
                   'Q 2 -99 19 -96 Q 34 -88 16 -51 Z','#f5dfb0',INK,2.4)
            c.path('M -23 -67 Q -31 -94 -18 -97 Q -10 -88 -16 -68 '
                   'M 5 -65 Q 13 -91 20 -86 Q 23 -77 13 -61',None,'#df9e8c',5)
            c.path('M -35 -48 Q -35 -74 -5 -72 Q 21 -76 29 -49 '
                   'Q 45 -24 29 -5 Q 10 8 -18 0 Q -45 -10 -35 -48 Z','#f5dfb0',INK,2.4)
            c.path('M 18 -57 Q 43 -31 27 -9 Q 18 1 6 0 L 17 -28 Z','#e5c795',None)
            c.ellipse(-21,-4,17,7,'#f7e6be',INK,1.5); c.ellipse(20,-3,15,7,'#f7e6be',INK,1.5)
            if expression in ('sleepy','sneeze','laugh'):
                c.path('M -24 -44 Q -17 -39 -10 -45 M 3 -44 Q 11 -39 17 -45',None,INK,2)
            else:
                for ex in (-17,11):
                    c.ellipse(ex,-44,7,10,CREAM,INK,1.5)
                    c.ellipse(ex+look[0],-43+look[1],2.7,4.5,INK)
            c.path('M -9 -31 L 0 -31 L -4 -26 Z','#b87b76',None)
            if expression=='sneeze':
                c.path('M -15 -23 Q -2 -32 9 -23 Q 12 -7 -4 -5 Q -17 -9 -15 -23 Z',INK,INK,1)
                c.path('M -10 -10 Q -2 -17 5 -10',None,'#df9e8c',3)
            elif expression=='inhale':
                c.ellipse(-4,-20,4,6,INK)
                c.path('M -26 -59 L -13 -63 M 6 -63 L 16 -59',None,INK,1.8)
            elif expression=='laugh':
                c.path('M -14 -24 Q -2 -18 10 -25 Q 7 -7 -3 -7 Q -13 -9 -14 -24 Z',INK,None)
                c.path('M -4 -11 L 1 -11',None,'#df9e8c',3)
            else:
                c.path('M -4 -26 L -4 -21 M -12 -22 Q -5 -17 -4 -21 Q 1 -17 5 -22',None,INK,1.5)
            c.path('M -30 -31 L -45 -35 M -29 -27 L -46 -26 M 19 -30 L 34 -35 M 20 -25 L 37 -23',None,INK,1)
            c.path('M -25 -15 Q -2 -3 24 -14 L 25 -6 Q -1 5 -26 -6 Z','#829d95',INK,1.3)
            c.path('M 16 -9 L 34 -3 L 24 7 L 13 -5 Z','#829d95',INK,1.3)


def cup(c,x,y,rotation=0,scale=1,handle_side=1):
    with c.transform(x=x,y=y,rotation=rotation,sx=scale,sy=scale):
        handle=skia.Path(); handle.moveTo(25,-38); handle.cubicTo(65,-48,58,-4,29,-12)
        pen=skia.Paint(Style=skia.Paint.kStroke_Style,StrokeWidth=7,StrokeCap=skia.Paint.kRound_Cap)
        shape=skia.Path();pen.getFillPath(handle,shape)
        with c.transform(sx=handle_side,sy=1):
            c.path(skia.Simplify(shape),'#7eaaa4',INK,2)
        c.path('M -30 -48 Q -31 -5 -18 -1 Q 4 8 25 -3 L 33 -48 Z','#8cb5ab',INK,2.5)
        c.path('M 17 -45 L 24 -43 L 18 -9 Q 10 -4 7 -7 Z','#6d9995',None)
        c.ellipse(1,-48,32,8,'#e2d7b4',INK,2)
        c.ellipse(1,-47,26,5,'#795848',None)
        c.path('M -20 -37 L -17 -17',None,'#c4d3ba',3)
        c.path('M -4 -24 L 2 -30 L 7 -22 L 1 -16 Z',CREAM,None)



def cup_handle_anchor(x,y,rotation=0,scale=1,handle_side=-1):
    """World wrist contact for the authored handle grip; not the cup body."""
    a=math.radians(rotation)
    lx,ly=handle_side*68*scale,-25*scale
    return x+lx*math.cos(a)-ly*math.sin(a),y+lx*math.sin(a)+ly*math.cos(a)


def cup_handle_grip(c,x,y,rotation=0,scale=1,handle_side=-1,closure=1,skin=SKIN):
    """One connected custom hand around the handle; hide the generic hand.

    Wrist placement matches ``cup_handle_anchor``. The palm, fingers and
    opposing thumb share one contour, so there are no floating finger caps.
    """
    u=max(0,min(1,closure))
    with c.transform(x=x,y=y,rotation=rotation,sx=-handle_side*scale,sy=scale):
        palm='M-73 -33 Q-65 -39 -59 -40 Q-50 -44 -44 -38 L-43 -19 Q-45 -10 -55 -10 Q-64 -11 -73 -17 Z'
        shapes=[svg_path(palm)]
        finger_lines=[]
        for (y0,length),(ox,oy) in zip([(-32,17),(-25,18),(-18,15),(-11,13)],[(-48,-64),(-35,-57),(-28,-43),(-26,-28)]):
            tipx=ox*(1-u)+(-55+length)*u
            tipy=oy*(1-u)+y0*u
            path=f'M-58 {y0-4} Q-49 {y0-6} {tipx-2} {tipy-4} Q{tipx+5} {tipy-3} {tipx+3} {tipy+2} Q-47 {y0+7} -59 {y0+3} Z'
            shapes.append(svg_path(path))
            finger_lines.append(f'M-56 {y0+3} Q-51 {y0+5} {-47+8*u} {y0+3}')
        thumb_tip=(-35-7*u,-27-9*u)
        thumb=f'M-64 -34 Q-63 -46 -55 -46 Q-50 -45 {thumb_tip[0]} {thumb_tip[1]-4} Q{thumb_tip[0]+5} {thumb_tip[1]+2} {thumb_tip[0]-1} {thumb_tip[1]+4} Q-52 -29 -58 -33 Z'
        shapes.append(svg_path(thumb))
        outline=shapes[0]
        for shape in shapes[1:]:outline=skia.Op(outline,shape,skia.PathOp.kUnion_PathOp)
        c.path(outline,skin,INK,1.4)
        for line in finger_lines:c.path(line,None,INK,1)
        c.path('M-61 -31 Q-55 -28 -52 -34',None,INK,1)
        c.path('M-67 -24 Q-63 -26 -60 -22',None,'#bf7f72',1)


def cookie(c,x,y,rotation=0,scale=1):
    with c.transform(x=x,y=y,rotation=rotation,sx=scale,sy=scale):
        c.path('M -21 -9 Q -25 -22 -11 -25 Q 1 -32 12 -23 Q 27 -22 26 -9 '
               'Q 34 3 23 15 Q 19 29 4 27 Q -12 31 -20 19 Q -33 9 -21 -9 Z','#d99f62',INK,2)
        c.path('M -20 11 Q -1 29 21 9 Q 21 27 3 27 Q -13 28 -20 16', '#bd8257',None)
        for xx,yy,rr in [(-10,-13,3),(11,-10,4),(-4,4,3),(13,12,3),(-16,11,2)]:
            c.path(f'M {xx-rr} {yy} L {xx} {yy-rr} L {xx+rr} {yy+1} L {xx+1} {yy+rr} Z','#715044',None)
        c.path('M -14 -20 L -7 -22 M -25 0 L -23 5',None,'#edc48a',2)


def plant(c,x,y,scale=1):
    with c.transform(x=x,y=y,sx=scale,sy=scale):
        c.path('M -28 -47 L -20 3 Q 0 11 22 2 L 31 -47 Z','#bb7d69',INK,2)
        c.ellipse(1,-47,30,7,'#c99378',INK,2)
        c.path('M 0 -45 Q -13 -94 4 -144 M 0 -68 Q -34 -95 -37 -111 '
               'M 0 -83 Q 30 -111 38 -124',None,'#6a7b65',4)
        for xx,yy,rr in [(-27,-104,-35),(22,-111,35),(-8,-130,-25),(9,-151,20),(-38,-113,-50)]:
            with c.transform(x=xx,y=yy,rotation=rr):
                c.path('M 0 15 Q -34 -3 0 -24 Q 29 -1 0 15 Z','#82947b',INK,1.5)
                c.line([(0,10),(0,-17)],'#a6b091',1.3)


def _room(c, mood='day'):
    # Painted architectural planes, not a flat presentation background.
    c.gradient_rect(0,0,1280,720,['#e4d4b5','#b5c2ac'],start=(0,0),end=(1100,700))
    c.path('M 0 0 L 193 0 L 244 467 L 0 560 Z','#b1bca9',None)
    c.path('M 0 561 L 244 467 L 1280 468 L 1280 720 L 0 720 Z','#c5a481',INK,2)
    c.path('M 0 575 L 245 484 L 1280 485',None,'#877d71',3)
    for xx in range(-400,1600,200):
        c.line([(xx,720),(244+(xx-244)*.42,485)],'#ad8c72',1.5)
    c.line([(0,644),(1280,603)],'#b89578',1.6)
    # Sunlit window and loose curtains.
    c.path('M 753 66 L 1084 58 L 1088 361 L 752 366 Z','#9a8a72',INK,2)
    c.rect(766,78,305,272,'#dce4c7',INK,2)
    c.gradient_rect(771,83,295,260,['#c0d5c5','#f4e9b5'])
    c.path('M 773 283 Q 834 225 894 282 Q 985 208 1065 251 L 1067 343 L 773 343 Z','#acb997',None)
    c.line([(914,81),(917,347)],'#9a8a72',8);c.line([(771,221),(1068,217)],'#9a8a72',7)
    c.path('M 735 49 Q 721 163 746 286 L 782 281 Q 760 179 790 50 Z','#e9bd8c',INK,2)
    c.path('M 1055 45 Q 1093 179 1067 288 L 1112 285 Q 1124 187 1101 44 Z','#e9bd8c',INK,2)
    c.path('M 753 56 Q 741 164 762 274 M 1084 58 Q 1101 165 1083 274',None,'#c79579',2)
    c.line([(721,45),(1120,42)],INK,5)
    c.path('M 772 365 L 1175 568 L 863 568 L 761 365 Z','#fff0bb45',None)
    # Crooked pictures.
    with c.transform(x=459,y=124,rotation=-5):
        c.rect(-62,-72,124,144,'#9a7865',INK,2)
        c.rect(-52,-62,104,124,'#ead8af',INK,1)
        c.ellipse(0,-12,28,31,'#b9bd98')
        c.path('M -36 43 Q -11 -9 30 36 L 38 50 L -37 50 Z','#768c7b',None)
        c.path('M -20 0 Q 1 -32 22 -4 M 0 -22 L 0 36',None,'#f4e5bd',3)
    c.path('M 588 104 L 662 111 L 658 198 L 581 194 Z','#b27e65',INK,2)
    c.path('M 594 116 L 649 121 L 646 183 L 591 180 Z','#eee0ba',INK,1)
    c.path('M 607 159 Q 619 124 633 155 Q 641 178 604 170 Z','#d89a74',None)
    # Shelf, books, pottery, lamp and cabinet.
    c.path('M 42 264 L 252 267 L 262 485 L 39 500 Z','#867e6e',INK,2)
    c.path('M 55 278 L 237 281 L 239 470 L 54 484 Z','#9b9980',INK,1)
    for yy in (343,415,477): c.line([(52,yy),(246,yy-5)],'#625f59',5)
    for xx,hh,col in [(63,52,'#c89073'),(81,61,'#6a8c88'),(102,44,'#e5c78f'),(123,54,'#a9ae8d'),(143,59,'#94788b')]:
        c.path(f'M {xx} 337 L {xx-2} {337-hh} L {xx+13} {335-hh} L {xx+15} 337 Z',col,INK,1.3)
        c.line([(xx+3,327),(xx+11,327)],'#ead4a4',1)
    c.ellipse(187,317,22,15,'#c9997b',INK,1.5)
    c.path('M 170 310 L 171 286 Q 187 278 202 286 L 204 311', '#d7b38c',INK,1.5)
    c.path('M 69 390 Q 102 347 122 390 L 122 409 L 69 409 Z','#d6c8a3',INK,1.5)
    c.path('M 161 408 L 159 365 L 213 361 L 215 407 Z','#718782',INK,1.5)
    c.rect(1040,404,183,126,'#9c8973',INK,2)
    c.rect(1050,416,76,96,'#b09a7e',INK,1.4); c.rect(1136,416,76,96,'#b09a7e',INK,1.4)
    c.ellipse(1116,462,3,4,INK);c.ellipse(1146,462,3,4,INK)
    plant(c,1149,400,.83)
    c.line([(990,530),(990,295)],'#716b63',5)
    c.ellipse(990,530,28,6,'#8c8070',INK,1.5)
    c.path('M 951 294 L 964 233 L 1016 233 L 1032 294 Z','#e5c394',INK,2)
    c.ellipse(990,295,40,5,'#c8a680',INK,1)
    c.path('M 976 242 L 969 285 M 1001 242 L 1011 285',None,'#c8a680',1)
    # Long bench establishes the middle plane.
    c.path('M 324 438 Q 537 414 757 439 L 746 489 L 332 491 Z','#83958a',INK,2)
    c.line([(349,488),(342,547)],INK,9);c.line([(724,488),(738,546)],INK,9)
    c.path('M 343 448 Q 537 434 737 449',None,'#b4baa0',2)


@lru_cache(maxsize=4)
def _room_picture(mood,stroke_scale=1):
    recorder=skia.PictureRecorder()
    raw=recorder.beginRecording(skia.Rect.MakeWH(1280,720))
    canvas=Canvas(raw,1280,720)
    canvas.roughness=.38
    canvas.stroke_scale=stroke_scale
    _room(canvas,mood)
    # Small static broken marks suggest pencil and dry brush without raster assets.
    import random
    rng=random.Random(7)
    for _ in range(680):
        x=rng.uniform(0,1280); y=rng.uniform(0,720)
        canvas.line([(x,y),(x+rng.uniform(2,11),y+rng.uniform(-1,1))],'#635a4a0b',rng.uniform(.5,1.2))
    # Soft local shadows preserve the distinction between floor, wall and props.
    for x,y,rx,ry in [(145,502,135,19),(536,501,220,14),(1137,530,118,18)]:
        paint=skia.Paint(AntiAlias=True)
        paint.setShader(skia.GradientShader.MakeRadial((x,y),rx,[color('#493f4a17'),color('#493f4a00')]))
        raw.save()
        raw.translate(x,y);raw.scale(1,ry/rx);raw.translate(-x,-y)
        raw.drawOval(skia.Rect.MakeLTRB(x-rx,y-rx,x+rx,y+rx),paint)
        raw.restore()
    return recorder.finishRecordingAsPicture()


@lru_cache(maxsize=4)
def _room_layer(mood,stroke_scale):
    return StaticLayer(lambda c: c.raw.drawPicture(_room_picture(mood,stroke_scale)),seed=7)


def room(c,mood='day'):
    """Output-aware cached painted set; a new raster is made for each scale bucket."""
    _room_layer(mood,getattr(c,'stroke_scale',1))(c)


def grain(c,amount=.12,seed=1):
    """Fast native-tile transparent paper grain over the finished composition."""
    c.paper(amount=amount,seed=seed)


def table(c):
    c.path('M 600 523 L 1176 513 L 1252 586 L 575 598 Z','#d4a773',INK,2.5)
    c.path('M 575 598 L 1252 586 L 1251 610 L 575 621 Z','#956c53',INK,2)
    c.path('M 606 622 L 600 720 L 628 720 L 640 621 Z','#a67c5e',INK,2)
    c.path('M 1197 613 L 1205 720 L 1233 720 L 1221 610 Z','#a67c5e',INK,2)
    c.path('M 622 556 Q 808 532 1078 544 M 701 582 Q 915 565 1178 571',None,'#b98a61',1.6)
    c.path('M 647 563 L 676 558 M 1114 553 L 1149 554',None,'#e9c393',2)


def steam(c,x,y,t,amount=1):
    for i in range(3):
        phase=(t*.35+i*.3)%1
        xx=x+(i-1)*16+math.sin(t*2+i)*5
        yy=y-phase*70
        alpha=round((1-phase)*.4*amount*255)
        c.path(f'M {xx} {yy} C {xx-18} {yy-15} {xx+18} {yy-28} {xx} {yy-42}',None,f'#fff6dd{alpha:02x}',3)


def accents(c,x,y,t,strength=1):
    """Hand-drawn reaction marks, intentionally sparse and tied to an action."""
    for i in range(3):
        a=(-75+i*30)*math.pi/180
        c.line([(x+math.cos(a)*27,y+math.sin(a)*27),
                (x+math.cos(a)*(41+strength*8),y+math.sin(a)*(41+strength*8))],RUST,2.6)


def cup_fingers(c,x,y,rotation=0,scale=1):
    """Foreground grip drawing. Draw cup, then these fingertips to wrap its edge."""
    with c.transform(x=x,y=y,rotation=rotation,sx=scale,sy=scale):
        for xx,yy in ((-26,-24),(-24,-17),(-20,-10)):
            c.path(f'M {xx-8} {yy-4} Q {xx+5} {yy-8} {xx+8} {yy-2} Q {xx+8} {yy+4} {xx-5} {yy+4} Z',SKIN,INK,1.3)
        c.path('M -29 -28 Q -40 -42 -31 -46 Q -24 -49 -18 -32',SKIN,INK,1.5)


def cookie_fingers(c,x,y,rotation=0,scale=1):
    """Finger pressure drawn over the near plane of a held biscuit."""
    with c.transform(x=x,y=y,rotation=rotation,sx=scale,sy=scale):
        for xx,yy in ((-20,0),(-18,7),(-13,13)):
            c.path(f'M {xx-5} {yy-4} Q {xx+7} {yy-6} {xx+8} {yy} Q {xx+4} {yy+5} {xx-5} {yy+3} Z',SKIN,INK,1.2)


def open_hand(c,x,y,rotation=0,scale=1):
    """A distinct open silhouette for release poses, with an opposing thumb."""
    with c.transform(x=x,y=y,rotation=rotation,sx=scale,sy=scale):
        c.path('M -11 9 L -21 -5 Q -24 -10 -20 -13 Q -17 -15 -13 -8 L -10 -1 '
               'L -12 -23 Q -12 -28 -8 -28 Q -4 -28 -4 -23 L -2 -9 '
               'L 1 -29 Q 2 -35 6 -31 L 8 -8 L 13 -26 Q 17 -30 20 -25 '
               'L 17 -4 L 24 -15 Q 30 -18 29 -11 L 21 12 Q 16 23 2 22 Z',SKIN,INK,1.4)
        c.path('M -3 5 Q 3 -1 12 3 M -9 10 Q -4 8 1 13',None,'#bf7f72',1)
