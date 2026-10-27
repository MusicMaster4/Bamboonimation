"""Three unrelated worlds, one drawing vocabulary. No downloaded artwork.

    bamboonimation render examples/versatility.py -o renders/versatility.mp4

The jellyfish, spacecraft and ink garden are deliberately different subjects.
All coordinates are logical units; renderer resolution/FPS remain independent.
"""
from __future__ import annotations
import math
import random
from bamboonimation import Scene
from bamboonimation.procedural import ParticleSystem, PathMotion, StaticLayer, spring, overlap
from bamboonimation.storyboard import Storyboard

TAU = math.tau
INK = '#243b49'
_stars = [(random.Random(i*31+9).uniform(0,1280), random.Random(i*53+2).uniform(0,720), random.Random(i).uniform(.7,2.2)) for i in range(95)]
bubbles = ParticleSystem(seed=73, rate=13, origin=(640,780), spread=(620,20),
    velocity=((-14,14),(-120,-75)), lifetime=(5,10), size=(1.5,5), colors=('#d4ead899','#91c8c799'))
flight = PathMotion([(95,440),(350,180),(680,540),(1010,275)])


def seaweed(c, x, y, height, t, fill, lean=0):
    bend=math.sin(t*1.4+x*.02)*15+lean
    c.path(f'M{x} {y} C{x-45} {y-height*.36} {x+bend+50} {y-height*.68} {x+bend} {y-height} '
           f'C{x+bend-20} {y-height*.65} {x+18} {y-height*.3} {x+15} {y} Z',fill,INK,1.6)
    c.path(f'M{x+6} {y} Q{x-14+bend} {y-height*.5} {x+bend} {y-height+15}',None,'#345b60',1)


def jelly(c, x, y, scale, t, phase=0):
    with c.transform(x,y,sx=scale,sy=scale):
        pulse=math.sin(t*3+phase)
        for n in range(9):
            a=(n-4)*17
            length=175+(n%3)*31
            wiggle=22*math.sin(t*2+n*.7)
            c.path(f'M{a} 18 C{a+wiggle} 95 {a-wiggle} 120 {a+wiggle*.7} {length}',None,
                   '#dbb6b3' if n%2 else '#9cbfb7',3 if n%3 else 6)
            c.path(f'M{a+1.7} 18 C{a+wiggle+2} 95 {a-wiggle+2} 120 {a+wiggle*.7+2} {length}',None,'#e2d6ba88',1)
        with c.transform(sx=1+pulse*.045,sy=1-pulse*.045):
            c.path('M-105 17 C-109 -39 -77 -100 -19 -115 C36 -139 109 -65 110 14 '
                   'Q89 39 69 19 Q46 45 20 21 Q0 48 -25 20 Q-52 44 -75 18 Q-91 37 -105 17 Z',
                   '#e6c8ad',INK,2.5)
            c.path('M-96 0 C-85 -72 -12 -126 47 -87 C10 -95 -36 -61 -35 12 Z','#efd8bf',None)
            c.path('M27 -100 Q86 -69 96 9 Q80 24 69 16 C68 -45 47 -78 27 -100 Z','#c49e9a',None)
            c.path('M-72 8 Q-49 -64 -10 -92 M-12 15 Q-20 -30 -10 -92 M48 13 Q34 -50 -10 -92',None,'#ab9194',1.5)
            for px,py in [(-65,-25),(-40,-62),(21,-68),(64,-30),(-14,-31),(29,-18)]:
                c.ellipse(px,py,4,2.8,'#f6e8cb')
            c.path('M-103 16 Q-87 0 -75 18 Q-49 -1 -25 20 Q0 -2 20 21 Q46 -2 69 19 Q88 -2 108 14',None,'#7c6a78',2)


