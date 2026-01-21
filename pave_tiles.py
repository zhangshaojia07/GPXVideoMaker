from librarian import MapTile,download_tiles,preload_tiles,get_not_exists_tiles,load_tile
import mercantile as mtl
from rich.progress import track
from utils import TX_EXP

needed_tiles: set[MapTile] = set()

def pave_tiles_preload(width,height,ctr_px,map_style):
    zoom2=ctr_px.z
    zoom=zoom2-TX_EXP
    lt_px=mtl.Tile(ctr_px.x-width//2,ctr_px.y-height//2,zoom2)
    rb_px=mtl.Tile(lt_px.x+width-1,lt_px.y+height-1,zoom2)
    lt_tile=mtl.parent(lt_px,zoom=zoom)
    rb_tile=mtl.parent(rb_px,zoom=zoom)
    tiles=[MapTile(x,y,zoom,map_style) for x in range(lt_tile.x,rb_tile.x+1) for y in range(lt_tile.y,rb_tile.y+1)]
    needed_tiles.update(tiles)

def pave_tiles(img,ctr_px,map_style):
    width,height=img.size
    zoom2=ctr_px.z
    zoom=zoom2-TX_EXP
    lt_px=mtl.Tile(ctr_px.x-width//2,ctr_px.y-height//2,zoom2)
    rb_px=mtl.Tile(lt_px.x+width-1,lt_px.y+height-1,zoom2)
    lt_tile=mtl.parent(lt_px,zoom=zoom)
    rb_tile=mtl.parent(rb_px,zoom=zoom)
    tiles=[MapTile(x,y,zoom,map_style) for x in range(lt_tile.x,rb_tile.x+1) for y in range(lt_tile.y,rb_tile.y+1)]
    for tile in tiles:
        off_x,off_y=tile.x<<TX_EXP,tile.y<<TX_EXP
        img.paste(load_tile(tile),(off_x-lt_px.x,off_y-lt_px.y))

def prepare_tiles():
    tiles_to_be_downloaded=get_not_exists_tiles(needed_tiles)
    download_tiles(tiles_to_be_downloaded)
    preload_tiles(needed_tiles)

from rich import inspect
from PIL import Image
if __name__=='__main__':
    lon_min, lat_min = 119.8, 29.9      # 杭州西南角
    lon_max, lat_max = 120.6, 30.5      # 杭州东北角

    map_settings = {
        'ctr_px': mtl.tile(120.16832787794688,30.192544547086104,18+TX_EXP),
        'map_style': 7
    }

    img_w,img_h=1920,1080
    img_w,img_h=1280,720

    img=Image.new("RGB",(img_w,img_h))

    pave_tiles_preload(width=img_w,height=img_h,**map_settings)

    prepare_tiles()

    pave_tiles(img=img,**map_settings)

    img.show()