"""Hierarchical cutout rigs, pose blending, IK and deterministic acting helpers."""
from __future__ import annotations
from dataclasses import dataclass
import math
from .scene import Group,Node
from .animation import mix,easing


def solve_two_bone(length1,length2,target,origin=(0,0),bend=1):
    """Return (upper angle, relative lower angle), in clockwise degrees.

    Coordinates are in the upper bone parent's space. Unreachable targets are
    clamped to the reachable annulus. ``bend=-1`` chooses the opposite elbow.
    No render-time state is retained.
    """
    if not all(math.isfinite(v) and v>0 for v in (length1,length2)):
        raise ValueError('Bone lengths must be positive and finite')
    dx,dy=target[0]-origin[0],target[1]-origin[1]
    if not all(math.isfinite(v) for v in (dx,dy)): raise ValueError('IK target must be finite')
    distance=math.hypot(dx,dy)
    d=max(abs(length1-length2)+1e-9,min(length1+length2-1e-9,distance))
    elbow=math.acos(max(-1,min(1,(d*d-length1*length1-length2*length2)/(2*length1*length2))))
    elbow*=1 if bend>=0 else -1
    shoulder=math.atan2(dy,dx)-math.atan2(length2*math.sin(elbow),length1+length2*math.cos(elbow))
    return math.degrees(shoulder),math.degrees(elbow)

class Bone(Group):
    """A bone extends along local +x; children can start at its tip."""
    _static_properties={'length'}

    def __init__(self,length=100,**kwargs):
        if not math.isfinite(length) or length<=0: raise ValueError('Bone length must be positive and finite')
        super().__init__(**kwargs); self.length=length

    def attach(self,node,at_tip=False):
        if at_tip:
            holder=Group(x=self.length); holder.add(node); self.add(holder)
        else: self.add(node)
        return self

    def tip(self,time=0):
        """Endpoint in the bone's parent's coordinate system."""
        pose=self.pose(time)
        angle=math.radians(pose['rotation'])
        x=(self.length-pose['pivot'][0])*pose['sx']; y=-pose['pivot'][1]*pose['sy']
        return (pose['x']+math.cos(angle)*x-math.sin(angle)*y,
                pose['y']+math.sin(angle)*x+math.cos(angle)*y)

class Rig(Group):
    _static_properties={'bones','poses'}

    def __init__(self,**kwargs):
        super().__init__(**kwargs); self.bones={}; self.poses={}

    def bone(self,name,length,parent=None,x=None,y=0,rotation=0):
        if name in self.bones: raise ValueError(f'Duplicate bone {name!r}')
        if isinstance(parent,str):
            if parent not in self.bones: raise ValueError(f'Unknown parent bone {parent!r}')
            parent=self.bones[parent]
        if parent is not None and parent not in self.bones.values(): raise ValueError('Parent bone must belong to this rig')
        node=Bone(length,name=name,x=parent.length if x is None and parent else (x or 0),y=y,rotation=rotation)
        (parent or self).add(node); self.bones[name]=node
        return node

    def define_pose(self,name,pose):
        """Store ``{bone_name: rotation_degrees | {property: value}}``."""
        clean={}
        for bone,values in pose.items():
            if bone not in self.bones: raise ValueError(f'Unknown bone {bone!r}')
            values={'rotation':values} if isinstance(values,(int,float)) else dict(values)
            for prop in values: self.bones[bone].channel(prop)
            clean[bone]=values
        self.poses[name]=clean
        return self

    def to_pose(self,name,start=0,duration=.3,ease='smooth'):
        if name not in self.poses: raise ValueError(f'Unknown pose {name!r}')
        for bone,props in self.poses[name].items():
            for prop,value in props.items(): self.bones[bone].animate(prop,value,start,duration,ease)
        return self

    def set_pose(self,name,time=0):
        for bone,props in self.poses[name].items(): self.bones[bone].at(time,**props)
        return self

    def ik(self,upper,lower,target,time=0,bend=1):
        """Key a two-bone chain. Target is in upper bone parent's local space."""
        a,b=self.bones[upper],self.bones[lower]
        for bone in (a,b):
            if bone.value('sx',time)!=1 or bone.value('sy',time)!=1 or tuple(bone.value('pivot',time))!=(0,0):
                raise ValueError('IK chain bones require unit scale and zero pivot; scale the enclosing Rig instead')
        if b.parent is not a: raise ValueError('Lower bone must be a direct child of upper bone')
        if abs(b.value('x',time)-a.length)>1e-6 or abs(b.value('y',time))>1e-6:
            raise ValueError('IK lower bone must start at the upper bone tip')
        ra,rb=solve_two_bone(a.length,b.length,target,(a.value('x',time),a.value('y',time)),bend)
        a.at(time,rotation=ra); b.at(time,rotation=rb)
        return self


