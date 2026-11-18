# **GPX Video Maker**

![Stars](https://img.shields.io/github/stars/zhangshaojia07/GPXVideoMaker?style=flat&color=ffd700)
![Python](https://img.shields.io/badge/python-3.12-blue?style=flat&logo=python)
![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)
![FFmpeg](https://img.shields.io/badge/dependency-FFmpeg-red?logo=ffmpeg&logoColor=white)
![License](https://img.shields.io/github/license/zhangshaojia07/GPXVideoMaker?style=flat)

> 📍 **From GPX track to polished video, in one step.**

![demo](demo/QingShanLake.gif)

Please leave a free Star⭐ if you find this useful. Thank you!

This is a Python project managed with [uv](https://github.com/astral-sh/uv).

It renders GPX tracks into track animation videos.

## ✨ Features

* 📍 GPX track parsing
* 🎬 High-definition FFmpeg rendering
* 🗺️ AMap (Gaode) map tile support
* 🖱️ GUI file-picker interface

## 📋 Prerequisites

This project depends on FFmpeg. Please install it and configure the environment variable yourself.

## 🛠 Quick Start

If you already have `uv` installed, it only takes two steps to run:

1️⃣ **Clone the repository and enter the directory**:
```bash
git clone https://github.com/zhangshaojia07/GPXVideoMaker.git
cd GPXVideoMaker
```

2️⃣ **Sync the environment and run**:
```bash
uv sync
uv run main.py
```

*(These commands automatically create a virtual environment, install dependencies, and run the script.)*

## 🐍 Traditional approach (using pip)

If you do not have `uv` installed, you can use the traditional `pip` workflow instead:

Click the green **Code** button 👉 **Download ZIP** 👉 extract it to a folder you like.

1️⃣ **Create a virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```

2️⃣ **Install dependencies**:
```bash
pip install -r requirements.txt
```

3️⃣ **Run**:
```bash
python main.py
```

## 💡 Tips

If the file-picker window does not pop up, run `export GUI=False` (Linux/Mac) or `set GUI=False` (Windows) in the terminal.

> If you do not want to type the command every time, you can hardcode `enable_GUI` in `utils.py`.

The source GPX file of the demo animation is available under the `debug/` directory for testing.

Map tiles come from AMap (Gaode). If you switch tile providers, remember to adjust the coordinate system accordingly.

## 🤝 Contributing & Feedback

Issues and Pull Requests are welcome.

## ✅ TODO
- [x] Let the user choose how to render long stretches without track points
- [x] Let the user choose the camera center longitude/latitude algorithm
  - [x] Add camera cage mode for the follow mode
  - [x] Add the switch mode
    - [ ] EaseInOut camera movement when switching (freeze time or not)
- [x] Preview rendering
  - [ ] Configure preview parameters
- [x] Update the usage tutorial in the README
- [ ] Add an "I only need a single overall image" mode

## 🚦 Project Flow

```mermaid
graph TD
    A[Read GPX file]
    B[Select output type]
    D[Set map zoom]
    E[Set overlay styles]
    F["Set camera movement mode (video)"]
    G[Select output location]
    H[Render]
    I[Output]
    J[Download all map tiles]
    K[Render preview frame]
    L[Download preview-frame map tiles]
    A --> O1
    B --> O1
    O1 --> O2
    D --> O2
    E --> O2
    F --> O2
    O2 --> O3
    L --> K
    K --> O3
    O3 --> O1
    O3 --> I
    G --> I
    J --> H
    H --> I
```

## 📜 Copyright & License

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Assets: NOTICE](https://img.shields.io/badge/Assets-NOTICE-blue.svg)](NOTICE)

The project code is open-sourced under the **[MIT License](LICENSE)**.
For third-party font and game asset copyright details, see the **[NOTICE file](NOTICE)**.
