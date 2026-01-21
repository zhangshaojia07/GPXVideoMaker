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
    pave_tiles(img,ctr_px,map_style)
    overlay_track(img,ctr_px,traj,traj_vals,traj_dis,line_width=15)
    overlay_icon(img,ctr_px,ctr_px,gps_img)
    overlay_dist_time(img,dist,clock)
    overlay_speed(img,speed)

def main():
    if is_debug:
        gpx_file=r"debug\20260118_QingShanLake.gpx"
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
    seg = extract_gpx(gpx_file)
    info(f"成功提取 {len(seg.points)} 个轨迹点")

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

    if is_debug:
        map_style=7
    else:
        map_style=user_select(
            choices=["卫星地图","矢量地图"],
            default=1,
            prompt="请选择地图样式",
        )[0]+6

    if is_debug:
        zoom=16
    else:
        zoom=IntPrompt.ask("请输入地图缩放级别（zoom）",choices=[str(i) for i in range(1,19)],default=16)
    
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

    if is_debug:
        vid_dur=10
    else:
        vid_dur=FloatPrompt.ask("请输入视频时长（秒） 默认 30s",default=30)
    frame_no=np.ceil(vid_dur*FPS).astype(np.int64)

    if is_debug:
        output_file=r"debug\output.mp4"
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

    start_time, end_time = seg.get_time_bounds()
    duration = (end_time - start_time)
    frame_duration = duration / (frame_no-1)

    moments = [start_time + frame_duration * i for i in range(frame_no)]
    moments[-1] = end_time

    dist=[]
    dist_cur = 0
    idx_list = []
    idx_cur = 0
    for p in moments:
        while idx_cur < len(seg.points) - 1 and seg.points[idx_cur+1].time <= p:
            dist_cur += seg.points[idx_cur+1].distance_2d(seg.points[idx_cur])
            idx_cur += 1
        idx_list.append(idx_cur)
        dist.append(dist_cur / 1000)

    course=[0]+[-i.course_between(j) for i,j in zip(seg.points[:-1],seg.points[1:])]
    # course=smooth_moving_average_angle(course)

    speed=[mps_to_kmph(seg.get_speed(i)) for i in idx_list]
    traj_px=[mtl.tile(p.longitude,p.latitude,zoom+TX_EXP) for p in seg.points]
    traj=[(p.x,p.y) for p in traj_px]
    traj_speed=np.array(smooth_moving_average([mps_to_kmph(seg.get_speed(i)) for i,p in enumerate(seg.points)]))
    traj_speed=traj_speed/traj_speed.max()

    traj2=[np.array(p) for p in traj]
    gps_pos=[traj2[i]
             if i+1==len(traj2)
             else traj2[i]+(tm-seg.points[i].time)/(seg.points[i+1].time-seg.points[i].time)*(traj2[i+1]-traj2[i])
             for i,tm in zip(idx_list,moments)]
    ctr_pxs=[mtl.Tile(int(np.round(x)),int(np.round(y)),zoom+TX_EXP) for x,y in gps_pos]

    for ctr_px in ctr_pxs:
        pave_tiles_preload(img_w,img_h,ctr_px,map_style)
    prepare_tiles()
    info(f"瓦片准备完毕")

    lists={
        'ctr_px':ctr_pxs,
        'tm':moments,
        'map_style':[map_style]*frame_no,
        'traj':[traj[:i+1]+[j] for i,j in zip(idx_list,gps_pos)],
        'traj_vals':[traj_speed[:i+1] for i in idx_list],
        'traj_dis':[traj_disable[:i+1] for i in idx_list],
        'gps_img':[get_gps_breathe(i) if traj_disable[p] else get_gps_no_dir(course[p]) for i,p in enumerate(idx_list)],
        'speed':max_every_k_seconds(speed,1/10),
        'dist':dist,
        'clock':[p.astimezone(TZ) for p in moments],
    }
    info_list = [dict(zip(lists.keys(), vals)) for vals in zip(*lists.values())]

    writer=VideoWriter(output_file,(img_w,img_h))
    for fi in track(info_list,"渲染中"):
        img=Image.new("RGB",(img_w,img_h))
        render_one_frame(img,**fi)
        writer.write(np.array(img))
    writer.release()

if __name__=='__main__':
    main()