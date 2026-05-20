from pathlib import Path
import pytz
from rich.prompt import IntPrompt
from rich.console import Console
from rich.markup import escape
import numpy as np
from datetime import datetime,timedelta
import os
import platform
import subprocess
import json
import mercantile as mtl

console=Console(highlight=None)

def info(text="Tip: waiting is part of smooth rendering"):
    console.print(f"[italic blue]{escape(text)}[/]")

def warn(text="Warning: please check your input"):
    console.print(f"[italic red]{escape(text)}[/]")

SETTINGS_FILE = Path("settings.json")
DEFAULT_SETTINGS = {
    "is_debug": False,
    "enable_GUI": True,
    "is_convert_wgs_to_gcj": True,
    "TZ_name": "Asia/Shanghai",
    "default_map": {
        "video_frames": {
            "style": "satellite",
            "zoom": 16,
        },
        "overall": {
            "style": "vector",
            "zoom": 14,
        },
    },
    "FPS": 30,
    "track_fail_interval_sec": 3 * 60,
    "preview_frame_no": 1,
}

TX_EXP = 8

def load_settings() -> dict:
    settings = DEFAULT_SETTINGS.copy()
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8-sig") as f:
            user_settings = json.load(f)
        if isinstance(user_settings, dict):
            settings.update(user_settings)
    else:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    return settings

SETTINGS = load_settings()

is_debug = bool(SETTINGS["is_debug"])
enable_GUI = bool(SETTINGS["enable_GUI"])
is_convert_wgs_to_gcj = bool(SETTINGS["is_convert_wgs_to_gcj"])
TZ_name = str(SETTINGS["TZ_name"])
TZ = pytz.timezone(TZ_name)
FPS = int(SETTINGS["FPS"])
track_fail_interval_sec = int(SETTINGS["track_fail_interval_sec"])
preview_frame_no = int(SETTINGS["preview_frame_no"])

def normalize_map_style(style_value, fallback: int) -> int:
    if isinstance(style_value, int):
        return style_value if style_value in (6, 7) else fallback
    style = str(style_value).strip().lower()
    if style in ("satellite", "sat", "s"):
        return 6
    if style in ("vector", "vec", "v"):
        return 7
    return fallback

def normalize_zoom(zoom_value, fallback: int) -> int:
    try:
        zoom = int(zoom_value)
    except (TypeError, ValueError):
        return fallback
    return min(max(zoom, 1), 18)

_default_map = SETTINGS.get("default_map", {})
_video_frames_map = _default_map.get("video_frames", {})
_overall_map = _default_map.get("overall", {})

DEFAULT_MAP_STYLE_VIDEO_FRAMES = normalize_map_style(_video_frames_map.get("style"), fallback=6)
DEFAULT_MAP_ZOOM_VIDEO_FRAMES = normalize_zoom(_video_frames_map.get("zoom"), fallback=16)
DEFAULT_MAP_STYLE_OVERALL = normalize_map_style(_overall_map.get("style"), fallback=7)
DEFAULT_MAP_ZOOM_OVERALL = normalize_zoom(_overall_map.get("zoom"), fallback=14)

def prepare_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def fix_xiaomi_altitude_bug(ele):
    return None if ele==-20000 else ele

def mps_to_kmph(x):
    return x*3.6

def user_select(choices,prompt="Please choose",default=None):
    for i,p in enumerate(choices):
        console.print(f"[bold magenta][{i+1}][/]: [bold yellow]{escape(p)}[/]{" [bold cyan](default)[/]" if default==i else ""}")
    idx=IntPrompt.ask(
        prompt=prompt,
        choices=[str(i+1) for i in range(len(choices))],
        show_choices=False,
        default=None if default is None else default+1,
        show_default=False,
        )-1
    return idx,choices[idx],len(choices)

def smooth_moving_average(vals, window_size=5):
    """Simple moving average."""
    smoothed = np.convolve(vals, np.ones(window_size)/window_size, mode='same')
    return smoothed

def smooth_moving_average_angle(vals, window_size=5):
    """Moving average for cyclic angles (0-360 degrees)."""
    vals = np.asarray(vals, dtype=np.float64)
    rad = np.radians(vals)
    cos_vals = np.cos(rad)
    sin_vals = np.sin(rad)
    window = np.ones(window_size) / window_size
    cos_smoothed = np.convolve(cos_vals, window, mode='same')
    sin_smoothed = np.convolve(sin_vals, window, mode='same')
    rad_smoothed = np.arctan2(sin_smoothed, cos_smoothed)
    deg_smoothed = np.degrees(rad_smoothed)
    return deg_smoothed

def max_every_k_frames(vals, k:int):
    vals=vals.copy()
    n=len(vals)
    idx=list(range(0,n,k))
    for i,j in zip(idx,idx[1:]+[n]):
        vals[i:j]=[max(vals[i:j])]*(j-i)
    return vals

def square_box(ctr:tuple[float,float],hlf_sl:float):
    return [ctr[0]-hlf_sl,ctr[1]-hlf_sl,ctr[0]+hlf_sl,ctr[1]+hlf_sl]
    
def max_every_k_seconds(vals, k:float):
    return max_every_k_frames(vals,int(np.ceil(k*FPS)))

def fmt_time(dt: datetime | None) -> str:
    return dt.astimezone(TZ).strftime("%Y-%m-%d %H:%M") if dt else '--'

def fmt_tim_rich(dt: datetime | None) -> str:
    return dt.astimezone(TZ).strftime("[cyan]%Y-%m-%d [bold]%H:%M[/][/]") if dt else '[cyan]--[/]'

def start_file(file_path):

    file_path=Path(file_path)

    if not Path.exists(file_path):
        warn(f"Error: file not found: {file_path}")
        return

    sys_platform = platform.system()

    if sys_platform == "Windows":
        os.startfile(file_path)
    elif sys_platform == "Darwin":
        subprocess.run(["open", file_path])
    else:
        subprocess.run(["xdg-open", file_path])

def lonlat2px(lonlat:list[tuple[float,float]],zoom:int)->list[mtl.Tile]:
    return [mtl.tile(lon,lat,zoom+TX_EXP) for lon,lat in lonlat]

def px2lonlat(tiles:list[mtl.Tile])->list[tuple[float,float]]:
    return [tuple(mtl.ul(p)) for p in tiles]

from rich import print,inspect
if __name__=='__main__':
    lst=[i for i in range(10)][::-1]
    print(lst)
    print(max_every_k_frames(lst,4))
