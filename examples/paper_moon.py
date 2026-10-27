"""Paper Moon: a fifteen-second original ink-and-paper creature story.

A paper crane unfolds into a five-tailed fox to save a falling moon-seed.
All art, staging and replacement drawings are authored below with vector paths.
No external assets, reference characters, paid calls or generated image frames.

bamboonimation render examples/paper_moon.py -o renders/paper_moon/paper_moon.mp4 --fps 24
"""
from __future__ import annotations
import math
import random
from functools import lru_cache
import skia
from bamboonimation.drawing import svg_path
from pathlib import Path
from bamboonimation import (Scene,Storyboard,DrawingBank,ExposureSheet,LatticeWarp,
                            warp_path,StaticLayer)
from bamboonimation.effects import hatch,impact_flash,speed_lines

W,H=1280,720
TAU=math.tau
P={'ink':'#253343','night':'#172d40','sky':'#203f50','sage':'#9cae98',
   'paper':'#e9d5ab','light':'#fff1c5','coat':'#c88c68','rust':'#a56759',
   'shadow':'#694f57','blue':'#658c93','moon':'#f0dfb2'}

def ramp(a,b,t):
    u=max(0,min(1,(t-a)/(b-a)))
    return u*u*(3-2*u)

def cue(t,*keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*ramp(a,b,t)
    return keys[-1][1]

# Only subject drawings use this sheet; camera and atmospheric effects have
# independent clocks. Protect the one-frame smear and two impact exposures.
exposure=ExposureSheet(fps=24)
f=0
boundaries=(55,61,68,72,75,76,77,78,80,81,84,124,132,134,138,144,148,156,182,202,209,264,303,360)
while f<360:
    hold=1 if 68<=f<=83 or 124<=f<=143 else 2
    if f in (0,36,52,66,156,204,232,264):hold=6
    next_boundary=min(k for k in boundaries if k>f)
    hold=min(hold,next_boundary-f,360-f)
    exposure.add(str(f),frames=hold)
    f+=hold



def leaf(c,x,y,scale,rotation,fill):
    with c.transform(x,y,rotation=rotation,sx=scale):
        c.path('M0 0 C-38 -8 -58 -54 -20 -80 Q-17 -29 0 0Z',fill,P['ink'],1.2)
        c.path('M0 0Q-25 -34 -20 -69 M-11 -22L-31 -30 M-18 -42L-34 -50',None,'#426269',.8)


def background(c):
    c.gradient_rect(0,0,W,H,['#173244','#305561','#71817b'])
    # Painted moonlight, fine clouds and distant hills.
    c.ellipse(994,148,91,91,'#b7c0a512')
    c.ellipse(994,148,76,76,'#c7c8a51d')
    c.ellipse(994,148,65,65,P['moon'])
    c.path('M965 94Q924 161 986 205Q936 179 932 145Q932 111 965 94Z','#d1c6a5',None)
    for x,y,rx,ry in [(1015,122,12,17),(974,172,9,7),(1012,185,7,4)]:
        c.ellipse(x,y,rx,ry,'#c5bda235')
    for n in range(38):
        rng=random.Random(902+n)
        x,y=rng.uniform(70,1220),rng.uniform(40,330)
        c.ellipse(x,y,rng.uniform(.5,1.3),.8,'#c5d0b277')
    c.path('M0 361 Q145 276 308 359 Q505 264 664 348 Q892 269 1068 338 Q1170 304 1280 340 L1280 720L0 720Z','#385b65',None)
    c.path('M0 429 Q139 337 333 421 Q544 315 748 433 Q1029 330 1280 389 L1280 720L0 720Z','#345762',None)
    # Cypress trunks and imperfect hand-painted stone wall.
    for x,y,s in [(91,422,.8),(209,401,.55),(1156,395,.65),(1236,443,.9)]:
        with c.transform(x,y,sx=s):
            c.path('M-49 13Q-62 -39 -33 -94Q-40 -160 -5 -248Q21 -207 19 -164Q57 -107 30 -68Q58 -21 33 16Z','#284b58',None)
            c.path('M-5 35L-3 -169M-3 -76L-26 -110M-3 -114L13 -136',None,'#527575',2)
    c.path('M0 488L173 469L300 488L478 469L660 486L839 463L1010 481L1280 457L1280 604L0 604Z','#507075',P['ink'],2)
    for row in range(3):
        y=490+row*34
        c.path(f'M0 {y}Q300 {y+16} 640 {y-2}T1280 {y-16}',None,'#365661',1.3)
        for x in range(-60+row%2*60,1300,117):
            c.path(f'M{x} {y-1}l5 31',None,'#365661',1.2)
    c.path('M0 591Q211 549 452 594Q732 537 995 583Q1141 553 1280 572L1280 720L0 720Z','#42636a',None)
    for x,y,s in [(45,614,1.1),(134,600,.65),(1147,610,.8),(1249,601,1.3)]:
        for a in (-58,-18,25,62):leaf(c,x,y,s,a,'#769080')
    # Gnarled branch from the right: the moon-seed is attached to its last twig.
    c.path('M1305 80C1158 102 1105 225 979 240Q890 248 823 206L815 215'
           'Q879 268 987 260C1125 248 1191 135 1305 139Z','#354c55',P['ink'],2)
    c.path('M1270 109Q1107 249 967 248M1115 213Q1100 157 1060 144M1015 249Q1023 292 996 318',None,'#6b8077',2)
    for x,y,s,a in [(1187,168,.7,80),(1114,191,.8,15),(1067,151,.7,70),
                    (1007,280,.55,155),(947,247,.5,15),(893,242,.55,40)]:
        leaf(c,x,y,s,a,'#84977d')
    # Moss-covered foreground stepping stones; subject registration is y=613.
    c.path('M239 626Q250 589 323 586L850 578Q946 584 965 624L942 657'
           'L275 669Z','#62777a',P['ink'],2.8)
    c.path('M254 621Q399 597 569 607Q779 591 945 618L930 638Q552 623 275 647Z','#91a293',None)
    c.path('M278 649Q548 628 930 638L920 652L287 665Z','#3e5966',None)
    c.path('M362 605l-16 27 16 25M674 602l14 28-12 23M823 596l-18 23 11 16',None,'#45616a',1.3)
    for n in range(17):
        x=275+n*39
        c.ellipse(x,621+math.sin(n*1.2)*4,10+n%3*3,3,'#9aab8a')
    # Fine ink grass and flowers frame the stone without hiding contact.
    for n in range(26):
        x=(n*89+25)%1280
        y=682+(n%3)*12
        c.path(f'M{x} {y}q-5 -34 -18 -46 M{x} {y}q9 -43 27 -56',None,'#1e404f',1.5)
        if n%3==0:
            c.ellipse(x+23,y-48,5,3,'#bcaa97')
    c.paper(.12,seed=42)

BG=StaticLayer(background,seed=42,max_cache_bytes=80*1024*1024)


def seed(c,x,y,t,scale=1,glow=True):
    with c.transform(x,y,sx=scale):
        if glow:
            c.ellipse(0,0,25,25,'#ffe9a312')
            c.ellipse(0,0,16,16,'#ffe9a31c')
        c.path('M0 -12C11 -12 17 -2 8 8Q0 15 -9 6C-17 -4 -8 -12 0 -12Z',P['light'],P['ink'],1.2)
        c.path('M-6 -7Q-10 0 -5 5',None,'#c7a96d',1)
        c.path('M1 -11Q8 -26 17 -25Q14 -13 1 -11Z','#a8b78b',P['ink'],.8)
        c.path('M-5 -5L3 3M-3 2L4 -4',None,'#ead193',.7)


def crane(c,t,unfold=0):
    # Registration sits on the stone; every wing shares the folded body seam.
    u=unfold if unfold else .025*math.sin(t*2.4)
    c.path('M-30 0L-17 -14L-4 -8L-5 0Z','#afaa9a',P['ink'],1)
    c.path('M12 0L14 -13L26 -10L33 0Z','#afaa9a',P['ink'],1)
    c.path('M-62 -42L-143 -64L-65 -15L-17 -13Z','#c2bcaa',P['ink'],1.7)
    # Rear wing opens before the near wing.
    c.path(f'M-55 -35L{-105-u*80} {-101-u*62}L{-7-u*25} {-62-u*34}L24 -30Z','#b7c5b8',P['ink'],1.6)
    c.path('M-65 -32L-5 -69L55 -43L30 -8L-15 -4Z',P['paper'],P['ink'],2)
    c.path('M-65 -32L-5 -69L-17 -19Z','#f3e3be',None)
    c.path('M-17 -19L30 -8L55 -43L8 -34Z','#c7b699',None)
    c.path(f'M-18 -20L{-64-u*77} {-111-u*77}L{21+u*38} {-69-u*22}L38 -20Z',P['light'],P['ink'],1.7)
    c.path(f'M-18 -20L{-64-u*77} {-111-u*77}L8 -34Z','#d1c5a5',None)
    c.path('M28 -30L47 -97L77 -122L91 -105L67 -91L59 -35Z',P['paper'],P['ink'],1.7)
    c.path('M47 -97L77 -122L65 -91L59 -35Z','#f5e7c4',None)
    c.path('M77 -122L119 -113L91 -105Z','#bd9273',P['ink'],1.1)
    c.ellipse(78,-112,2,2,P['ink'])
    c.path('M-55 -33L-17 -19L8 -34M47 -97L65 -91',None,'#9d9f91',1)
    # Tiny star pattern survives as the fox's shoulder marking.
    c.path('M-6 -52L-2 -44L7 -43L0 -38L1 -30L-6 -35L-13 -31L-11 -40L-17 -46L-9 -46Z','#809895',None)


# Fox model: consistent warm coat, dark paws, cream muzzle, five joined tails,
# pale diamond shoulder and hooked paper-fold whiskers in all replacements.
TAIL='M-69 -64C-125 -42 -167 -111 -154 -182C-120 -153 -77 -143 -85 -100Q-72 -79 -69 -64Z'
TAILTIP='M-154 -182C-137 -151 -112 -148 -95 -128L-104 -113Q-149 -127 -154 -182Z'

def tails(c,t,fan=1,back=False):
    for i in range(5):
        angle=(-74+i*31)*fan+math.sin(t*2.5-i*.8)*4
        drag=math.sin(t*3-i*.7)*6
        warp=LatticeWarp((-175,-190,-55,-30),(((drag,-3),(drag*.5,2)),((0,0),(0,0))))
        with c.transform(-75,-69,rotation=angle):
            c.translate(69,64)
            c.path(warp_path(TAIL,warp),P['rust'] if i%2 else P['coat'],P['ink'],1.8)
            c.path(warp_path(TAILTIP,warp),P['paper'],P['ink'],1.2)
            c.path('M-84 -77Q-122 -97 -145 -147',None,'#e2b48a',1)
            if i in (0,3):
                hatch(c,warp_path(TAIL,warp),spacing=8,angle=65,color='#593f4844',width=.7,seed=i,jitter=.5)


def head(c,t,view='profile',mood='alert',ear=0):
    # Head origin is the neck junction. Shapes overlap to maintain connection.
    if view=='profile':
        c.path('M-35 0L-55 -24L-41 -34L-48 -55L-28 -50L-23 -100L3 -67'
               'L28 -104L30 -59Q52 -49 62 -28L94 -15L69 1L45 10Q8 37 -35 0Z',P['coat'],P['ink'],2)
        c.path('M-22 -87L-17 -52L-3 -62Z','#744f57',None)
        c.path('M25 -91L13 -66L27 -61Z','#744f57',None)
        c.path('M-35 -11Q-8 5 14 -19Q41 -40 62 -28L94 -15L69 1L45 10Q11 28 -10 15Z',P['paper'],None)
        c.path('M4 -24Q22 -46 39 -28Q23 -13 4 -24Z',P['light'],P['ink'],1.2)
        if mood=='sleep':c.path('M9 -25Q23 -16 34 -27',None,P['ink'],2)
        else:
            c.ellipse(27,-26,3.2,6,P['ink'])
            c.ellipse(28,-29,1.1,1.7,P['light'])
        c.path('M83 -18L95 -15L86 -7L79 -10Z',P['ink'],None)
        c.path('M45 -1Q61 8 76 -2M52 10l7 -1',None,P['ink'],1.2)
        c.path('M-29 -38Q-15 -48 -2 -38M8 -46Q24 -53 37 -43',None,P['ink'],1.4)
        c.path('M-27 -9l-21 5M-22 -3l-24 12',None,'#f0d1a1',1)
    else:
        c.path('M-48 2L-65 -23L-49 -23L-59 -58L-38 -49L-40 -105L-5 -73'
               'L30 -110L41 -61L61 -47L53 -22L65 -21L44 8L5 31Z',P['coat'],P['ink'],2)
        c.path('M-34 -91L-27 -61L-11 -70Z','#77535a',None)
        c.path('M28 -96L12 -75L33 -65Z','#77535a',None)
        c.path('M-48 2L-47 -25Q-24 -3 -9 -13L2 -3L15 -18Q32 -14 51 -31L44 8L5 31Z',P['paper'],None)
        for x,y in [(-22,-34),(27,-38)]:
            if mood=='sleep':c.path(f'M{x-11} {y}Q{x} {y+10} {x+10} {y-2}',None,P['ink'],1.8)
            else:
                c.path(f'M{x-13} {y-2}Q{x} {y-17} {x+11} {y-2}Q{x} {y+9} {x-13} {y-2}Z',P['light'],P['ink'],1)
                c.ellipse(x+2+(2-4*ramp(12.6,14.8,t) if t>12.6 else 0),y-3,2.5,5,P['ink'])
                c.ellipse(x+3,y-5,1,1.5,P['light'])
        c.path('M-4 -3L10 -5L4 5Z',P['ink'],None)
        c.path('M4 5Q-2 17 -11 11M4 5Q12 16 22 9',None,P['ink'],1.2)
        c.path('M-42 -7l-25 3M-39 0l-22 12M40 -8l24 -5M38 0l23 9',None,'#edd4ad',1.1)
        c.path('M-33 -55Q-21 -63 -9 -55M15 -60Q28 -68 40 -58',None,P['ink'],1.3)
    c.path('M-8 -59L-3 -51L5 -61L-1 -43Z','#f1d9a9',None)


def paw(c,x,y,angle=0):
    with c.transform(x,y,rotation=angle):
        c.path('M-13 -15Q-20 -5 -15 7Q-3 18 14 8Q24 2 16 -10L4 -18Z',P['paper'],P['ink'],1.4)
        c.path('M-7 1l-1 7M1 2l1 7M9 0l3 6',None,'#a78874',.8)


@lru_cache(maxsize=256)
def contour_between(source,target,step):
    # Authored contour pairs use the same hip/shoulder/paw registration.
    # Arc-length samples are only an inbetweening aid, never a new character.
    u=step/12
    a=skia.PathMeasure(svg_path(source),True)
    b=skia.PathMeasure(svg_path(target),True)
    out=skia.Path()
    for i in range(100):
        pa=a.getPosTan(a.getLength()*i/100)[0]
        pb=b.getPosTan(b.getLength()*i/100)[0]
        x=pa.x()*(1-u)+pb.x()*u;y=pa.y()*(1-u)+pb.y()*u
        if i==0:out.moveTo(x,y)
        else:out.lineTo(x,y)
    out.close()
    return out


def gather(c,t,u):
    # Thirteen connected replacement drawings gather four limbs under the body.
    # The reaching paw has its own registered anchor throughout this passage.
    step=round(u*12);u=step/12
    def shape(a,b,fill,stroke=P['ink'],width=1.8):
        c.path(contour_between(a,b,step),fill,stroke,width)
    tails(c,t,fan=.68+.32*u)
    shape('M-81 -59Q-100 -39 -132 -15L-170 -2Q-184 4 -177 15L-144 17Q-111 3 -70 -8L-34 -42Z',
          'M-72 -59Q-97 -26 -76 -4L-45 0L-24 -41Z',P['rust'])
    shape('M32 -58Q75 -74 115 -94L148 -92Q159 -87 147 -77L119 -77Q87 -41 50 -24Z',
          'M44 -55L57 -9L84 -8Q100 1 87 8L52 10Q38 5 32 -30Z',P['rust'])
    shape('M-91 -66Q-102 -107 -39 -122Q16 -139 65 -107L83 -71Q48 -29 8 -33Q-45 -24 -78 -41Z',
          'M-85 -59Q-111 -105 -63 -135Q-30 -151 12 -128Q26 -160 55 -148Q84 -134 77 -95L59 -65Q33 -43 -8 -38Q-57 -26 -85 -59Z',P['coat'],width=2)
    shape('M-60 -58Q-20 -42 17 -64Q50 -78 73 -84L66 -62Q16 -12 -47 -42Z',
          'M23 -140Q42 -125 60 -133L73 -103Q58 -75 34 -62Q15 -86 6 -108Z',P['paper'],None)
    shape('M-69 -62Q-48 -33 -57 -14L-90 15Q-107 30 -92 35L-68 30L-25 -4Q-11 -24 -10 -48Z',
          'M23 -70Q34 -51 28 -17L35 -5Q39 7 22 9L8 5L7 -20L3 -59Z',P['coat'])
    if u>.65:
        with c.opacity((u-.65)/.35):paw(c,23,0)
    shape('M31 -73Q58 -71 76 -49L132 -39L161 -49Q179 -54 179 -42Q169 -26 145 -24L76 -24Q38 -26 13 -49Z',
          'M44 -91Q64 -92 77 -119L104 -137Q121 -147 129 -131L120 -114L91 -98Q73 -58 49 -56L30 -69Z',P['coat'])
    paw(c,163-46*u,-38-92*u,-12-8*u)
    with c.transform(76-23*u,-112-38*u,rotation=-11+11*u):head(c,t,'profile')
    shadow=contour_between('M-81 -87Q-74 -58 -20 -54Q4 -56 16 -75L-15 -107Z',
                           'M-83 -106Q-69 -65 -25 -58L-8 -103L-51 -134Z',step)
    c.path(shadow,P['shadow']+'80',None)
    hatch(c,shadow,spacing=7,angle=-38,color=P['ink']+'88',width=.7,seed=19,jitter=.8)
    c.path('M-28 -109L-17 -98L-23 -85L-35 -97Z',P['paper'],None)
    c.path('M-58 -120L-28 -109L-9 -115M-52 -52Q-30 -41 -12 -48',None,'#edbb8c',1)


def fox(c,t,pose='crouch',graphic=False,plant_amount=None):
    if pose=='gather':
        gather(c,t,ramp(5.45,6.15,t));return
    tails(c,t,fan=.68 if pose=='leap' else 1)
    if pose=='leap':
        # Rear limbs attach inside the belly before the main torso overlays them.
        c.path('M-81 -59Q-100 -39 -132 -15L-170 -2Q-184 4 -177 15L-144 17'
               'Q-111 3 -70 -8L-34 -42Z',P['rust'],P['ink'],1.7)
        c.path('M32 -58Q75 -74 115 -94L148 -92Q159 -87 147 -77L119 -77'
               'Q87 -41 50 -24Z',P['rust'],P['ink'],1.7)
        body='M-91 -66Q-102 -107 -39 -122Q16 -139 65 -107L83 -71'
        body+='Q48 -29 8 -33Q-45 -24 -78 -41Z'
        c.path(body,P['coat'],P['ink'],2)
        c.path('M-60 -58Q-20 -42 17 -64Q50 -78 73 -84L66 -62Q16 -12 -47 -42Z',P['paper'],None)
        c.path('M-69 -62Q-48 -33 -57 -14L-90 15Q-107 30 -92 35L-68 30'
               'L-25 -4Q-11 -24 -10 -48Z',P['coat'],P['ink'],1.8)
        c.path('M31 -73Q58 -71 76 -49L132 -39L161 -49Q179 -54 179 -42'
               'Q169 -26 145 -24L76 -24Q38 -26 13 -49Z',P['coat'],P['ink'],1.8)
        paw(c,163,-38,-12)
        with c.transform(76,-112,rotation=-11):head(c,t,'profile')
        shadow='M-81 -87Q-74 -58 -20 -54Q4 -56 16 -75L-15 -107Z'
    else:
        # Grounded 3/4 model, hip/shoulder/neck masses stay connected.
        planted=pose in ('sit','plant')
        c.path('M-72 -59Q-97 -26 -76 -4L-45 0L-24 -41Z',P['rust'],P['ink'],1.7)
        c.path('M44 -55L57 -9L84 -8Q100 1 87 8L52 10Q38 5 32 -30Z',P['rust'],P['ink'],1.7)
        body='M-85 -59Q-111 -105 -63 -135Q-30 -151 12 -128Q26 -160 55 -148'
        body+='Q84 -134 77 -95L59 -65Q33 -43 -8 -38Q-57 -26 -85 -59Z'
        if planted:
            body='M-84 -51Q-111 -99 -61 -139Q-25 -161 12 -131Q24 -161 55 -148Q83 -132 76 -97L60 -57Q48 -27 4 -18Q-60 -1 -84 -51Z'
        c.path(body,P['coat'],P['ink'],2)
        c.path('M23 -140Q42 -125 60 -133L73 -103Q58 -75 34 -62Q15 -86 6 -108Z',P['paper'],None)
        # Far foreleg remains grounded; near foreleg is authored for each action.
        c.path('M23 -70Q34 -51 28 -17L35 -5Q39 7 22 9L8 5L7 -20L3 -59Z',P['coat'],P['ink'],1.7)
        paw(c,23,0)
        if pose in ('catch','catch_profile'):
            u=0 if plant_amount is None else plant_amount
            px=117;py=-130+140*u
            c.path(f'M44 -91Q64 -92 {77+12*u} {-119+80*u}L{px-13} {py-7}'
                   f'Q{px+4} {py-17} {px+12} {py-1}L{px+3} {py+16}'
                   f'L91 {-98+80*u}Q73 -58 49 -56L30 -69Z',P['coat'],P['ink'],1.8)
            paw(c,px,py,-20+20*u)
        elif pose=='plant':
            c.path('M44 -91Q61 -85 63 -50L103 -24L131 -20L126 -1L99 0'
                   'Q56 -11 39 -40L28 -68Z',P['coat'],P['ink'],1.8)
            paw(c,123,-11,-8)
        else:
            c.path('M50 -77Q65 -55 62 -16L73 -6Q85 5 70 10L50 9'
                   'Q40 -12 39 -39L29 -66Z',P['coat'],P['ink'],1.8)
            paw(c,61,1)
        with c.transform(53,-150,rotation=math.sin(t*1.7)*2):
            head(c,t,'front' if planted or pose=='catch' else 'profile',mood='sleep' if pose=='sit' and 10.7<t<12.6 else 'alert')
        shadow='M-83 -106Q-69 -65 -25 -58L-8 -103L-51 -134Z'
    c.path(shadow,P['shadow']+'80',None)
    hatch(c,shadow,spacing=7,angle=-38,color=P['ink']+'88',width=.7,seed=19,jitter=.8)
    c.path('M-28 -109L-17 -98L-23 -85L-35 -97Z',P['paper'],None)
    # Fine shoulder and belly marks retain paper-fold provenance after unfolding.
    c.path('M-58 -120L-28 -109L-9 -115M-52 -52Q-30 -41 -12 -48',None,'#edbb8c',1)


bank=DrawingBank()
bank.add('crane',lambda c,t:crane(c,t),anchors={'feet':(0,0),'beak':(119,-113)})
bank.add('unfold',lambda c,t:crane(c,t,cue(t,(2.3,0),(2.98,1))),anchors={'feet':(0,0),'beak':(119,-113)})
for name in ('crouch','leap','catch','catch_profile','plant','sit'):
    anchor={'crouch':(61,1),'leap':(163,-38),'catch':(117,-130),'catch_profile':(117,-130),'plant':(123,-11),'sit':(61,1)}[name]
    bank.add(name,lambda c,t,p=name:fox(c,t,p),anchors={'feet':(23,0),'paw':anchor})

for i in range(13):
    u=i/12
    bank.add(f'gather{i}',lambda c,t,u=u:gather(c,t,u),
             anchors={'feet':(23,0),'paw':(163-46*u,-38-92*u)})

for i in range(8):
    u=i/7
    bank.add(f'lower{i}',lambda c,t,u=u:fox(c,t,'catch',plant_amount=u),
             anchors={'feet':(23,0),'paw':(117,-130+140*u)})



def connected_smear(c,t):
    # One connected whole-body passage, recognisable snout/ears and dark paws.
    # All parts attach to the same elongated torso; no disembodied hair blobs.
    c.path('M-169 -66C-175 -141 -97 -180 -13 -164L31 -180L34 -151'
           'L60 -185L66 -143L110 -117L154 -105L119 -85L95 -81'
           'Q58 -44 13 -33L-16 -4L-55 5L-42 -29Q-91 -8 -145 -3'
           'L-175 8L-191 -1L-150 -23L-141 -52Z',P['coat'],P['ink'],2)
    c.path('M-169 -66Q-236 -121 -208 -200Q-174 -176 -146 -137Z',P['rust'],P['ink'],1.6)
    c.path('M-208 -200Q-201 -168 -169 -152L-159 -135Q-200 -142 -208 -200Z',P['paper'],None)
    c.path('M40 -111Q77 -112 95 -102L122 -97L97 -83L64 -73Q25 -55 -1 -45L-35 -51Z',P['paper'],None)
    c.path('M70 -119Q84 -126 92 -114Q80 -108 70 -119Z',P['light'],P['ink'],1)
    c.ellipse(84,-117,2.5,4,P['ink'])
    c.path('M143 -110L155 -105L142 -99Z',P['ink'],None)
    c.path('M-111 -140Q-54 -160 8 -143M-132 -124Q-65 -144 -10 -130',None,'#efbc8b',1.5)

bank.add('smear',connected_smear,anchors={'feet':(-40,0),'paw':(97,-80)})


def subject_state(t):
    if t<3.0:return ('crane' if t<2.3 else 'unfold'),424,613,1,cue(t,(0,0),(1.65,0),(1.92,-6),(2.12,2),(2.3,0))
    if t<3.125:return 'crouch',439,613,.72,0
    if t<3.25:return 'crouch',439,613,.72,0
    if t<3.333333333:return 'crouch',443,620,.77,-8
    if t<3.375:return 'smear',466,592,.86,-7
    if t<5.45:
        u=(t-3.375)/(5.75-3.375)
        x=470+200*u
        y=605-310*math.sin(math.pi*u*.76)
        scale=.79+.22*u
        return 'leap',x,y,scale,cue(t,(3.375,-14),(4.3,-20),(5.75,4))
    if t<6.15:
        u=ramp(5.45,6.15,t)
        step=round(u*12);v=step/12
        # Body trajectory is continuous with the flight arc at 5.45 seconds.
        return f'gather{step}',644.74+(738-644.74)*u,335.1+(570-335.1)*u,0.982+0.028*u,3*(1-u)
    if t<6.5:
        return 'catch_profile',cue(t,(6.15,738),(6.5,748)),cue(t,(6.15,570),(6.5,613)),1.01,0
    if t<7.6:return 'catch',748,613,1.01,0
    if t<8.4:return f'lower{min(7,int(ramp(7.6,8.4,t)*8))}',748,613,1.01,0
    return 'sit',748,613,1.01,0


def seed_state(t):
    if t<1.8:return 835+math.sin(t*3)*3,251+math.sin(t*2)*2,1
    if t<5.45:
        u=(t-1.8)/3.95
        return 835+math.sin(u*math.pi)*19,251+63*u+34*u*u,1
    if t<5.75:
        # Reach to the moving target before contact, then keep it on the paw.
        key,x,y,s,r=subject_state(t)
        px,py=bank.anchor(key,'paw',x,y,scale=s,rotation=r)
        u=(t-1.8)/3.95;v=ramp(5.45,5.75,t)
        return (835+math.sin(u*math.pi)*19)*(1-v)+px*v,(251+63*u+34*u*u)*(1-v)+(py-17*s)*v,1
    key,x,y,s,r=subject_state(t)
    if t<8.4:
        px,py=bank.anchor(key,'paw',x,y,scale=s,rotation=r)
        return px,py-17*s,1
    return 866,606,max(0,1-ramp(8.5,9.05,t))


def bloom(c,t):
    u=ramp(8.55,10,t)
    if u<=0:return
    with c.transform(866,606):
        c.path(f'M0 0Q{-11*u} {-40*u} {7*u} {-94*u}',None,'#b8c59a',3)
        leaf(c,0,-29*u,u*.53,-62,'#b2bea0')
        leaf(c,2,-52*u,u*.48,108,'#b9c5a5')
        with c.transform(7*u,-94*u,sx=max(.001,u),rotation=math.sin(t*2)*3):
            c.ellipse(0,0,62,62,'#ffe8a710')
            for i in range(7):
                with c.transform(rotation=i*TAU/7*180/math.pi):
                    c.path('M0 0C-22 -9 -31 -38 -6 -53Q17 -42 0 0Z',P['light'],P['ink'],1.2)
                    c.path('M-4 -9Q-15 -29 -7 -43',None,'#cfb68c',.8)
            c.ellipse(0,0,10,9,'#e3b577',P['ink'],1)
            for i in range(8):
                c.ellipse(math.sin(i*2.4)*6,math.cos(i*2.4)*5,1,1,P['ink'])


def world(c,t):
    a=exposure.time(t)
    f=int(a*24+.001)
    c.roughness=.28
    c.boil_fps=0
    BG(c)
    # Branch stays connected to the seed until the stem tears at 1.8s, visibly before the close-up cut.
    if t<1.8:
        sx,sy,_=seed_state(t)
        c.path(f'M824 211Q823 235 {sx} {sy-12}',None,'#b0b599',1.4)
    elif t<2.3:
        c.path('M824 211Q828 228 831 229',None,'#b0b599',1.4)
    key,x,y,s,r=subject_state(a)
    if key in ('crane','unfold'):
        # Crane lifts its head with its body, then draws the paper wings open.
        bank.draw(c,key,x,y,scale=s,rotation=r,time=a)
    else:
        if key not in ('leap','catch_profile') and not key.startswith('gather'):c.ellipse(x,y+3,98*s,9*s,'#1c354a40')
        bank.draw(c,key,x,y,scale=s,rotation=r,time=a)
    sx,sy,ss=seed_state(a)
    if ss>0:seed(c,sx,sy,t,ss)
    bloom(c,t)
    # Slow independent fireflies are atmosphere; none carry the acting.
    for i in range(7):
        x=105+i*159+math.sin(t*.7+i)*15
        y=378+i%3*63+math.cos(t+i)*12
        c.ellipse(x,y,2,2,'#c5d6ab70')
    # Paper flecks detach from the folding silhouette during metamorphosis.
    if 2.85<t<3.7:
        q=t-2.85
        for i in range(6):
            x=420+math.cos(i*1.3)*q*115
            y=500+math.sin(i*1.3)*q*70-q*35
            with c.transform(x,y,rotation=i*39+q*140):
                c.path('M-4 -2L7 0L0 5Z','#d9c6a1',P['ink'],.7)
    if 3.375<t<3.7:
        speed_lines(c,t,center=(420,530),count=9,radius=(20,190),length=(15,55),
                    angles=(135,225),color='#d0b18d',opacity=.5,width=(.7,1.2),seed=3)
    if t>12.1:
        u=ramp(12.1,14.8,t)
        mx=873-114*u
        my=505-116*math.sin(u*math.pi*.85)
        with c.transform(mx,my,rotation=math.sin(t*4)*10):
            wing=5+abs(math.sin(t*17))*12
            c.path(f'M0 0Q{-wing} -22 {-wing-6} -5Q-9 12 0 0Z',P['light'],P['ink'],.8)
            c.path(f'M0 0Q{wing} -22 {wing+6} -5Q9 12 0 0Z',P['light'],P['ink'],.8)
            c.ellipse(0,0,1.7,7,P['ink'])
            c.path('M0 -6Q-4 -14 -8 -13M0 -6Q4 -14 8 -13',None,P['paper'],.7)
    # Very small moonlit pollen appears only as the flower opens.
    if t>9:
        for i in range(8):
            u=(t-9+i*.21)%2
            c.ellipse(866+math.sin(i*2+u)*26,496-u*32,1.5,1.5,'#f0d7a16a')


def make_shot(start,end,focus,zoom=1,angle=0):
    def paint(c,local):
        t=start+local
        c.stroke_scale=1/zoom
        with c.transform(640,360,rotation=angle,sx=zoom):
            c.translate(-focus[0],-focus[1])
            # Two deliberately different graphic exposures, then ordinary art.
            if 3.125<=t<3.208333333333:
                f=int(t*24+1e-5)
                if f==75:
                    impact_flash(c,t,at=75/24,frames=1,fps=24,background=P['ink'],ink=P['light'],
                                 painter=lambda cv,tt:bank.draw(cv,'crouch',439,613,scale=.72,time=tt))
                else:
                    impact_flash(c,t,at=76/24,frames=1,fps=24,background=P['light'],ink=P['ink'],
                                 painter=lambda cv,tt:bank.draw(cv,'crouch',439,613,scale=.72,time=tt))
            else:world(c,t)
    return Scene(width=W,height=H,duration=end-start,background=P['night'],painter=paint,seed=42)


scene=Storyboard(width=W,height=H,background=P['night'],seed=42)
for spec in [(0,2.3,(640,360),1,0),
             (2.3,3.5,(451,521),2.0,-3),
             (3.5,6.5,(660,403),1.12,0),
             (6.5,8.7,(837,488),2.0,2),
             (8.7,15,(690,442),1.25,0)]:
    scene.add(make_shot(*spec))
scene.metadata={'title':'Paper Moon','description':'A folded crane becomes a five-tailed fox to save and plant a moon-seed. Original vector artwork and directed replacement drawings.'}

# Optional original score is repository-owned; no reference soundtrack is used.
from bamboonimation.audio import AudioClip
_score=Path(__file__).resolve().parents[1]/'assets'/'audio'/'paper_moon.wav'
if _score.is_file():
    scene.audio.append(AudioClip(_score,start=0,volume=.9))
