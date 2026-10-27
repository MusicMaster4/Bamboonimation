"""15-second directed cartoon with original drawings and motivated shots.

Reference-study body acting round: variable exposures, anticipation, single-frame smears,
profile replacements, registered cup grips, strong pose changes and contact cuts.
Render with: python -m bamboonimation render examples/tea_for_two.py -o renders/tea.mp4
"""
import math
from dataclasses import replace
from pathlib import Path
from bamboonimation import Scene, Storyboard, AudioClip, WarpCanvas, LatticeWarp
from bamboonimation.acting import ExposureSheet
from bamboonimation.effects import speed_lines
from bamboonimation.cartoon import (Actor,Rabbit,Pose,FacePose,BodyPose,BODY_POSES,blend_body,POSES,blend_pose,room,table,
                                     cup,cup_fingers,steam,cue,smooth,accents,grain,INK)

mira=Actor()
pip=Rabbit()
# All action beats are source-frame boundaries. Export FPS remains independent.
RELEASE = 115/24
TAKEOFF = 121/24
LANDING = 139/24
CATCH = 149/24
SETTLE = 160/24
SETDOWN = 180/24
HAND_RELEASE = 184/24

exposures=ExposureSheet(fps=24)
f=0
boundaries=(44,64,84,96,114,115,116,118,121,126,130,134,138,139,143,147,149,152,154,160,168,180,184,197,216,240,276,360)
while f<360:
    hold=1 if 114<=f<=143 or 147<=f<=160 else 2
    if f in (84,96,216,240):hold=6
    hold=min(hold,min(k for k in boundaries if k>f)-f,360-f)
    exposures.add(str(f),frames=hold)
    f+=hold


def grounded(body, *, landed=False):
    # Feet are support points, not children of the chest/pelvis articulation.
    return replace(body,left_foot=(-32,-9) if landed else (-29,-9),
                   right_foot=(36,-9) if landed else (29,-9),heel_lift=(0,0))


STAND=grounded(BODY_POSES['neutral'])
REACH=grounded(replace(BODY_POSES['reach'],chest=(18,7),pelvis=(-5,5),head=(4,-2),
                       chest_angle=9,pelvis_angle=-4,head_angle=-5))
BRACE=grounded(replace(BODY_POSES['brace'],chest=(-16,8),pelvis=(5,16),head=(-8,0),
                       chest_angle=-13,pelvis_angle=5,head_angle=8))
LAUNCH=grounded(replace(BRACE,chest=(-26,-12),pelvis=(2,6),chest_angle=-18,pelvis_angle=6))
AIR=replace(BODY_POSES['airborne'],chest=(-33,-9),pelvis=(9,4),head=(12,-5),
            chest_angle=-23,pelvis_angle=9,head_angle=15)
LAND=grounded(replace(BODY_POSES['brace'],chest=(10,13),pelvis=(8,18),
                       chest_angle=8,pelvis_angle=-4),landed=True)
CONTACT=grounded(replace(BODY_POSES['catch'],chest=(20,5),pelvis=(2,7),head=(6,-2),
                          chest_angle=8,pelvis_angle=-3,head_angle=-4),landed=True)
CUSHION=replace(CONTACT,chest=(10,16),pelvis=(8,17),head=(3,-1),chest_angle=3,pelvis_angle=-5)
REST=grounded(replace(BODY_POSES['neutral'],chest=(8,3),pelvis=(0,3),chest_angle=3,pelvis_angle=-1),landed=True)
END=grounded(BODY_POSES['neutral'],landed=True)
BODY_KEYS=[
    (0,STAND),(.75,STAND),
    (26/24,grounded(replace(BODY_POSES['reach'],chest=(-3,2),pelvis=(-4,3),chest_angle=-2,pelvis_angle=1))),
    (33/24,grounded(replace(REACH,chest=(12,4),pelvis=(-6,5),head=(6,-2),chest_angle=7,pelvis_angle=-3))),
    (40/24,REACH),(1.9,REACH),(2.7,STAND),(114/24,STAND),
    (118/24,BRACE),(TAKEOFF,LAUNCH),(126/24,AIR),(130/24,AIR),
    (134/24,replace(AIR,chest=(-12,-2),pelvis=(5,7),chest_angle=-10,head_angle=7)),
    (LANDING,LAND),(143/24,replace(LAND,chest=(4,6),pelvis=(3,9),chest_angle=2,left_knee=(-40,-43),right_knee=(43,-42))),
    (CATCH,CONTACT),(154/24,CUSHION),(SETTLE,REST),(7,REST),(8.4,END),(15,END),
]