def underwater(c,t):
    c.roughness=.35; c.boil_fps=12
    water_background(c)
    c.path('M0 590 Q160 555 330 604 T680 587 T1000 604 T1280 570 L1280 720 L0 720Z','#274a55',None)
    for x in range(-20,1300,75):
        seaweed(c,x,690,110+(x*13%140),t*.5,'#315e62',18)
    for p in bubbles.sample(t+4):
        c.ellipse(p.x,p.y,p.size,p.size,None,p.color[:7]+f"{round(p.opacity*153):02x}",.9)
    # Tiny fish use the same generic path/transform vocabulary as large subjects.
    for n in range(9):
        x=(n*121+t*(24+n%3*5))%1450-80
        y=160+n%3*71+math.sin(t+n)*11
        with c.transform(x,y,sx=.55,sy=.55):
            c.path('M-24 0 Q0 -16 24 0 Q0 15 -24 0 L-36 12 L-34 -12Z','#9fbfb1',None)
            c.ellipse(12,-1,1.6,1.6,INK)
    jelly(c,915,174,.48,t,1)
    jelly(c,313,224,.61,t,2.4)
    jelly(c,671+math.sin(t*.8)*22,265+math.sin(t*1.2)*14,1.12,t)
    # Foreground plants establish a third depth plane.
    c.path('M0 671 Q252 632 434 683 Q718 638 909 678 Q1100 644 1280 668 L1280 720L0 720Z','#193845',None)
    for x,h in [(0,270),(82,215),(1180,290),(1255,238)]:
        seaweed(c,x,754,h,t,'#1c414b',-15)
    for n in range(16):
        x=(n*113+83)%1280
        c.ellipse(x,695+(n*7%20),8+n%4*3,3+n%3,'#476467')
    water_paper(c)


def spacecraft(c,x,y,angle,t):
    with c.transform(x,y,rotation=angle*.4,sx=1.05):
        # Engine flame is analytic, including secondary tip flicker.
        flame=56+math.sin(t*30)*8
        c.path(f'M-74 -15 Q{-95-flame*.4} -29 {-90-flame} 0 Q{-100-flame*.3} 24 -74 15Z','#d99473',None)
        c.path(f'M-77 -8 Q-107 -14 {-90-flame*.6} 0 Q-103 14 -77 8Z','#f1d2a0',None)
        c.path('M-47 -21 L-71 -49 L-100 -45 L-82 -4 L-97 32 L-68 37 L-42 16Z','#b46d68',INK,2.7)
        c.path('M-75 -22 Q-12 -74 66 -24 L99 0 Q75 44 -4 44 Q-62 41 -75 19Z','#d6c8ad',INK,2.8)
        c.path('M-65 22 Q13 62 85 10 Q34 43 -65 11Z','#a69c93',None)
        c.path('M-9 -44 Q6 -86 42 -69 Q67 -56 61 -27Z','#b3c5be',INK,2.4)
        c.path('M-1 -46 Q11 -74 35 -64 Q20 -66 13 -38Z','#ecdfbd',None)
        # A tiny passenger remains original vector artwork.
        c.ellipse(27,-51,12,15,'#ddaa88',INK,1.4)
        c.path('M15 -54 Q12 -72 29 -68 Q42 -66 41 -53 Q31 -59 21 -51Z','#414852',None)
        c.ellipse(32,-51,1.8,2.5,INK)
        c.path('M-33 -32 L-10 -26 M-31 -29 L-19 25 M69 -20 L71 16',None,'#6d6b71',1.6)
        c.ellipse(35,9,16,15,'#386874',INK,2)
        c.ellipse(31,5,6,8,'#c7d8c7',None)
        for px in (-43,-15,13,70):
            c.ellipse(px,27,1.5,1.5,INK)
        c.path('M-39 25 L-59 63 L-24 61 L7 32Z','#b66f66',INK,2.3)
        c.path('M-53 53 L-28 54',None,'#e3b38b',2)


