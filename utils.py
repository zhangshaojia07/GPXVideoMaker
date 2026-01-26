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
import mercantile as mtl

console=Console(highlight=None)

def info(text="Tips:等红灯其实是在等绿灯"):
    console.print(f"[italic blue]{escape(text)}[/]")

def warn(text="Tips:等红灯其实是在等绿灯"):
    console.print(f"[italic red]{escape(text)}[/]")

r'''
In CMD:

C:\>set DEBUG="True"

Check:

C:\>echo %DEBUG%
'''
def get_bool_env(key: str, default: bool = False) -> bool:
    """从环境变量读取 bool 配置，兼容常见写法"""
    val = os.getenv(key, "").strip().lower()
    if val in ("true", "1", "yes", "on", "t", "y"):
        return True
    if val in ("false", "0", "no", "off", "f", "n"):
        return False
    # 非法值时返回默认（也可以 raise ValueError，如果想更严格）
    return default

is_debug = get_bool_env('DEBUG',default=False)

GUI_file_selection = get_bool_env('GUI_FILE_SELECTION',default=True)

is_convert_wgs_to_gcj = True

TZ_name = "Asia/Shanghai"
TZ = pytz.timezone(TZ_name)

TX_EXP = 8

FPS = 30

track_fail_interval_sec = 3 * 60

preview_frame_no = 1

def prepare_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def fix_xiaomi_altitude_bug(ele):
    return None if ele==-20000 else ele

def mps_to_kmph(x):
    return x*3.6

def user_select(choices,prompt="请选择",default=None):
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
    """简单的移动平均"""
    smoothed = np.convolve(vals, np.ones(window_size)/window_size, mode='same')
    return smoothed

def smooth_moving_average_angle(vals, window_size=5):
    """适配0~360度循环角度的移动平均函数"""
    # 1. 转换为numpy数组，确保数据类型正确
    vals = np.asarray(vals, dtype=np.float64)
    
    # 2. 角度转弧度（numpy三角函数默认用弧度）
    rad = np.radians(vals)
    
    # 3. 计算每个角度的cos和sin分量（矢量表示）
    cos_vals = np.cos(rad)
    sin_vals = np.sin(rad)
    
    # 4. 对cos、sin分量分别做移动平均（保持mode='same'保证长度一致）
    window = np.ones(window_size) / window_size
    cos_smoothed = np.convolve(cos_vals, window, mode='same')
    sin_smoothed = np.convolve(sin_vals, window, mode='same')
    
    # 5. 矢量转回角度（arctan2返回-π~π）
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

    # 检查文件是否存在
    if not Path.exists(file_path):
        warn(f"错误：找不到文件 {file_path}")
        return

    sys_platform = platform.system()

    if sys_platform == "Windows":
        # Windows 专用，最简单
        os.startfile(file_path)
    elif sys_platform == "Darwin":
        # macOS 指令
        subprocess.run(["open", file_path])
    else:
        # Linux (如 Ubuntu) 指令
        subprocess.run(["xdg-open", file_path])

def lonlat2px(lonlat:list[tuple[float,float]],zoom:int):
    return [mtl.tile(lon,lat,zoom+TX_EXP) for lon,lat in lonlat]

from rich import print,inspect
if __name__=='__main__':
    lst=[i for i in range(10)][::-1]
    print(lst)
    print(max_every_k_frames(lst,4))