def body_state(t):
    for (start,a),(end,b) in zip(BODY_KEYS,BODY_KEYS[1:]):
        if t<=end:return blend_body(a,b,smooth(start,end,t))
    return END


def motion_state(t):
    if t<TAKEOFF:return 500,669,0
    if t<LANDING:
        q=t-TAKEOFF;duration=LANDING-TAKEOFF
        return (500+85*q/duration,
                669-1100*duration*.5*q+550*q*q,
                cue(t,(TAKEOFF,0),(5.4,-5),(5.65,3),(LANDING,0)))
    return 585,669,0


def cup_state(t):
    if RELEASE<=t<CATCH:
        q=t-RELEASE;duration=CATCH-RELEASE;gravity=800
        vy=(465-508-.5*gravity*duration*duration)/duration
        return 690+80*q/duration,508+vy*q+.5*gravity*q*q,-360*q/duration
    return (cue(t,(0,706),(1.8,706),(2.65,690),(RELEASE,690),(CATCH,770),(6.65,735),(SETDOWN,707)),
            cue(t,(0,543),(1.8,543),(2.65,508),(RELEASE,508),(CATCH,465),(CATCH+.125,480),(6.65,490),(SETDOWN,543)),
            cue(t,(0,0),(RELEASE,0),(CATCH,-360),(15,-360)))


