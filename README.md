# GPX Video Maker

![demo](demo/QingShanLake.gif)

求求各位留下免费的 Star⭐ 谢谢！

Python 实现 GPX 轨迹生成轨迹视频

## 快速开始

### 1. 获取项目代码

**方式一：使用 Git**

```bash
git clone https://github.com/zhangshaojia07/GPXVideoMaker.git
```

**方式二：直接下载压缩包**

点击绿色的 **Code** 按钮 👉 **Download ZIP** 👉 解压到你喜欢的文件夹

### 2. 使用终端进入项目目录

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 运行程序

```bash
python main.py
```

如未能成功弹出选择文件窗口，请运行前设置环境变量  `GUI_FILE_SELECTION = False`

项目 `debug/` 目录下有演示动图的源 GPX 文件，可供测试。

## Tips

地图瓦片来自高德地图。若更换，请注意更改经纬坐标系。

## TODO
- [x] 用户选择长时间无轨迹点渲染方案
- [ ] 用户选择摄像机中心经纬度算法（1. 几个最近的点参照 2. 自定义定点 3. 固定矩形框中心）
- [ ] 预览渲染
- [ ] 中文翻译至英文
- [ ] 攥写 `requirements.txt`