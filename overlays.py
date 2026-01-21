from PIL import Image, ImageDraw, ImageFont
import matplotlib as plt
import numpy as np
from utils import FPS,square_box
from numpy import sin,pi
from mercantile import Tile
from datetime import datetime,timedelta

StrawberryCountBG = Image.open(r"graphics\strawberryCountBG.png")
StrawberryCountBG_w, StrawberryCountBG_h = StrawberryCountBG.size
StrawberryCountBG_resized=StrawberryCountBG.resize((StrawberryCountBG_w//2,StrawberryCountBG_h//2),Image.Resampling.NEAREST)
font_file = r"fonts\Renogare-Regular.otf"
gps_icon = Image.open(r"graphics\gps_icon@2x.png")
gps_icon_rot = [gps_icon.rotate(ang,Image.Resampling.BICUBIC) for ang in range(360)]
gps_no_dir = Image.open(r"graphics\gps_icon@2x_no_dir.png")
gps_breathe = Image.open(r"graphics\gps_breathe.png")
gps_breathe_sec = 3
gps_breathe_len = int( gps_breathe_sec * FPS )
gps_breathe_factor = [(sin(i/gps_breathe_len*2*pi)+1)*0.3+1 for i in range(gps_breathe_len)]
gps_breathe_scale = [gps_breathe.resize((int(gps_breathe.width*k),int(gps_breathe.height*k))) for k in gps_breathe_factor]

def draw_monospaced_text(draw:ImageDraw.ImageDraw,xy:tuple[int,int],text:str,font,space:int|None=None,**options):
    if not space:
        space=0
        for ch in text:
            bbox = draw.textbbox((0, 0), ch, font=font)
            left, top, right, bottom = bbox
            space=max(space,right - left)
    for i,ch in enumerate(text):
        draw.text(
            xy=(xy[0]+i*space,xy[1]),
            text=ch,
            font=font,
            **options
        )

def overlay_dist_time(img:Image.Image,dist:float,time:datetime|timedelta,offset_y:int=50):

    draw=ImageDraw.Draw(img)

    if isinstance(time,timedelta):
        time=(datetime(2000,1,1) + time)
    time_text=time.strftime("%H:%M")

    img.paste(StrawberryCountBG, (0,offset_y),StrawberryCountBG)
    img.paste(StrawberryCountBG_resized, (0,StrawberryCountBG_h+offset_y),StrawberryCountBG_resized)

    text_offset_y=24
    text2_offset_y=12

    draw_monospaced_text(
        draw,
        (StrawberryCountBG_w-55, offset_y+text_offset_y),
        "km",
        ImageFont.truetype(font_file, 24),
        22,
        fill="#d0d0d0",
        stroke_width=2,          
        stroke_fill="black",
        anchor="ms"
    )

    draw_monospaced_text(
        draw,
        (26, offset_y+text_offset_y),
        f"{dist:6.2f}",
        ImageFont.truetype(font_file, 40),
        35,
        fill="white",
        stroke_width=2,          
        stroke_fill="black",
        anchor="ms"
    )

    draw_monospaced_text(
        draw,
        (26, StrawberryCountBG_h+offset_y+text2_offset_y),
        time_text,
        ImageFont.truetype(font_file, 20),
        20,
        fill="#a0a0a0",
        stroke_width=2,          
        stroke_fill="black",
        anchor="ms"
    )

def overlay_speed(img:Image.Image,speed:float,color=None,offset_y:int=140):

    draw=ImageDraw.Draw(img)
    
    if not color:
        color=(lambda x:"white" if x<20 else ("#99FFB9" if x<30 else "#FFEE99"))(speed)

    img.paste(StrawberryCountBG, (0,offset_y),StrawberryCountBG)

    text_offset_y=24

    draw_monospaced_text(
        draw,
        (StrawberryCountBG_w-90, offset_y+text_offset_y),
        "km/h",
        ImageFont.truetype(font_file, 24),
        fill="#d0d0d0",
        stroke_width=2,          
        stroke_fill="black",
        anchor="ms"
    )

    draw_monospaced_text(
        draw,
        (26, offset_y+text_offset_y),
        f"{speed:5.2f}",
        ImageFont.truetype(font_file, 40),
        35,
        fill=color,
        stroke_width=2,          
        stroke_fill="black",
        anchor="ms"
    )

def overlay_track_color(img:Image.Image,ctr_px:Tile,traj:list[tuple[int,int]],colors:list[tuple[int,int,int]],dis:list[bool],line_width:float=9):

    draw=ImageDraw.Draw(img)

    traj = traj + np.array([img.width/2-ctr_px.x,img.height/2-ctr_px.y])
    traj = [tuple(i) for i in traj]

    rad=line_width/2
    for p1,p2,col,d in zip(traj[:-1],traj[1:],colors,dis):
        if not d:
            draw.line([p1,p2],fill=col,width=line_width)
            draw.ellipse(square_box(p1,rad),fill=col)
            draw.ellipse(square_box(p2,rad),fill=col)

def overlay_track(img:Image.Image,ctr_px:Tile,traj:list[tuple[int,int]],vals:list[float],dis:list[bool],cmap:str='viridis',line_width:float=9):
    
    cmap = plt.colormaps[cmap] if isinstance(cmap, str) else cmap
    colors = cmap(vals)    # (N-1, 4)  float 0-1
    colors = (colors[:,:3] * 255).astype(np.uint8)  # 转 0-255 RGB
    colors = [tuple(col) for col in colors]

    overlay_track_color(img,ctr_px,traj,colors,dis,line_width)

def get_gps_icon(ang:float):
    return gps_icon_rot[int(ang)%360]

def get_gps_no_dir(*args,**kwargs):
    return gps_no_dir

def get_gps_breathe(frame_id):
    return gps_breathe_scale[frame_id % gps_breathe_len]

def overlay_icon(img:Image.Image,ctr_px:Tile,pos:tuple[int,int],icon:Image.Image):
    img_w,img_h=img.size
    icon_w,icon_h=icon.size
    img.paste(icon,(pos[0]-ctr_px.x+(img_w-icon_w)//2,pos[1]-ctr_px.y+(img_h-icon_h)//2),icon)

import mercantile as mtl
from utils import TX_EXP
if __name__ == "__main__":
    my_img = Image.new("RGB", (1920, 1080), (255, 0, 255, 255))
    n=21
    points = np.random.multivariate_normal([0, 0], [[200**2, 0], [0, 200**2]], n).astype(np.int32)
    points = [tuple(p) for p in points]
    values = np.random.rand(n-1)
    values = [-1 if i%3==0 else p for i,p in enumerate(values)]
    px=mtl.Tile(0,0,18+TX_EXP)
    overlay_track(my_img,px,points,values,[False for val in values])
    overlay_icon(my_img,px,points[-1],get_gps_breathe(0))
    overlay_dist_time(my_img,20.35345,timedelta(hours=2,minutes=45))
    overlay_speed(my_img,16.42,"#E4D47F")
    overlay_speed(my_img,16.42,"#9EE0B3",200)
    my_img.show()