def world(c,t):
    a=exposures.time(t)
    f=int(a*24+.001)
    c.roughness=.38
    c.boil_fps=12
    room(c)
    if 4.79<a<4.96:
        speed_lines(c,a,center=(520,430),count=12,radius=(130,800),length=(50,160),
                    color='#6d7164',width=(.8,1.6),opacity=.22,seed=44)
    ax,ay,body_angle=motion_state(a)
    body=body_state(a)
    cx,cy,rot=cup_state(a)
    reach=smooth(.9,1.8,a)
    grip=(1.8<=a<RELEASE) or CATCH<=a<HAND_RELEASE
    p=blend_pose(POSES['idle'],Pose(left=(-61,-144),right=(155,-120),tilt=7),reach)
    if grip:
        p=Pose(left=(cue(a,(CATCH,-88),(152/24,-88),(SETTLE,-58)),
                     cue(a,(CATCH,-220),(152/24,-220),(SETTLE,-137))) if a>=CATCH else (-58,-137),
               tilt=cue(a,(0,7),(4.6,7),(CATCH,-4),(7.7,5)))
    elif a>=HAND_RELEASE:
        p=blend_pose(Pose(left=(-58,-137),right=(63,-135),tilt=-8),POSES['idle'],smooth(HAND_RELEASE,8.7,a))
        if a>12:p=blend_pose(p,Pose(left=(-57,-146),right=(-10,-220),tilt=8),smooth(12,12.7,a)*(1-smooth(13,13.8,a)))
    elif a>=RELEASE:
        p=blend_pose(POSES['surprise'],Pose(left=(-88,-220),right=(159,-231),tilt=-3),smooth(RELEASE,5.3,a))
        p=replace(p,lean=0,crouch=0)
    # Body deformation carries the weight; the feet keep their authored support.
    squash=1
    walk=0
    receiving=5.3<=a<CATCH
    approaching=.9<=a<1.8
    if grip or receiving or approaching:
        gap=85*(1-smooth(5.65,CATCH,a)) if receiving else 0
        wx,wy=cx-33-gap,cy-22+(65*(1-smooth(5.65,CATCH,a)) if receiving else 0)
        if approaching:
            wx=cue(a,(.9,580.5),(1.8,673));wy=cue(a,(.9,519.5),(1.8,521))
        p=mira.pose_for_hand('right',(wx,wy),ax,ay,a,scale=1.15,pose=p,walk=walk,
                             squash=squash,rotation=body_angle,body=body)
    expression='shout' if 4.9<a<5.7 else 'worried' if 5.7<a<6.7 else 'sleepy' if 12.5<a<13.0 else 'content' if a>11.4 else 'delighted' if a>8.7 else 'curious'
    view='profile' if 1.35<=a<8.5 else 'three_quarter' if .9<=a<1.35 else 'front'
    face=None;shoulder_turn=0
    look=(cue(a,(0,0),(.45,0),(.75,4)),
          cue(a,(0,0),(.45,0),(.75,5),(RELEASE,5),(5.1,-4),(5.8,-4),(CATCH,3),(15,3)))
    blink=(11.1<a<11.3 or 13.2<a<13.37) if a>10.4 else None
    if 9<=a<11.5:
        # Eyes lead; the head follows, then the shoulders counterturn and settle.
        # Face is exposed on ones independently of the body's held drawings.
        ft=math.floor(t*24)/24
        view='three_quarter'
        look=(cue(ft,(9,1),(9.28,1),(9.52,4)),cue(ft,(9,5),(9.28,5),(9.52,2.5),(10.5,3.3)))
        p=replace(p,tilt=cue(a,(9,-8),(9.55,-8),(9.9,12),(10.3,5)),
                  lean=cue(a,(9,0),(9.55,0),(10,-8),(10.4,-3),(11.5,0)))
        shoulder_turn=cue(a,(9,0),(9.62,0),(10.03,-.65),(10.7,-.25))
        face=FacePose(eye_open=(cue(ft,(9,1),(9.65,1),(9.88,.45),(10.2,.45),(10.48,1)),
                               cue(ft,(9,1),(9.88,.9),(10.48,1))),
                      brow_offset=(cue(ft,(9,-2),(9.9,4),(10.5,-3)),cue(ft,(9,-1),(9.9,-4),(10.5,-1))),
                      cheek=cue(ft,(9,0),(9.7,4),(10.4,0),(10.9,5),(11.5,2)),
                      jaw=cue(ft,(9,2),(9.6,5),(10.1,-2),(10.55,5),(11.4,0)))
        blink=10.35<=ft<10.46 or 11.15<=ft<11.23
        expression='worried' if ft<9.85 else 'content' if ft<10.45 or ft>=11.2 else 'delighted'
    # Connected actor remains readable through the extreme action. The single
    # smear extends its silhouette; it does not replace the body with fragments.
    height=max(0,669-ay)
    c.ellipse(ax,674,67*(1-.22*height/80),8,'#493f4a'+f'{round(34-17*height/80):02x}')
    with c.transform(x=ax,y=ay,rotation=body_angle):
        actor_canvas=c
        if f==116:
            # The entire connected actor shares a single displacement field.
            warp=LatticeWarp((-180,-410,240,20),[[(12,-6),(55,-18)],[(-45,8),(65,-8)],[(0,0),(8,0)]])
            actor_canvas=WarpCanvas(c,warp)
        mira.draw(actor_canvas,0,0,a,scale=1.15,pose=p,expression=expression,view=view,
                  look=look,face=face,shoulder_turn=shoulder_turn,blink=blink,walk=walk,body=body,shadow=False,
                  front_hands=('right',) if 12<a<13.8 else (),
                  hand_shapes={'right':'open'} if receiving or approaching or HAND_RELEASE<=a<8.2 else {},
                  squash=squash)
    table(c)
    if grip or approaching or HAND_RELEASE<=a<8.2:
        # The table may cover the torso, but the grasping forearm is above it.
        with c.transform(x=ax,y=ay,rotation=body_angle):
            mira.draw_arm(c,'right',0,0,a,scale=1.15,pose=p,walk=walk,squash=squash,
                          shape='open' if approaching or a>=HAND_RELEASE else 'fist',body=body,occlude_root=True)
    c.ellipse(707,549,46,8,'#e9ce9f',INK,1.3)
    # Ear drag: the head recoils before the long ears settle back into the model.
    squash=cue(a,(0,1),(3.5,1),(4.0,.93),(4.4,.77),(4.59,.71),(4.71,1.23),
                 (4.88,.87),(5.2,1.06),(5.65,1),(12,1))
    py=cue(a,(0,544),(4.6,544),(4.75,519),(5.1,544),(8.5,544),(9,519),(9.4,544),(12,544))
    pip.draw(c,1010,py,a,scale=1.25,expression=('sleepy' if a<3.4 else 'inhale' if a<4.65 else 'sneeze' if a<4.92 else 'laugh' if 9<a<10.3 else 'sleepy' if a>13.6 else 'content'),
             look=(-2,-1),squash=squash)
    if 4.65<a<5.0:
        for i in range(5):
            q=(a-4.65)*3
            c.ellipse(970-q*(70+i*25),477+i*8-q*22,3+i,1.7,'#e9ead399')
        accents(c,984,419,a)
    cup(c,cx,cy,rot)
    if grip: cup_fingers(c,cx,cy,rot)

    steam(c,cx,cy-66,a,amount=1-smooth(4.7,5.1,a))
    # Hand-drawn tea droplets continue after the cup stops, establishing weight.
    if 4.9<a<CATCH:
        for i in range(7):
            q=a-4.9-i*.045
            if 0<q<1.25:
                xx=735+q*(66+i*18)
                yy=379-q*125+q*q*235+i*4
                c.ellipse(xx,yy,2,3.5,'#926951')
    if CATCH-.2<a<CATCH:
        c.path('M 762 447 Q 780 437 792 431 M 766 460 Q 789 452 800 442',None,'#cc7053',2)
    if 8.8<a<10.5:
        c.path('M 954 444 Q 961 434 968 440 M 1052 443 Q 1060 433 1066 441',None,'#cc7053',1.5)


