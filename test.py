import math

# ========== 常用常量 ==========
PI = 3.1415926535897932384626
A  = 6378245.0
EE = 0.00669342162296594323


def out_of_china(lon, lat):
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)


def _delta(lon, lat):
    dLat = transform_lat(lon - 105.0, lat - 35.0)
    dLon = transform_lon(lon - 105.0, lat - 35.0)
    radLat = lat / 180.0 * PI
    magic = math.sin(radLat)
    magic = 1 - EE * magic * magic
    sqrtMagic = math.sqrt(magic)
    dLat = (dLat * 180.0) / ((A * (1 - EE)) / (magic * sqrtMagic) * PI)
    dLon = (dLon * 180.0) / (A / sqrtMagic * math.cos(radLat) * PI)
    return dLat, dLon


def transform_lat(x, y):
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * PI) + 40.0 * math.sin(y / 3.0 * PI)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * PI) + 320 * math.sin(y * PI / 30.0)) * 2.0 / 3.0
    return ret


def transform_lon(x, y):
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * PI) + 20.0 * math.sin(2.0 * x * PI)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * PI) + 40.0 * math.sin(x / 3.0 * PI)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * PI) + 300.0 * math.sin(x / 30.0 * PI)) * 2.0 / 3.0
    return ret


# ========== 核心转换函数 ==========

def wgs84_to_gcj02(wgs_lon, wgs_lat):
    if out_of_china(wgs_lon, wgs_lat):
        return wgs_lon, wgs_lat
    dlat, dlon = _delta(wgs_lon, wgs_lat)
    return wgs_lon + dlon, wgs_lat + dlat


def gcj02_to_wgs84(gcj_lon, gcj_lat):
    if out_of_china(gcj_lon, gcj_lat):
        return gcj_lon, gcj_lat
    dlat, dlon = _delta(gcj_lon, gcj_lat)
    return gcj_lon - dlon, gcj_lat - dlat


def gcj02_to_bd09(gcj_lon, gcj_lat):
    x = gcj_lon
    y = gcj_lat
    z = math.hypot(x, y) + 0.00002 * math.sin(y * PI * 3000.0 / 180.0)
    theta = math.atan2(y, x) + 0.000003 * math.cos(x * PI * 3000.0 / 180.0)
    return z * math.cos(theta) + 0.0065, z * math.sin(theta) + 0.006


def bd09_to_gcj02(bd_lon, bd_lat):
    x = bd_lon - 0.0065
    y = bd_lat - 0.006
    z = math.hypot(x, y) - 0.00002 * math.sin(y * PI * 3000.0 / 180.0)
    theta = math.atan2(y, x) - 0.000003 * math.cos(x * PI * 3000.0 / 180.0)
    return z * math.cos(theta), z * math.sin(theta)


def wgs84_to_bd09(wgs_lon, wgs_lat):
    gcj_lon, gcj_lat = wgs84_to_gcj02(wgs_lon, wgs_lat)
    return gcj02_to_bd09(gcj_lon, gcj_lat)


def bd09_to_wgs84(bd_lon, bd_lat):
    gcj_lon, gcj_lat = bd09_to_gcj02(bd_lon, bd_lat)
    return gcj02_to_wgs84(gcj_lon, gcj_lat)


# ========== 一键输出所有可能 ==========

def show_all_possible(lon: float, lat: float):
    print(f"\n输入坐标: {lon:.8f}, {lat:.8f}")
    print("以下是假设不同源坐标系后，所有可能的转换结果：\n")

    cases = [
        ("假设输入是 WGS-84",   lon, lat, wgs84_to_gcj02, wgs84_to_bd09),
        ("假设输入是 GCJ-02",   lon, lat, gcj02_to_wgs84, gcj02_to_bd09),
        ("假设输入是 BD-09",    lon, lat, bd09_to_wgs84,  bd09_to_gcj02),
    ]

    for title, src_lon, src_lat, to_other1, to_other2 in cases:
        print(title)
        print(f"  原坐标       →  {src_lon:11.6f}, {src_lat:10.6f}")
        
        if to_other1 == wgs84_to_gcj02 or to_other1 == bd09_to_gcj02:
            name1 = "GCJ-02"
        elif to_other1 == gcj02_to_wgs84 or to_other1 == bd09_to_wgs84:
            name1 = "WGS-84"
        else:
            name1 = "WGS-84"  # fallback

        if to_other2 == wgs84_to_bd09 or to_other2 == gcj02_to_bd09:
            name2 = "BD-09"
        else:
            name2 = "BD-09"   # fallback

        o1_lon, o1_lat = to_other1(src_lon, src_lat)
        o2_lon, o2_lat = to_other2(src_lon, src_lat)

        print(f"  → {name1:6}    {o1_lon:11.6f}, {o1_lat:10.6f}")
        print(f"  → {name2:6}    {o2_lon:11.6f}, {o2_lat:10.6f}")
        print()


if __name__ == "__main__":
    try:
        lon = float(input("请输入经度 lon: ").strip())
        lat = float(input("请输入纬度 lat: ").strip())
        show_all_possible(lon, lat)
    except ValueError:
        print("请输入有效的数字坐标")
    except KeyboardInterrupt:
        print("\n已取消")