from rich.prompt import Prompt,IntPrompt,FloatPrompt
from rich.console import Console
from rich.markup import escape
from rich.progress import track
import numpy as np
from utils import *
from gpx_handler import extract_gpx
from tkinter import filedialog
from video_writer import VideoWriter
from PIL import Image
from pave_tiles import pave_tiles,pave_tiles_preload,prepare_tiles
from overlays import *
import mercantile as mtl
from datetime import datetime
from pathlib import Path

from rich import print,inspect

console=Console(highlighter=None)
    
def render_one_frame(
        img:Image.Image,
		ctr_px:mtl.Tile,
		tm:datetime|None=None,
        # tiles
		map_style:int|None=None,
        tile_warning:bool=True,
        # track & icon
        traj:list[tuple[int,int]]|None=None,
        traj_vals:list[float]|None=None,
        traj_dis:list[bool]|None=None,
		gps_img:Image.Image|None=None,
        # widgets
		speed:float|None=None,
		dist:float|None=None,
        clock:str|None=None,
        ):
    pave_tiles(img,ctr_px,map_style,tile_warning)
    overlay_track(img,ctr_px,traj,traj_vals,traj_dis,line_width=15)
    overlay_icon(img,ctr_px,traj[-1],gps_img)
    overlay_dist_time(img,dist,clock)
    overlay_speed(img,speed)

def main():

# ASK gpx file
    if is_debug:
        gpx_file="debug/20260118_QingShanLake.gpx"
    else:
        while True:
            if GUI_file_selection:
                console.print(f"[bold magenta]请在窗口中选择 GPX 文件[/]")
                gpx_file = filedialog.askopenfilename(
                    title="选择文件",
                    filetypes=[("GPX 文件", "*.gpx")],
                )
            else:
                gpx_file=Prompt.ask("请输入 GPX 文件路径")
            gpx_file=gpx_file.strip().strip('"')
            try:
                if Path(gpx_file).suffix.lower() == '.gpx':
                    break
            except Exception:
                pass
            warn(f"文件必须为 GPX 文件: '{gpx_file}'")
    
# EXTRACT gpx
    seg = extract_gpx(gpx_file)
    info(f"成功提取 {len(seg.points)} 个轨迹点")

# ASK disable trkpts
    traj_disable=[]
    for p,q in zip(seg.points[:-1],seg.points[1:]):
        if (q.time - p.time).total_seconds() >= track_fail_interval_sec:
            if is_debug:
                ret=True
            else:
                prompt=f"请选择 {fmt_tim_rich(p.time)} ~ {fmt_tim_rich(q.time)} 轨迹处理方式"
                ret=bool(user_select(['显示','不显示'],prompt=prompt,default=0)[0])
        else:
            ret=False
        traj_disable.append(ret)
    traj_disable.append(False)

# ASK map_style
    if is_debug:
        map_style=7
    else:
        map_style=user_select(
            choices=["卫星地图","矢量地图"],
            default=1,
            prompt="请选择地图样式",
        )[0]+6

# ASK zoom
    if is_debug:
        zoom=16
    else:
        zoom=IntPrompt.ask("请输入地图缩放级别（zoom）",choices=[str(i) for i in range(1,19)],default=16)

# ANALYSIS seg
    start_time, end_time = seg.get_time_bounds()
    seg_duration = (end_time - start_time)
    seg_bounds=seg.get_bounds()
    trk_ctr_lon=(seg_bounds.min_longitude+seg_bounds.max_longitude)/2
    trk_ctr_lat=(seg_bounds.min_latitude +seg_bounds.max_latitude )/2

# ASK camera ctr mode
    if is_debug:
        ctr_mode={
            'mode_name':'跟随',
        }
    else:
        ctr_mode={}
        ctr_mode["mode_name"]=user_select(
            choices=["跟随","固定","切换"],
            default=0,
            prompt="请选择摄像机运动模式",
        )[1]
        if ctr_mode["mode_name"]=="跟随":
            pass
        elif ctr_mode["mode_name"]=="固定":
            ctr_mode["pos_lon"]=FloatPrompt.ask("指定摄像机中心经度（默认轨迹中心）",default=trk_ctr_lon)
            ctr_mode["pos_lat"]=FloatPrompt.ask("指定摄像机中心纬度（默认轨迹中心）",default=trk_ctr_lat)
        elif ctr_mode["mode_name"]=="切换":
            pass
            
# ASK resolution
    if is_debug:
        img_w,img_h=1280,720
    else:
        vid_res=user_select(
            choices=["1920x1080","1280x720","480x360","自定义"],
            default=0,
            prompt="请选择视频分辨率",
        )
        if vid_res[0]+1==vid_res[2]:
            img_w=IntPrompt.ask("请输入视频宽度（像素）")
            if img_w<=0:
                raise ValueError(f"Invalid video width: {img_w}")
            img_h=IntPrompt.ask("请输入视频高度（像素）")
            if img_h<=0:
                raise ValueError(f"Invalid video height: {img_h}")
        else:
            img_w,img_h=map(lambda x:int(x),vid_res[1].split('x'))

