from rich.prompt import Prompt,IntPrompt,FloatPrompt
from rich.console import Console
from rich.markup import escape
from rich.progress import track
import numpy as np
import argparse
import shutil
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

OVERLAY_PRESETS = {
    "Full": {
        "track": True,
        "icon": True,
        "distance_time": True,
        "speed": True,
    },
    "Minimal": {
        "track": True,
        "icon": True,
        "distance_time": False,
        "speed": False,
    },
    "None": {
        "track": False,
        "icon": False,
        "distance_time": False,
        "speed": False,
    },
}

OUTPUT_MODE_CHOICES = ["Video", "Timestamped Frames", "Overall Images", "All"]

def parse_args():
    parser = argparse.ArgumentParser(description="GPX video/frame/image renderer")
    parser.add_argument(
        "--debug-shortcut",
        action="store_true",
        help="Use debug defaults, auto-read GPX from debug/, and write outputs into debug/",
    )
    parser.add_argument(
        "--debug-gpx",
        type=str,
        default=None,
        help="GPX path for --debug-shortcut (default: first *.gpx in debug/)",
    )
    parser.add_argument(
        "--debug-output-mode",
        choices=["video", "frames", "overall", "all"],
        default="all",
        help="Output type for --debug-shortcut",
    )
    return parser.parse_args()

def map_debug_output_mode(mode: str) -> str:
    return {
        "video": "Video",
        "frames": "Timestamped Frames",
        "overall": "Overall Images",
        "all": "All",
    }[mode]

def cleanup_debug_outputs():
    paths = [
        Path("debug/output.mp4"),
        Path("debug/frames"),
        Path("debug/overall"),
    ]
    for p in paths:
        if p.is_file():
            p.unlink(missing_ok=True)
        elif p.is_dir():
            shutil.rmtree(p, ignore_errors=True)

def pick_debug_gpx(cli_gpx: str | None) -> str:
    if cli_gpx:
        p = Path(cli_gpx)
        if p.exists() and p.suffix.lower() == ".gpx":
            return str(p)
        raise FileNotFoundError(f"Invalid --debug-gpx: {cli_gpx}")
    candidates = sorted(Path("debug").glob("*.gpx"))
    if not candidates:
        raise FileNotFoundError("No .gpx file found under debug/")
    return str(candidates[0])

def get_debug_defaults(output_mode: str) -> dict:
    if output_mode == "Overall Images":
        return {
            "map_style": 6,
            "zoom": 14,
            "img_w": 1920,
            "img_h": 1080,
            "vid_dur": 6,
            "ctr_mode": {
                "mode_name": "Fixed",
            },
        }
    return {
        "map_style": 7,
        "zoom": 16,
        "img_w": 1280,
        "img_h": 720,
        "vid_dur": 10,
        "ctr_mode": {
            "mode_name": "Follow",
            "cam_box_size": 108,
        },
    }

def ask_overlay_options(debug_shortcut: bool = False):
    if is_debug or debug_shortcut:
        return OVERLAY_PRESETS["Full"]
    preset_idx, preset_name, preset_cnt = user_select(
        choices=["Full", "Minimal", "None", "Custom"],
        default=0,
        prompt="Please select overlay preset",
    )
    if preset_idx + 1 < preset_cnt:
        return OVERLAY_PRESETS[preset_name].copy()
    opts = {}
    for name, key, default in [
        ("Track", "track", True),
        ("GPS Icon", "icon", True),
        ("Distance/Time", "distance_time", True),
        ("Speed", "speed", True),
    ]:
        opts[key] = user_select(
            choices=[f"Enable {name}", f"Disable {name}"],
            default=0 if default else 1,
            prompt=f"Overlay: {name}",
        )[0] == 0
    return opts

def timestamp_tag(dt: datetime) -> str:
    return dt.astimezone(TZ).strftime("%Y%m%d_%H%M%S")

