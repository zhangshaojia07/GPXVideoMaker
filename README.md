# **GPX Video Maker**

![Stars](https://img.shields.io/github/stars/zhangshaojia07/GPXVideoMaker?style=flat&color=ffd700)
![Python](https://img.shields.io/badge/python-3.12-blue?style=flat&logo=python)
![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)
![FFmpeg](https://img.shields.io/badge/dependency-FFmpeg-red?logo=ffmpeg&logoColor=white)
![License](https://img.shields.io/github/license/zhangshaojia07/GPXVideoMaker?style=flat)

> 📍 **从 GPX 轨迹到精美视频，只需一步。**

![demo](demo/QingShanLake.gif)

求求各位留下免费的 Star⭐ 谢谢！

这是一个使用 [uv](https://github.com/astral-sh/uv) 进行管理的 Python 项目

该项目功能为 GPX 轨迹生成轨迹视频

## ✨ 功能特性

* 📍 GPX 轨迹解析
* 🎬 FFmpeg 高清渲染
* 🗺️ 高德地图瓦片支持
* 🖱️ GUI 文件选择界面

## 📋 前置要求

本项目依赖 FFmpeg，请自行安装并配置环境变量。

## 🛠 快速开始

如果你已经安装了 `uv`，只需两步即可运行：

1️⃣ **克隆项目并进入目录**:
```bash
git clone https://github.com/zhangshaojia07/GPXVideoMaker.git
cd GPXVideoMaker
```

2️⃣ **同步环境并运行**:
```bash
uv run main.py
```

*(该命令会自动创建虚拟环境、安装依赖并执行脚本)*


## 🐍 传统方式 (使用 pip)

如果你没有安装 `uv`，也可以使用传统的 `pip` 工作流：

点击绿色的 **Code** 按钮 👉 **Download ZIP** 👉 解压到你喜欢的文件夹

1️⃣ **创建虚拟环境**:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows 使用: .venv\Scripts\activate
```


2️⃣ **安装依赖**:
```bash
pip install -r requirements.txt
```


3️⃣ **运行**:
```bash
python main.py
```

## 💡 Tips

如果无法弹出文件选择窗口，请在终端执行 `export GUI_FILE_SELECTION=False` (Linux/Mac) 或 `set GUI_FILE_SELECTION=False` (Windows)。

> 如果不想每次都输入命令，可以直接在 `utils.py` 中找到 `GUI_file_selection` 硬编码。

项目 `debug/` 目录下有演示动图的源 GPX 文件，可供测试。

地图瓦片来自高德地图。若更换，请注意更改经纬坐标系。

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request

## ✅ TODO
- [x] 用户选择长时间无轨迹点渲染方案
- [ ] 用户选择摄像机中心经纬度算法（1. 几个最近的点参照 2. 自定义定点 3. 固定矩形框中心）
- [ ] 预览渲染
- [x] 攥写 `requirements.txt`
- [ ] 添加英文版 README