def blend_poses(a,b,amount):
    """Blend a pair of complete pose dictionaries; rotate by the shortest arc."""
    if not 0<=amount<=1: raise ValueError('Pose blend amount must be between 0 and 1')
    result={}
    for bone in a.keys()|b.keys():
        av=a.get(bone,b.get(bone)); bv=b.get(bone,av)
        av={'rotation':av} if isinstance(av,(float,int)) else av
        bv={'rotation':bv} if isinstance(bv,(float,int)) else bv
        props={}
        for prop in av.keys()|bv.keys():
            va=av.get(prop,bv.get(prop)); vb=bv.get(prop,va)
            if prop=='rotation': vb=va+(vb-va+180)%360-180
            props[prop]=mix(va,vb,amount)
        result[bone]=props
    return result


def blink(time,at,duration=.15):
    """Eyelid closure 0..1 for one blink, with a short closed hold."""
    if duration<=0: raise ValueError('Blink duration must be positive')
    u=(time-at)/duration
    if u<=0 or u>=1: return 0.0
    if u<.4: return easing('smooth')(u/.4)
    if u<.55: return 1.0
    return 1-easing('smooth')((u-.55)/.45)


def spring(time,start=0,frequency=3,damping=5):
    """Analytical 0â†’1 settle; deterministic and independent of output fps."""
    u=max(0,time-start)
    return 1-math.exp(-damping*u)*math.cos(2*math.pi*frequency*u)


def walk_cycle(time,period=.8,stride=30):
    """A reusable gait pose; apply values to your character's named channels."""
    if period<=0: raise ValueError('Walk period must be positive')
    phase=2*math.pi*time/period
    return {'left_leg':math.sin(phase)*stride,'right_leg':-math.sin(phase)*stride,
            'left_arm':-math.sin(phase)*stride*.7,'right_arm':math.sin(phase)*stride*.7,
            'body_y':-abs(math.sin(phase))*stride*.12,'body_rotation':math.sin(phase)*2}

@dataclass(frozen=True)
class MouthCue:
    start: float
    end: float
    shape: str

class LipSync:
    """Time-aligned viseme cues; accepts Rhubarb JSON without external tools.

    A..H/X Rhubarb labels remain unchanged for the artist's drawing bank.
    Uncovered intervals use the resting mouth. Cues are half-open [start,end).
    """
    def __init__(self,cues=(),rest='X'):
        self.rest=rest
        self.cues=sorted([c if isinstance(c,MouthCue) else MouthCue(**c) for c in cues],key=lambda c:c.start)
        previous=0
        for cue in self.cues:
            if not all(math.isfinite(t) for t in (cue.start,cue.end)) or cue.start<0 or cue.end<=cue.start:
                raise ValueError('Mouth cue times must be finite, nonnegative and increasing')
            if cue.start<previous: raise ValueError('Mouth cues must not overlap')
            previous=cue.end

    def __call__(self,time):
        for cue in self.cues:
            if cue.start<=time<cue.end: return cue.shape
            if cue.start>time: break
        return self.rest

    @classmethod
    def from_rhubarb(cls,path,rest='X'):
        import json
        from pathlib import Path
        data=json.loads(Path(path).read_text(encoding='utf-8'))
        return cls([MouthCue(c['start'],c['end'],c['value']) for c in data['mouthCues']],rest)