def space(c,t):
    c.roughness=.35; c.boil_fps=12
    space_background(c)
    for i,(x,y,r) in enumerate(_stars):
        alpha=.55+.35*math.sin(t*.7+i)
        c.ellipse(x,y,r,r,f'#ede1bd{round(alpha*255):02x}')
    # Large gas giant; an elliptical ring is drawn behind and then in front.
    with c.transform(967,227,rotation=-21):
        c.ellipse(0,0,260,49,None,'#bf9b84',21)
        c.ellipse(0,0,260,49,None,'#ead2a7',7)
        c.ellipse(0,0,137,137,'#c9ac91',INK,2.5)
        sphere='M-137 0 A137 137 0 1 0 137 0 A137 137 0 1 0 -137 0Z'
        with c.clip(sphere):
            for n in range(8):
                y=-140+n*37
                c.path(f'M-150 {y} Q-40 {y+39} 150 {y+9}',None,'#ac8d86',15 if n%2 else 8)
            c.ellipse(77,8,92,150,'#5e53613b')
        c.path('M-260 0 C-254 63 236 67 260 0',None,'#c6a38e',22)
        c.path('M-260 0 C-254 63 236 67 260 0',None,'#edd0a2',6)
    # Near moon in lower edge, with shallow craters and a settlement.
    c.path('M-35 715 Q202 429 640 625 Q861 740 1310 660L1310 760L-35 760Z','#8d8592',INK,3)
    c.path('M-35 732 Q206 482 618 659 L602 740Z','#a99a9d',None)
    for x,y,rx,ry in [(135,638,45,11),(382,615,29,7),(566,697,56,12),(960,705,72,7)]:
        c.ellipse(x,y,rx,ry,'#706e81',None)
        c.path(f'M{x-rx} {y} Q{x} {y-ry*2} {x+rx} {y}',None,'#c1abab',2)
    for x,y,s in [(240,568,.9),(308,575,.65)]:
        with c.transform(x,y,sx=s):
            c.path('M-33 30L-28 -10Q0 -49 29 -10L34 30Z','#d3bda4',INK,2)
            c.ellipse(0,-4,15,14,'#465b72',INK,2)
            c.line([(-40,32),(40,32)],INK,3)
            c.line([(21,-31),(27,-61)],INK,2)
            c.ellipse(28,-65,4,4,'#df9b80')
    p=flight.sample(min(1,t/4.4))
    spacecraft(c,*p,t)
    # Staggered meteor shards are continuous positions, not simulation state.
    for n in range(3):
        x=(t*72+n*195)%1420-80
        y=90+n*120
        c.line([(x-37,y-14),(x,y)],'#a49b9950',3)
        c.ellipse(x,y,4,2,'#dfb89e')
    space_paper(c)


def leaf(c,x,y,scale,rotation,fill):
    if scale<=.001:
        return
    with c.transform(x,y,rotation=rotation,sx=scale):
        c.path('M0 0 C-55 -4 -69 -66 -19 -89 Q-13 -31 0 0Z',fill,INK,1.7)
        c.path('M0 0 Q-32 -29 -20 -77 M-14 -21L-45 -35 M-21 -43L-40 -57',None,'#45615b',1)