# ASK duration
    if is_debug:
        vid_dur=10
    else:
        vid_dur=FloatPrompt.ask("请输入视频时长（秒） 默认 30s",default=30)
    frame_no=np.ceil(vid_dur*FPS).astype(np.int64)

# PROCESS video info
    frame_duration = seg_duration / (frame_no-1)

    moments = [start_time + frame_duration * i for i in range(frame_no)]
    moments[-1] = end_time

    dist:list[float] = []
    dist_cur = 0
    idx_list:list[int] = []
    idx_cur = 0
    for p in moments:
        while idx_cur < len(seg.points) - 1 and seg.points[idx_cur+1].time <= p:
            dist_cur += seg.points[idx_cur+1].distance_2d(seg.points[idx_cur])
            idx_cur += 1
        idx_list.append(idx_cur)
        dist.append(dist_cur / 1000)

    course:list[float] = [0]+[-i.course_between(j) for i,j in zip(seg.points[:-1],seg.points[1:])]
    # course=smooth_moving_average_angle(course)

    speed:list[float] = [mps_to_kmph(seg.get_speed(i)) for i in idx_list]
    traj_lonlat:list[tuple[float,float]] = [(p.longitude,p.latitude) for p in seg.points]
    traj_speed = np.array(smooth_moving_average([mps_to_kmph(seg.get_speed(i)) for i,p in enumerate(seg.points)]))
    traj_speed:list[float] = traj_speed/traj_speed.max()
    traj_lonlat_np=[np.array(p) for p in traj_lonlat]
    gps_lonlat=[traj_lonlat_np[i]
             if i+1==len(traj_lonlat_np)
             else traj_lonlat_np[i]+(tm-seg.points[i].time)/(seg.points[i+1].time-seg.points[i].time)*(traj_lonlat_np[i+1]-traj_lonlat_np[i])
             for i,tm in zip(idx_list,moments)]
    gps_lonlat:list[tuple[float,float]]=[tuple(p) for p in gps_lonlat]
    
    if ctr_mode["mode_name"]=="跟随":
        ctr_list_pos=gps_lonlat
    elif ctr_mode["mode_name"]=="固定":
        ctr_list_pos=[(ctr_mode["pos_lon"],ctr_mode["pos_lat"])] * frame_no
    elif ctr_mode["mode_name"]=="切换":
        pass
    ctr_list_px=lonlat2px(ctr_list_pos,zoom)
    traj_px:list[mtl.Tile]=lonlat2px(traj_lonlat,zoom)
    traj:list[tuple[int,int]]=[(p.x,p.y) for p in traj_px]
    gps_list:list[tuple[int,int]]=[(px.x,px.y) for px in lonlat2px(gps_lonlat,zoom)]

# SUMMARY video info
    lists={
        'ctr_px':ctr_list_px,
        'tm':moments,
        'map_style':[map_style]*frame_no,
        'traj':[traj[:i+1]+[j] for i,j in zip(idx_list,gps_list)],
        'traj_vals':[traj_speed[:i+1] for i in idx_list],
        'traj_dis':[traj_disable[:i+1] for i in idx_list],
        'gps_img':[get_gps_breathe(i) if traj_disable[p] else get_gps_no_dir(course[p]) for i,p in enumerate(idx_list)],
        'speed':max_every_k_seconds(speed,1/10),
        'dist':dist,
        'clock':[p.astimezone(TZ) for p in moments],
    }
    info_list = [dict(zip(lists.keys(), vals)) for vals in zip(*lists.values())]

# PRELOAD tile info
    tile_needed = []
    for ctr_px in ctr_list_px:
        tile_needed.append(pave_tiles_preload(img_w,img_h,ctr_px,map_style))

# PREVIEW
    if not is_debug:
        frame_id = frame_no//2
        prepare_tiles({p for p in tile_needed[frame_id]})
        info(f"预览视频：共 {preview_frame_no} 帧")
        preview_img=Image.new("RGB",(img_w,img_h))
        render_one_frame(preview_img,**info_list[frame_id])
        preview_img.show()

# PRELOAD
    prepare_tiles({p for lst in tile_needed for p in lst})
    info("瓦片准备完毕")

# ASK output file
    if is_debug:
        output_file="debug/output.mp4"
    else:
        while True:
            if GUI_file_selection:
                console.print(f"[bold magenta]请在窗口中指定导出视频文件[/]")
                output_file = filedialog.asksaveasfilename(
                    title="保存为",
                    defaultextension=".mp4",
                    filetypes=[("MP4 文件", "*.mp4")],
                )
            else:
                output_file=Prompt.ask("请输入导出视频文件路径")
            output_file=output_file.strip().strip('"')
            try:
                if Path(output_file).suffix.lower() == '.mp4':
                    break
            except Exception:
                pass
            warn(f"文件必须为 MP4 文件: '{output_file}'")

# RENDER
    writer=VideoWriter(output_file,(img_w,img_h))
    for fi in track(info_list,"渲染中"):
        img=Image.new("RGB",(img_w,img_h))
        render_one_frame(img,**fi)
        writer.write(np.array(img))
    writer.release()

# PLAY video
    start_file(output_file)

if __name__=='__main__':
    main()