def shot(start,end,focus,zoom=1,angle=0):
    def paint(c,local):
        t=start+local
        # A short camera settle responds to the catch; no accumulated simulation.
        shake=max(0,1-(t-CATCH)/.22) if CATCH<=t<CATCH+.22 else 0
        dx=math.sin((t-CATCH)*95)*4*shake
        dy=math.cos((t-CATCH)*71)*2*shake
        c.stroke_scale=1/zoom
        with c.transform(x=640+dx,y=360+dy,rotation=angle,sx=zoom,sy=zoom):
            c.translate(-focus[0],-focus[1])
            world(c,t)
        grain(c,amount=.11,seed=17)
    return Scene(width=1280,height=720,duration=end-start,background='#e4d4b5',seed=17,painter=paint)


# Motivated cuts: establish place -> hand/prop -> sneeze -> consequence -> catch.
scene=Storyboard(width=1280,height=720,seed=17,background='#e4d4b5')
for spec in [
    (0,1.75,(640,360),1,0),
    (1.75,3,(740,507),3.1,-5),
    (3,4.666666666666667,(1000,482),2.7,2),
    (4.666666666666667,4.791666666666667,(1000,475),2.9,-3),
    (RELEASE,5.75,(690,385),1.03,0),
    (5.75,7,(700,440),1.35,0),
    (7,8.5,(735,504),2.9,3),
    (8.5,9,(640,360),1,0),
    (9,11.5,(800,463),1.6,0),
    (11.5,15,(640,360),1,0),
]: scene.add(shot(*spec))

scene.audio.append(AudioClip(Path(__file__).resolve().parents[1]/"assets/audio/tea_for_two.wav"))
