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
    """basic info of a map tile"""
    x: int          
    y: int          
    zoom: int
    map_style: int  # map style  6=satellite, 7=vector
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
    return save_path.is_file() and save_path.stat().st_size > 0      # file exist and non-empty

def download_tiles(
    tiles: list[mtl.Tile],
    timeout: float | None = 10,
    retries: int = 3,
    backoff: float = 1.0,
    description: str = "download tiles",
) -> Path:
    """
    Download a single tile and return to the saved path.

    Parameters
    ----------
    tile : Tuple[int, int, int, int]
    timeout : float | None, optional
        Single request timeout (seconds), default is 10 seconds; None indicates no timeout.
    retries : int, optional
        Maximum retry count (excluding the first attempt), default is 3.
    backoff : float, optional
        The number of seconds to wait for the first retry, and it doubles for each subsequent attempt. The default value is 1.0 second.

    Returns
    -------
    Path
        The absolute path of the downloaded file.

    Raises
    ------
    RuntimeError
        Failed even after exhausting all retry attempts.
    """

    for tile in track(tiles, description=description):
        url = f"https://wprd02.is.autonavi.com/appmaptile?style={tile.map_style}&x={tile.x}&y={tile.y}&z={tile.zoom}"
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
                        f"Tile {tile.key} failed downloading(retried {retries} times)"
                    ) from exc
                time.sleep(wait)
                wait *= 2

def get_not_exists_tiles(tiles):
    return [tile for tile in tiles if not tile_exists(tile)]

tile_dict={}

def load_tile(tile,show_warning=True):
    if tile.key not in tile_dict:
        if tile_exists(tile):
            tile_dict[tile.key]=Image.open(map_tiles_dir / f"{tile.key}.png")
        else:
            if show_warning:
                warn(f"Failed to successfully load map tiles from the local file {tile.key}")
            return map_tile_default
    return tile_dict[tile.key]

if __name__=='__main__':
    pass