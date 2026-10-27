"""Decode EVERY reference frame to indexed local contact sheets and motion metrics.

Source and sheets remain under renders/ (gitignored). This does not redistribute
reference artwork or infer drawing exposure from compressed pixel equality.
Usage: python tools/analyze_reference.py renders/reference/video.mp4
"""
from pathlib import Path
import argparse
import json
import hashlib
import subprocess
from fractions import Fraction
import numpy as np
import skia
from bamboonimation.render import ffmpeg_executable


def main():
    p=argparse.ArgumentParser();p.add_argument('video',type=Path);p.add_argument('--title');p.add_argument('--source-url');args=p.parse_args()
    target=args.video.parent/'analysis';target.mkdir(parents=True,exist_ok=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_streams','-of','json',str(args.video)],text=True))['streams'][0]
    fps=Fraction(info['avg_frame_rate']); w,h=320,180
    process=subprocess.Popen([ffmpeg_executable(),'-hide_banner','-loglevel','error','-i',str(args.video),'-map','0:v:0','-vf',f'scale={w}:{h}','-vsync','0','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
    rows=[]; previous=None; count=0; sheet=None; canvas=None
    font=skia.Font(skia.Typeface.MakeFromName('sans-serif',skia.FontStyle()),13)
    pen=skia.Paint(Color=skia.ColorWHITE,AntiAlias=True)
    while True:
        data=process.stdout.read(w*h*3)
        if not data: break
        if len(data)!=w*h*3: raise RuntimeError('Truncated reference frame')
        arr=np.frombuffer(data,np.uint8).reshape(h,w,3)
        diff=np.abs(arr.astype(np.int16)-previous.astype(np.int16)) if previous is not None else np.zeros_like(arr,dtype=np.int16)
        rows.append({'frame':count,'time':float(count/fps),'mean_abs_delta':round(float(diff.mean()),4),
                     'changed_pixel_fraction_gt12':round(float((diff.max(axis=2)>12).mean()),6),
                     'sha256_320x180_rgb':hashlib.sha256(data).hexdigest()})
        page,index=divmod(count,24);col=index%4;row=index//4
        if index==0:
            sheet=skia.Surface(1280,1224);canvas=sheet.getCanvas();canvas.clear(skia.ColorSetRGB(30,30,35))
        rgba=np.empty((h,w,4),np.uint8);rgba[:,:,:3]=arr;rgba[:,:,3]=255
        image=skia.Image.fromarray(rgba,colorType=skia.ColorType.kRGBA_8888_ColorType)
        canvas.drawImage(image,col*w,row*204)
        canvas.drawString(f'f{count:04d}   {float(count/fps):07.3f}s',col*w+8,row*204+197,font,pen)
        previous=arr.copy();count+=1
        if index==23:
            (target/f'sheet-{page:03d}.jpg').write_bytes(bytes(sheet.makeImageSnapshot().encodeToData(skia.kJPEG,91)))
    if count%24:
        (target/f'sheet-{(count-1)//24:03d}.jpg').write_bytes(bytes(sheet.makeImageSnapshot().encodeToData(skia.kJPEG,91)))
    assert process.wait()==0
    assert count==int(info['nb_frames'])
    result={'source':args.source_url or args.video.name,'title':args.title or args.video.stem,
            'fps':str(fps),'frames':count,'width':info['width'],'height':info['height'],
            'source_sha256':hashlib.sha256(args.video.read_bytes()).hexdigest(),
            'analysis':'All decoded frames, source order, zero temporal subsampling; thumbnail320x180,24 frames per sheet. Pixel changes are compression-sensitive and do not prove exposure counts.',
            'frames_per_sheet':24,'sheets':(count+23)//24,'per_frame':rows}
    (target/'frames.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'Analyzed every frame: {count} frames / {fps}fps / {(count+23)//24} sheets. Local only: {target}')


if __name__=='__main__': main()
