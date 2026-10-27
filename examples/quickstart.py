"""A complete agent-friendly scene in a few lines: a character notices a moth."""
import math
from bamboonimation import Scene
from bamboonimation.cartoon import grain
from bamboonimation.cartoon import Actor, room

actor=Actor()

def draw(c,t):
    room(c)
    x=670+90*math.sin(t)
    y=280+30*math.cos(t*2)
    actor.draw(c,560,670,t,scale=1.2,pose='think',expression='curious',look=((x-560)/40,-3))
    c.ellipse(x,y,3,6,'#493f4a')
    c.ellipse(x-7,y-2,7,3+4*abs(math.sin(t*20)),'#fff1cf','#493f4a',1)
    c.ellipse(x+7,y-2,7,3+4*abs(math.sin(t*20)),'#fff1cf','#493f4a',1)
    grain(c,amount=.12)

scene=Scene(duration=10,painter=draw)
