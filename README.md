# GPX Video Maker

![demo](demo/QingShanLake.gif)

求求 star！

纯 Python 实现 GPX 轨迹生成轨迹视频

地图瓦片来自高德地图。若更换，请注意更改经纬坐标系。

如未能成功弹出选择文件窗口，请在 `utils.py` 中更改 `GUI_file_selection = False`。

## TODO
- [x] 用户选择长时间无轨迹点渲染方案
- [ ] 用户选择摄像机中心经纬度算法（1. 几个最近的点参照 2. 自定义定点 3. 固定矩形框中心）
- [ ] 预览渲染
- [ ] 中文翻译至英文
- [ ] 攥写 `requirements.txt`