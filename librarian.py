import requests, time
from pathlib import Path
from requests.exceptions import RequestException, HTTPError, Timeout
from dataclasses import dataclass
from utils import *
from PIL import Image
import mercantile as mtl
from rich.progress import track

map_tiles_dir=prepare_dir(Path("map_tiles"))

map_tile_default = Image.open("graphics/map_tile_default.png")

# https://blog.csdn.net/ChatGIS/article/details/144867297

@dataclass(frozen=True)
class MapTile:
    """表示一张地图瓦片的基本信息"""
    x: int          
    y: int          
    zoom: int       # 缩放层级
    map_style: int  # 地图风格。6 为卫星，7 为矢量。
    def __post_init__(self):
        for field_name, value in self.__dict__.items():
            if not isinstance(value, int):
                raise TypeError(
                    f"Field '{field_name}' must be int, got {type(value).__name__}"
                )
        if self.zoom < 1 or self.zoom > 18:
            raise ValueError(f"Invalid zoom level: {self.zoom}")
        if self.map_style < 1 not in {6,7}:
            raise ValueError(f"Invalid map style: {self.map_style}")
        for it in {self.x,self.y}:
            if it < 0 or it >= (1<<self.zoom):
                raise ValueError(f"xy out of bounds {self.x},{self.y}")

    @property
    def key(self) -> str:
        return f"{self.zoom}_{self.x}_{self.y}_{self.map_style}"

    def to_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.zoom, self.map_style)

    @classmethod
    def from_tuple(cls, t: tuple[int, int, int, int]) -> 'MapTile':
        if len(t) != 4:
            raise ValueError("Tuple must have exactly 4 elements")
        return cls(*t)

def tile_exists(tile:MapTile) -> bool:
    save_path = map_tiles_dir / f"{tile.key}.png"
    return save_path.is_file() and save_path.stat().st_size > 0      # 文件存在且非空

def download_tiles(
    tiles: list[mtl.Tile],
    timeout: float | None = 10,
    retries: int = 3,
    backoff: float = 1.0,
) -> Path:
    """
    下载单张瓦片并返回保存路径。

    Parameters
    ----------
    tile : Tuple[int, int, int, int]
        瓦片信息。
    timeout : float | None, optional
        单次请求超时（秒），默认 10 s；None 表示无超时。
    retries : int, optional
        最大重试次数（不含首次），默认 3。
    backoff : float, optional
        首次重试等待秒数，后续×2 退避，默认 1.0 s。

    Returns
    -------
    Path
        下载后的文件绝对路径。

    Raises
    ------
    RuntimeError
        用尽重试次数后仍失败。
    """

    for tile in track(tiles, description="下载瓦片"):
        url = f"https://wprd01.is.autonavi.com/appmaptile?style={tile.map_style}&x={tile.x}&y={tile.y}&z={tile.zoom}"
        save_path = map_tiles_dir / f"{tile.key}.png"

        wait = backoff
        for attempt in range(retries + 1):
            try:
                resp = requests.get(url, timeout=timeout, stream=True, headers={"Referer": "https://ditu.amap.com/"})
                resp.raise_for_status()
                with save_path.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        fh.write(chunk)
            except (RequestException, HTTPError, Timeout) as exc:
                if attempt == retries:
                    raise RuntimeError(
                        f"瓦片 {tile.key} 下载失败（重试{retries}次）"
                    ) from exc
                time.sleep(wait)
                wait *= 2

def get_not_exists_tiles(tiles):
    return [tile for tile in tiles if not tile_exists(tile)]

tile_dict={}

def preload_tiles(tiles:list[MapTile]):
    for tile in tiles:
        tile_dict[tile.key]=Image.open(map_tiles_dir / f"{tile.key}.png")

def load_tile(tile,show_warning=True):
    if tile.key in tile_dict:
        return tile_dict[tile.key]
    else:
        if show_warning:
            warn(f"未能成功从本地文件加载地图瓦片 {tile.key}，使用默认瓦片填充")
        return map_tile_default