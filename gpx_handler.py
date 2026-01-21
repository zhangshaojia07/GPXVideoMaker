import gpxpy
from rich.console import Console
from rich.prompt import Prompt
from rich.markup import escape
from rich.tree import Tree
from datetime import datetime
from utils import TZ,fix_xiaomi_altitude_bug,info,is_convert_wgs_to_gcj,fmt_tim_rich,fmt_time
from coord_convert.transform import wgs2gcj

console = Console(highlight=None)

def style_line(i, name, km, up, start, end):
    # 粉紫加粗序号
    num = f'[bold magenta][{i}][/]'
    # 红色加粗 Track 名
    track = f'[bold red]{escape(name or f"Track{i}")}[/]'
    # 绿色距离/爬升
    dist = f'[green]{km:.2f}km[/]'
    elev = f'[green]{up:.0f}m[/]'
    # 日期和时间
    s_fmt = fmt_tim_rich(start)
    e_fmt = fmt_tim_rich(end)

    return f'{num}: {track}  →{dist}  ↑{elev}  {s_fmt} ~ {e_fmt}'

def extract_gpx(gpx_file):

    gpx = gpxpy.parse(open(gpx_file))
    info(f"GPX 文件导入成功: {gpx_file}")

    for point in (point 
                for track in gpx.tracks 
                for segment in track.segments 
                for point in segment.points):
        point.elevation = fix_xiaomi_altitude_bug(point.elevation)

    # 列出所有 Track & Segment
    root = Tree("[bold bright_white]GPX Tracks[/]", guide_style="bright_black")

    choices = []

    for i, trk in enumerate(gpx.tracks, 1):
        md, ud = trk.get_moving_data(), trk.get_uphill_downhill()
        start, end = trk.get_time_bounds()

        # 一级节点：track 概要
        track_line = style_line(i,
                            trk.name,
                            md.moving_distance/1000,
                            ud.uphill,
                            start,
                            end)
        track_node = root.add(track_line, style="default", highlight=False)

        # 二级节点：逐个 segment
        for seg_idx, seg in enumerate(trk.segments, 1):
            seg_md, seg_ud = seg.get_moving_data(), seg.get_uphill_downhill()
            seg_start, seg_end = seg.get_time_bounds()
            seg_line = style_line(f"{i}.{seg_idx}",
                                f"Segment {seg_idx}",
                                seg_md.moving_distance/1000,
                                seg_ud.uphill,
                                seg_start,
                                seg_end)
            track_node.add(seg_line, highlight=False)
            
            choices.append(f"{i}.{seg_idx}")

    console.print(root)
    
    if len(choices)==1:
        idx = choices[0]
    else:
        idx = Prompt.ask('选择要导入的 Segment 编号',choices=choices)
    idx = idx.split(".")
    
    seg = gpx.tracks[int(idx[0])-1].segments[int(idx[1])-1]

    seg.reduce_points(0.01)

    # alternative: https://lbs.amap.com/api/webservice/guide/api/convert
    if is_convert_wgs_to_gcj:
        for point in seg.points:
            point.longitude,point.latitude = wgs2gcj(point.longitude,point.latitude)

    return seg

from rich import print,inspect
import matplotlib.pyplot as plt
if __name__=='__main__':
    gpx_file=r"C:\Users\19607\Desktop\cycling\Z20260116.gpx"
    seg=extract_gpx(gpx_file)
    print(len(seg.points))
    
    print(seg.points[655:660])

    point=seg.points[600]
    print(point.course_between(seg.points[599]))

    # seg.points={}
    # inspect(seg,all=True)

'''
seg:
get_bounds
get_time_bounds
get_speed

pnt:
ele
lat
lon
time
course_between
distance_2d
time_difference
'''