def garden(c,t):
    c.roughness=.35; c.boil_fps=12
    garden_background(c)
    # Printed-book style background hatching and distant hanging vines.
    c.ellipse(656,594,338,57,'#bebca255')
    for n in range(20):
        x=23+n*67
        c.path(f'M{x} 0 Q{x+50} 40 {x+9} {70+n%4*25}',None,'#8f9d7a44',1.2)
        leaf(c,x+13,65+n%4*25,.35,165+n%3*20,'#afba9855')
    # Central stem gradually grows using a sampled Bézier (no raster asset).
    grow=min(1,max(0,t/2.8))
    path=PathMotion([(620,623),(535,460),(781,334),(661,178)])
    points=[path.sample(grow*i/70)[:2] for i in range(71)]
    c.line(points,'#607c68',16)
    c.line([(x-2,y) for x,y in points],'#8ca083',5)
    for n in range(7):
        p=(n+1)/9
        x,y,a=path.sample(p)
        s=min(1,max(0,(grow-p)*7))
        side=-1 if n%2 else 1
        leaf(c,x,y,s*.9,side*59+(0 if side<0 else 135),'#769079' if n%2 else '#a4ad82')
    # Ink creature rides the growing blossom: wide nose, long neck, soft ears.
    px,py,_=path.sample(grow)
    bloom=spring(max(0,t-2.1),frequency=1.6,damping=.52)
    with c.transform(px,py-20,sx=max(.02,bloom),sy=max(.02,bloom)):
        for n in range(8):
            with c.transform(rotation=n*45+t*4):
                c.path('M0 5 C-47 -11 -52 -57 -9 -68 C19 -72 30 -33 0 5Z','#cb8e7d',INK,1.9)
                c.path('M-5 -15Q-21 -31 -12 -54',None,'#edc5a1',1.2)
        c.ellipse(0,-5,27,24,'#dfb47c',INK,2)
        for n in range(12):
            a=n*TAU/12
            c.ellipse(math.cos(a)*16,-5+math.sin(a)*13,1.5,2,INK)
    # A whimsical original bird is articulated from independent paths.
    bx=360
    by=496-4*math.sin(t*2)
    # Breathing changes the knees, while both toes retain ground registration.
    foot=578-by
    with c.transform(bx,by):
        c.line([(-16,42),(-23,foot-9),(-20,foot),(-37,foot)],INK,3)
        c.line([(16,42),(27,foot-9),(24,foot),(43,foot)],INK,3)
        c.path('M-41 10 Q-105 -9 -108 -66 Q-54 -56 -40 -21Z','#4c6262',INK,2)
        c.path('M-41 10 Q-78 -3 -92 -43',None,'#92a18d',2)
        c.path('M-48 12 C-79 -24 -38 -61 -7 -58 Q0 -130 37 -142 '
               'Q85 -151 87 -108 Q83 -69 48 -68 Q71 -11 35 31 Q-13 66 -48 12Z','#4d6667',INK,2.5)
        c.path('M-22 -21 Q28 -51 48 -23 Q33 25 -12 26 Q-41 19 -22 -21Z','#a4b19a',INK,1.6)
        c.path('M-8 -6 Q13 -21 33 -18 M-4 8Q15 -5 27 -3',None,'#6c8377',1)
        c.path('M76 -111 L127 -97 L80 -88Z','#c9a374',INK,2)
        c.ellipse(54,-111,12,17,'#eee1bc',INK,1.3)
        c.ellipse(59,-108-5*min(1,max(0,t-2.1)),4,7,INK)
        c.ellipse(61,-111,1.3,2,'#ffffff')
        c.path('M34 -139Q24 -166 38 -171M48 -143Q51 -169 65 -169',None,INK,2)
    # Falling seeds, a branch and small leaves tie the foreground together.
    for n in range(11):
        x=810+n*21+math.sin(n+t)*20
        y=(t*36+n*71)%610
        with c.transform(x,y,rotation=n*37+t*24):
            c.ellipse(0,0,3,6,'#a17d63')
            c.path('M0 -4Q-14 -31 -23 -19M0 -4Q14 -31 23 -19',None,'#7a8b72',1)
    c.path('M-10 720 Q242 603 451 694 Q839 625 1290 683 L1290 730Z','#788c71',INK,2)
    for x in (50,147,953,1120,1230):
        leaf(c,x,727,.8,-18+x%100,'#acb58c')
    garden_paper(c)



def _water_background(c):
    c.gradient_rect(0,0,1280,720,['#2c5561','#152e43'])
    for x,w in [(180,170),(590,90),(1020,190)]:
        c.polygon([(x,-20),(x+w,-20),(x+w+250,720),(x-130,720)],'#bcdcc50a')


def _grain(c,amount,seed):
    c.paper(amount,seed=seed)


water_background=StaticLayer(_water_background)
space_background=StaticLayer(lambda c:c.gradient_rect(0,0,1280,720,['#1d2945','#59425e']))
garden_background=StaticLayer(lambda c:c.gradient_rect(0,0,1280,720,['#e5d8bd','#f0e1c1']))
water_paper=StaticLayer(lambda c:_grain(c,.11,77))
space_paper=StaticLayer(lambda c:_grain(c,.10,12))
garden_paper=StaticLayer(lambda c:_grain(c,.14,19))


def make_scene():
    board=Storyboard()
    board.add(Scene(duration=4.4,painter=underwater,seed=77))
    board.add(Scene(duration=4.4,painter=space,seed=12),transition='dissolve',overlap=.4)
    board.add(Scene(duration=7.0,painter=garden,seed=19),transition='iris',overlap=.4)
    board.metadata={'title':'Worlds in a sketchbook','description':'Underwater, space and botanical ink illustration; entirely procedural original artwork.'}
    return board

scene=make_scene()
