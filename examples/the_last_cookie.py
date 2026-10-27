"""15-second original cartoon: a stolen cookie, a leap and an unlikely truce."""
import math
from pathlib import Path
from bamboonimation import Scene, Storyboard, AudioClip, ExposureSheet
from bamboonimation.cartoon import grain
from bamboonimation.cartoon import (Actor,Rabbit,Pose,POSES,blend_pose,room,table,
                                     cookie,cookie_fingers,cue,smooth,accents,INK)

mira=Actor(shirt='#9c788b',hair='#4a464f')
pip=Rabbit()
exposures=ExposureSheet()
f=0
while f<360:
    hold=1 if 64<=f<70 or 133<=f<139 or 168<=f<175 else 2
    if f in (48,96,192): hold=6
    boundary=min(k for k in (65,73,75,134,162,173,228,235,264,276,360) if k>f)
    hold=min(hold,boundary-f,360-f);exposures.add(str(f),frames=hold);f+=hold



def actor_state(a):
    progress=smooth(.8,2.9,a)
    jump=cue(a,(0,0),(5.9,0),(6.15,9),(6.55,-67),(7,-35),(7.5,0),(12,0))
    catch=smooth(5.7,6.1,a)*(1-smooth(7.7,8.8,a))
    p=blend_pose(POSES['think'],Pose(left=(-57,-145),right=(176,-113),tilt=9,lean=12),progress)
    p=blend_pose(p,Pose(left=(46,-235),right=(114,-231),tilt=-12,lean=24),catch)
    p=blend_pose(p,Pose(left=(-61,-140),right=(234,-132),tilt=-5,lean=4),smooth(8.5,9.7,a))
    # Both hands meet the biscuit before a piece is broken off and offered.
    share=smooth(9.05,9.8,a)
    reach=smooth(9.8,10.95,a)
    # Step toward Pip while offering; shorten the local reach as the body moves.
    lp=(244+104*reach-120/1.15*reach,-132-8*reach)
    p=Pose(left=p.left,right=(p.right[0]-120/1.15*reach,p.right[1]),tilt=p.tilt,lean=p.lean,crouch=p.crouch)
    p=blend_pose(p,Pose(left=lp,right=p.right,tilt=p.tilt,lean=p.lean),share)
    p=blend_pose(p,Pose(left=(-61,-140),right=p.right,tilt=p.tilt,lean=p.lean),smooth(11.65,12.3,a))
    sq=cue(a,(0,1),(5.8,1),(6.1,.94),(6.6,1.05),(7.5,.95),(7.9,1),(12,1))
    return p,jump,sq


def rabbit_state(a):
    rx=cue(a,(0,1020),(2.3,1020),(2.55,970),(2.75,855),(3.05,763),(3.4,907),(4.2,823),(5.3,794),(6,810),(7,858),(8.2,910),(15,910))
    ry=cue(a,(0,542),(2.3,542),(2.45,552),(2.7,455),(3.05,546),(3.4,458),(4.2,539),(4.55,548),(5.1,500),(5.6,540),(15,540))
    sq=cue(a,(0,1),(2.3,1),(2.45,.75),(2.7,1.19),(3.05,.88),(3.4,1.08),(4.2,.8),(4.6,1),(5.1,1.1),(5.6,.9),(6,1),(15,1))
    return rx,ry,sq


def rabbit_anchor(a):
    x,y,sq=rabbit_state(a)
    return x-31*1.12/sq,y-20*1.12*sq


def actor_x(a):return 485+120*smooth(9.8,10.95,a)

def actor_walk(a):return math.tau*smooth(9.8,10.95,a)

def held_anchor(a,side='right'):
    p,jump,sq=actor_state(a)
    x,y,_=mira.hand_anchor(side,actor_x(a),670+jump,a,scale=1.15,pose=p,squash=sq,walk=actor_walk(a))
    return (x+8,y-3) if side=='right' else (x-3.5,y-3)


def biscuit_part(c,x,y,rotation,part='whole',scale=.85):
    with c.transform(x,y,rotation=rotation,sx=scale):
        if part=='whole':cookie(c,0,0)
        else:
            shape='M-40 -40L0 -40L0 40L-40 40Z' if part=='main' else 'M0 -40L40 -40L40 40L0 40Z'
            with c.clip(shape):cookie(c,0,0)
            c.path('M0 -25L-2 -16L2 -8L-2 1L1 10L-1 19L0 27',None,INK,1.6)


