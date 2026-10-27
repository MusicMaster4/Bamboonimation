"""Bamboonimation — code-first, deterministic 2D cartoon animation."""
from .animation import (Track,Keyframe,EASINGS,mix,easing,cycle,pingpong,cubic_bezier,
                        follow_path,stagger)
from .drawing import Canvas,color,svg_path,morph_path
from .scene import Scene,Node,Group,Path,Ellipse,Rect,Text,Image,Sprite,Camera,Layer
from .rig import (Bone,Rig,solve_two_bone,blend_poses,blink,spring,walk_cycle,LipSync,MouthCue)

__version__='0.1.0'
__all__=['Scene','Node','Group','Path','Ellipse','Rect','Text','Image','Sprite','Camera','Layer',
         'Canvas','color','svg_path','morph_path','Track','Keyframe','EASINGS','mix','easing','cycle','pingpong',
         'cubic_bezier','follow_path','stagger','Bone','Rig','solve_two_bone','blend_poses','blink',
         'spring','walk_cycle','LipSync','MouthCue']

from .procedural import ParticleSystem, Particle, PathMotion, StaticLayer
from .storyboard import Storyboard
from .render import render, frame, save_frame, RenderReport
from .audio import AudioClip, Envelope, viseme

__all__ += ["ParticleSystem", "Particle", "PathMotion", "StaticLayer", "Storyboard",
            "render", "frame", "save_frame", "RenderReport", "AudioClip", "Envelope", "viseme"]

from .acting import ExposureSheet, Exposure, DrawingBank, smear_path, volume_preserving_squash
from .deformation import LatticeWarp, WarpCanvas, warp_path
from .effects import camera_shake, speed_lines, impact_flash, motion_echo, hatch, FollowThrough
__all__ += ["ExposureSheet", "Exposure", "DrawingBank", "smear_path", "volume_preserving_squash",
            "LatticeWarp", "WarpCanvas", "warp_path", "camera_shake", "speed_lines", "impact_flash",
            "motion_echo", "hatch", "FollowThrough"]

from .style import ArtStyle, PAPER, NIGHT, CEL
__all__ += ["ArtStyle", "PAPER", "NIGHT", "CEL"]