def save_frames(info_list: list[dict], img_w: int, img_h: int, output_dir: Path):
    prepare_dir(output_dir)
    for fi in track(info_list, "Rendering Frames"):
        img = Image.new("RGB", (img_w, img_h))
        render_one_frame(img, **fi)
        tm = fi.get("tm")
        tag = timestamp_tag(tm) if isinstance(tm, datetime) else "frame"
        ms = ""
        if isinstance(tm, datetime):
            ms = f"_{tm.astimezone(TZ).strftime('%f')[:3]}"
        img.save(output_dir / f"{tag}{ms}.png")

def pick_critical_frame_infos(full_frames: list[dict]) -> list[dict]:
    if not full_frames:
        return []
    n = len(full_frames)
    raw_idx = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
    idx = []
    seen = set()
    for i in raw_idx:
        if i not in seen:
            seen.add(i)
            idx.append(i)
    return [full_frames[i] for i in idx]

def save_overall_images(seg, zoom: int, map_style: int, img_w: int, img_h: int, output_dir: Path, overlay_opts: dict):
    prepare_dir(output_dir)
    seg_bounds = seg.get_bounds()
    trk_ctr_lon = (seg_bounds.min_longitude + seg_bounds.max_longitude) / 2
    trk_ctr_lat = (seg_bounds.min_latitude + seg_bounds.max_latitude) / 2
    ctr_px = mtl.tile(trk_ctr_lon, trk_ctr_lat, zoom + TX_EXP)

    traj_lonlat = [(p.longitude, p.latitude) for p in seg.points]
    traj_speed = np.array(smooth_moving_average([mps_to_kmph(seg.get_speed(i)) for i, _ in enumerate(seg.points)]))
    traj_speed = list((traj_speed - 0) / (40 - 0))
    traj = [(p.x, p.y) for p in lonlat2px(traj_lonlat, zoom)]
    traj_disable = [False] * len(traj)
    last_idx = len(seg.points) - 1
    course = 0 if last_idx == 0 else -seg.points[last_idx - 1].course_between(seg.points[last_idx])

    prepare_tiles(set(pave_tiles_preload(img_w, img_h, ctr_px, map_style)))

    for name, idx in [("start", 0), ("middle", len(seg.points) // 2), ("end", len(seg.points) - 1)]:
        point = seg.points[idx]
        img = Image.new("RGB", (img_w, img_h))
        render_one_frame(
            img=img,
            ctr_px=ctr_px,
            tm=point.time,
            map_style=map_style,
            tile_warning=True,
            traj=traj[: idx + 1],
            traj_vals=traj_speed[: idx + 1],
            traj_dis=traj_disable[: idx + 1],
            gps_img=get_gps_no_dir(course),
            speed=mps_to_kmph(seg.get_speed(idx)),
            dist=sum(seg.points[i].distance_2d(seg.points[i - 1]) for i in range(1, idx + 1)) / 1000,
            clock=point.time.astimezone(TZ),
            overlay_opts=overlay_opts,
        )
        img.save(output_dir / f"overall_{name}.png")
    
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
        overlay_opts:dict|None=None,
        ):
    overlay_opts = overlay_opts or OVERLAY_PRESETS["Full"]
    has_traj = traj is not None and len(traj) > 0
    has_traj_vals = traj_vals is not None and len(traj_vals) > 0
    has_traj_dis = traj_dis is not None and len(traj_dis) > 0
    pave_tiles(img,ctr_px,map_style,tile_warning)
    if overlay_opts.get("track", True) and has_traj and has_traj_vals and has_traj_dis:
        overlay_track(img,ctr_px,traj,traj_vals,traj_dis,line_width=15)
    if overlay_opts.get("icon", True) and has_traj and gps_img is not None:
        overlay_icon(img,ctr_px,traj[-1],gps_img)
    if overlay_opts.get("distance_time", True) and dist is not None and clock is not None:
        overlay_dist_time(img,dist,clock)
    if overlay_opts.get("speed", True) and speed is not None:
        overlay_speed(img,speed)

def main():
    args = parse_args()
    debug_shortcut = args.debug_shortcut
    output_mode: str | None = None

    if debug_shortcut:
        output_mode = map_debug_output_mode(args.debug_output_mode)
    elif is_debug:
        output_mode = "Video"
    debug_defaults = get_debug_defaults(output_mode) if (is_debug or debug_shortcut) else None

# ASK gpx file
    if debug_shortcut:
        gpx_file = pick_debug_gpx(args.debug_gpx)
        info(f"Debug shortcut GPX: {gpx_file}")
    elif is_debug:
        gpx_file="debug/20260118_QingShanLake.gpx"
    else:
        while True:
            if enable_GUI:
                console.print(f"[bold magenta]Please select a GPX file in the window[/]")
                gpx_file = filedialog.askopenfilename(
                    title="Select File",
                    filetypes=[("GPX Files", "*.gpx")],
                )
            else:
                gpx_file=Prompt.ask("Please enter the GPX file path")
            gpx_file=gpx_file.strip().strip('"')
            try:
                if Path(gpx_file).suffix.lower() == '.gpx':
                    break
            except Exception:
                pass
            warn(f"File must be a GPX file: '{gpx_file}'")
    
# EXTRACT gpx
    seg = extract_gpx(gpx_file)
    info(f"Successfully extracted {len(seg.points)} track points")

# ASK disable trkpts
    traj_disable=[]
    for p,q in zip(seg.points[:-1],seg.points[1:]):
        if (q.time - p.time).total_seconds() >= track_fail_interval_sec:
            if is_debug or debug_shortcut:
                ret=True
            else:
                prompt=f"Please choose how to handle track from {fmt_tim_rich(p.time)} ~ {fmt_tim_rich(q.time)}"
                ret=bool(user_select(['Show','Hide'],prompt=prompt,default=0)[0])
        else:
            ret=False
        traj_disable.append(ret)
    traj_disable.append(False)

# ASK map_style
    if is_debug or debug_shortcut:
        map_style=debug_defaults["map_style"]
    else:
        map_style=user_select(
            choices=["Satellite Map","Vector Map"],
            default=1,
            prompt="Please select map style",
        )[0]+6

# ASK zoom
    if is_debug or debug_shortcut:
        zoom=debug_defaults["zoom"]
    else:
        zoom=IntPrompt.ask("Please enter map zoom level",choices=[str(i) for i in range(1,19)],default=16)

# ANALYSIS seg
    start_time, end_time = seg.get_time_bounds()
    seg_duration = (end_time - start_time)
    seg_bounds=seg.get_bounds()
    trk_ctr_lon=(seg_bounds.min_longitude+seg_bounds.max_longitude)/2
    trk_ctr_lat=(seg_bounds.min_latitude +seg_bounds.max_latitude )/2
            
# ASK resolution
    if is_debug or debug_shortcut:
        img_w,img_h=debug_defaults["img_w"],debug_defaults["img_h"]
    else:
        vid_res=user_select(
            choices=["1920x1080","1280x720","480x360","Custom"],
            default=0,
            prompt="Please select video resolution",
        )
        if vid_res[0]+1==vid_res[2]:
            img_w=IntPrompt.ask("Please enter video width (pixels)")
            if img_w<=0:
                raise ValueError(f"Invalid video width: {img_w}")
            img_h=IntPrompt.ask("Please enter video height (pixels)")
            if img_h<=0:
                raise ValueError(f"Invalid video height: {img_h}")
        else:
            img_w,img_h=map(lambda x:int(x),vid_res[1].split('x'))

# ASK duration
    if is_debug or debug_shortcut:
        vid_dur=debug_defaults["vid_dur"]
    else:
        vid_dur=FloatPrompt.ask("Please enter video duration (seconds), default 30s",default=30)
    frame_no=max(np.ceil(vid_dur*FPS).astype(np.int64),2)

# ASK output mode
    if output_mode is None:
        output_mode = user_select(
            choices=OUTPUT_MODE_CHOICES,
            default=0,
            prompt="Please select output mode",
        )[1]

# CLEAN debug outputs
    if is_debug or debug_shortcut:
        cleanup_debug_outputs()

# ASK overlay preset/options
    overlay_opts = ask_overlay_options(debug_shortcut=debug_shortcut)

# ASK camera ctr mode
    if is_debug or debug_shortcut:
        ctr_mode=debug_defaults["ctr_mode"].copy()
        if ctr_mode["mode_name"] == "Fixed":
            ctr_mode["pos_lon"] = trk_ctr_lon
            ctr_mode["pos_lat"] = trk_ctr_lat
    else:
        ctr_mode={}
        ctr_mode["mode_name"]=user_select(
            choices=["Follow","Fixed","Switch"],
            default=0,
            prompt="Please select camera movement mode",
        )[1]
        if ctr_mode["mode_name"]=="Follow":
            ctr_mode["cam_box_size"]=IntPrompt.ask("Specify camera cage side length (pixels)",default=int(min(img_w,img_h)*0.15))
        elif ctr_mode["mode_name"]=="Fixed":
            ctr_mode["pos_lon"]=FloatPrompt.ask("Specify camera center longitude (default: track center)",default=trk_ctr_lon)
            ctr_mode["pos_lat"]=FloatPrompt.ask("Specify camera center latitude (default: track center)",default=trk_ctr_lat)
        elif ctr_mode["mode_name"]=="Switch":
            ctr_mode["margin_factor"]=FloatPrompt.ask("Specify frame edge overlap ratio (0.0~0.5)",default=0.4)

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
    traj_speed:list[float] = (traj_speed-0)/(40-0)
    traj_lonlat_np=[np.array(p) for p in traj_lonlat]
    traj_px:list[mtl.Tile]=lonlat2px(traj_lonlat,zoom)
    traj:list[tuple[int,int]]=[(p.x,p.y) for p in traj_px]
    gps_lonlat=[traj_lonlat_np[i]
             if i+1==len(traj_lonlat_np)
             else traj_lonlat_np[i]+(tm-seg.points[i].time)/(seg.points[i+1].time-seg.points[i].time)*(traj_lonlat_np[i+1]-traj_lonlat_np[i])
             for i,tm in zip(idx_list,moments)]
    gps_lonlat:list[tuple[float,float]]=[tuple(p) for p in gps_lonlat]
    gps_px=lonlat2px(gps_lonlat,zoom)
    gps_xy:list[tuple[int,int]]=[(px.x,px.y) for px in gps_px]
    
    if ctr_mode["mode_name"]=="Follow":
        cur_x,cur_y=gps_xy[0]
        ctr_list_px=[]
        tol=ctr_mode["cam_box_size"]//2
        for x,y in gps_xy:
            cur_x=min(max(cur_x,x-tol),x+tol)
            cur_y=min(max(cur_y,y-tol),y+tol)
            ctr_list_px.append(mtl.Tile(cur_x,cur_y,zoom+TX_EXP))
    elif ctr_mode["mode_name"]=="Fixed":
        ctr_list_px=[mtl.tile(ctr_mode["pos_lon"],ctr_mode["pos_lat"],zoom+TX_EXP) for _ in range(frame_no)]
    elif ctr_mode["mode_name"]=="Switch":
        cur_x,cur_y=gps_xy[0]
        half_img_w,half_img_h=img_w//2,img_h//2
        ctr_list_px=[]
        mar=ctr_mode["margin_factor"]
        coe=(1-mar)*2
        for x,y in gps_xy:
            fit_x=min(max(x,cur_x-half_img_w),cur_x+half_img_w)
            fit_y=min(max(y,cur_y-half_img_h),cur_y+half_img_h)
            if fit_x != x or fit_y != y:
                cur_x=int(cur_x*(1-coe)+fit_x*coe)
                cur_y=int(cur_y*(1-coe)+fit_y*coe)
            ctr_list_px.append(mtl.Tile(cur_x,cur_y,zoom+TX_EXP))  

# SUMMARY video info
    lists={
        'ctr_px':ctr_list_px,
        'tm':moments,
        'map_style':[map_style]*frame_no,
        'traj':[traj[:i+1]+[j] for i,j in zip(idx_list,gps_xy)],
        'traj_vals':[traj_speed[:i+1] for i in idx_list],
        'traj_dis':[traj_disable[:i+1] for i in idx_list],
        'gps_img':[get_gps_breathe(i) if traj_disable[p] else get_gps_no_dir(course[p]) for i,p in enumerate(idx_list)],
        'speed':max_every_k_seconds(speed,1/10),
        'dist':dist,
        'clock':[p.astimezone(TZ) for p in moments],
    }
    info_list = [dict(zip(lists.keys(), vals)) for vals in zip(*lists.values())]
    for fi in info_list:
        fi["overlay_opts"] = overlay_opts

# PRELOAD tile info
    tile_needed = []
    for ctr_px in ctr_list_px:
        tile_needed.append(pave_tiles_preload(img_w,img_h,ctr_px,map_style))

# PREVIEW
    if not (is_debug or debug_shortcut):
        frame_id = frame_no//2
        prepare_tiles({p for p in tile_needed[frame_id]})
        info(f"Preview video: {preview_frame_no} frames total")
        preview_img=Image.new("RGB",(img_w,img_h))
        render_one_frame(preview_img,**info_list[frame_id])
        preview_img.show()

# PRELOAD
    prepare_tiles({p for lst in tile_needed for p in lst})
    info("Tiles ready")

# ASK output file
    output_video = None
    output_frames_dir = None
    output_overall_dir = None

    if output_mode in ("Video", "All"):
        if is_debug or debug_shortcut:
            output_video = Path("debug/output.mp4")
        else:
            while True:
                if enable_GUI:
                    console.print(f"[bold magenta]Please specify the output video file in the window[/]")
                    output_file = filedialog.asksaveasfilename(
                        title="Save As",
                        defaultextension=".mp4",
                        filetypes=[("MP4 Files", "*.mp4")],
                    )
                else:
                    output_file=Prompt.ask("Please enter output video file path")
                output_file=output_file.strip().strip('"')
                try:
                    if Path(output_file).suffix.lower() == '.mp4':
                        output_video = Path(output_file)
                        break
                except Exception:
                    pass
                warn(f"File must be an MP4 file: '{output_file}'")

    if output_mode in ("Timestamped Frames", "All"):
        if is_debug or debug_shortcut:
            output_frames_dir = Path("debug/frames")
        else:
            output_frames_dir = Path(Prompt.ask("Please enter output directory for frames", default="frames"))

    if output_mode in ("Overall Images", "All"):
        if is_debug or debug_shortcut:
            output_overall_dir = Path("debug/overall")
        else:
            output_overall_dir = Path(Prompt.ask("Please enter output directory for overall images", default="overall"))

    if output_video is not None:
        writer=VideoWriter(str(output_video),(img_w,img_h))
        for fi in track(info_list,"Rendering Video"):
            img=Image.new("RGB",(img_w,img_h))
            render_one_frame(img,**fi)
            writer.write(np.array(img))
        writer.release()
        start_file(output_video)

    if output_frames_dir is not None:
        realtime_moments = [p.time for p in seg.points]
        filled = []
        j = 0
        for i, tm in enumerate(realtime_moments):
            while j + 1 < len(info_list) and info_list[j + 1]["tm"] <= tm:
                j += 1
            fi = dict(info_list[j])
            fi["tm"] = tm
            fi["clock"] = tm.astimezone(TZ)
            filled.append(fi)
        if debug_shortcut:
            filled = pick_critical_frame_infos(filled)
            info(f"Debug shortcut: exporting {len(filled)} critical frames only")
        save_frames(filled, img_w, img_h, output_frames_dir)
        info(f"Frames saved to: {output_frames_dir.resolve()}")

    if output_overall_dir is not None:
        save_overall_images(seg, zoom, map_style, img_w, img_h, output_overall_dir, overlay_opts)
        info(f"Overall images saved to: {output_overall_dir.resolve()}")

if __name__=='__main__':
    main()