def paint(c,t):
    a=exposures.time(t)
    z=cue(t,(0,1.05),(2,1.05),(3.2,1.16),(8,1.16),(10.2,1.04),(12,1.04))
    c.roughness=.5
    with c.transform(x=640,y=360,sx=z,sy=z):
        c.translate(-640,-360)
        room(c)
        # Reaching across the table, then a full-body catch with follow-through.
        p,jump,actor_squash=actor_state(a)
        expression='curious' if a<3 else 'surprise' if a<7.7 else 'delighted' if a<12.4 else 'content'
        mira.draw(c,actor_x(a),670+jump,a,scale=1.15,pose=p,walk=actor_walk(a),expression=expression,look=(4,-2),blink=(12.5<a<12.7),
                  squash=actor_squash,knee_bend=cue(a,(0,0),(5.8,0),(6.1,20),(6.6,-9),(7.5,18),(7.9,0)),
                  hand_shapes={'right':'open'} if 5.7<a<6.75 else {},front_hands=('left',) if a>9.05 else ())
        table(c)
        # Empty plate and crumbs ground the prop in the set.
        c.ellipse(732,546,65,12,'#d0b795',INK,1.8)
        c.ellipse(732,544,54,8,'#efe0bb',INK,1.3)
        for xx,yy in [(714,541),(749,545),(735,549),(763,540)]:
            c.path(f'M {xx} {yy} l 3 -2 l 2 4 Z','#b98554',None)
        rx,ry,squash=rabbit_state(a)
        pip.draw(c,rx,ry,a,scale=1.12,look=(-2,-1),squash=squash,
                 expression='laugh' if 11.15<a<11.65 or 11.8<a<12.9 else 'sleepy' if a>13 else 'content')
        if a>=6.75:
            mira.draw_arm(c,'right',actor_x(a),670+jump,a,scale=1.15,pose=p,squash=actor_squash,walk=actor_walk(a))
        if a>9.05:
            mira.draw_arm(c,'left',actor_x(a),670+jump,a,scale=1.15,pose=p,squash=actor_squash,walk=actor_walk(a))
        # Plate contact precedes the snatch; the held biscuit shares the paw clock.
        if a<3.05:
            cx,cy=732,524;rot=-14
        elif a<5.6:
            ax,ay=rabbit_anchor(a);u=smooth(3.05,3.125,a)
            cx,cy=732+(ax-732)*u,524+(ay-524)*u
            rot=cue(a,(3.05,-14),(3.4,60),(4.2,120),(5.6,190))
        elif a<6.75:
            x0,y0=rabbit_anchor(5.6);x1,y1=held_anchor(6.75)
            u=(a-5.6)/1.15
            cx=x0+(x1-x0)*u
            cy=y0+(y1-y0)*u-4*175*u*(1-u)
            rot=190+290*u
        else:
            cx,cy=held_anchor(a)
            rot=cue(a,(6.75,480),(7.2,500),(8.6,360),(9.5,360),(15,360))
        # A short connected forearm approaches the biscuit, then wraps its rim.
        if 2.9<a<5.6:
            c.path(f'M{rx-7} {ry-24}Q{rx-14} {ry-6} {cx+9} {cy+13}',None,'#f5dfb0',13)
        biscuit_part(c,cx,cy,rot,'main' if a>=9.8 else 'whole')
        if 3.05<=a<5.6:
            for dx,dy in ((9,12),(15,7)):
                c.ellipse(cx+dx,cy+dy,6,3.5,'#f7e6be',INK,1.1)
        if a>=6.75:cookie_fingers(c,cx,cy,rot,scale=.85)
        if a>=9.8 and a<11.65:
            piece_x,piece_y=held_anchor(a,'left')
            eat=1-smooth(11.15,11.65,a)
            biscuit_part(c,piece_x,piece_y,0,'share',scale=.85*eat)
            if a<11.15:
                with c.transform(piece_x,piece_y,sx=-1):cookie_fingers(c,0,0,0,scale=.85)
        if 2.8<a<3.5: accents(c,915,389,a)
        if 6<a<6.9:
            for i in range(3):
                c.path(f'M {cx+35+i*8} {cy+21+i*10} q 16 15 23 28',None,'#a3837455',2)
    grain(c,amount=.14,seed=33)


def shot(start,end,focus,zoom):
    def draw(c,local):
        c.stroke_scale=1/zoom
        with c.transform(x=640,y=360,sx=zoom,sy=zoom):
            c.translate(-focus[0],-focus[1])
            paint(c,start+local)
    return Scene(duration=end-start,painter=draw,seed=33)

scene=Storyboard(background='#e4d4b5',seed=33)
for spec in [(0,2.7,(640,360),1),(2.7,4.2,(867,485),1.65),
             (4.2,5.6,(802,474),1.9),(5.6,7.2,(642,360),1),
             (7.2,9.5,(625,414),1.65),(9.5,15,(640,360),1)]:
    scene.add(shot(*spec))

scene.audio.append(AudioClip(Path(__file__).resolve().parents[1]/"assets/audio/the_last_cookie.wav"))
