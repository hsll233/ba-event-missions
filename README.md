# 蔚蓝档案 · 活动任务助手

Windows 日服 PC 的活动任务 01～12 独立助手，适配简体中文汉化画面。提供便携运行环境和中文窗口，支持关卡范围、开始/停止、环境检查、报告与日志。

> 本项目基于 [Blue Archive Auto Script（BAAS）](https://github.com/pur1fying/blue_archive_auto_script) 的部分代码与素材整理、适配而成。识别引擎、数字 OCR 和游戏控制组件来自上游，具体来源见 [第三方来源说明](THIRD_PARTY_NOTICES.md)。本项目不是 BAAS 官方发行版。

## 下载与使用

从 [Releases](https://github.com/hsll233/ba-event-missions/releases/latest) 下载 `BAEventMissions-Portable.zip`，解压后双击 **活动任务助手.exe**。无需另外安装 Python 或 BAAS；保留整个文件夹，关闭助手后可整体移动。

1. 打开日服 PC 游戏，进入当前活动的中文 **任务** 关卡列表。
2. 准备好当前出战队伍，选择关卡范围（默认 1～12）。
3. 点击“开始任务”。需要结束时点击“停止”。

“检查环境”只验证本地依赖，不操作游戏。任务运行时会使用本地图片匹配与数字 OCR 点击游戏窗口，消耗现有体力；不会购买体力。程序不需要 OpenAI API。

## 功能与适用范围

- 按关卡号定位 01～12；已三星自动跳过，每次运行每关最多战斗一次。
- 使用游戏当前队伍，开启自动技能与三倍速，完成结算后重新验证三星。
- 非三星、战败、体力不足、识别失败、超时或用户停止时结束运行。
- 仅处理活动任务；不执行故事关、挑战关、日常调度、商店购买或循环扫荡。
- 游戏连接仍为日服 PC，识别图片为简体中文；更换语言不会把客户端切成国服。
- 通过直接读取游戏客户区解决 Windows 显示缩放导致的桌面截屏偏移，支持中文和带空格的安装路径。

**已实测**：2026-10-29，日服赛车活动「Start Your Engines！～183号よ永遠に！～」的任务 01～12 均已三星，并逐关重新识别确认。

以后相同布局的活动可以复用；活动界面、汉化译词、字体或排版变化时，需要更新 `app/assets/zh-CN/` 与 `app/visual.zh-CN.json`。未验证其他活动、其他服务器或 Android 模拟器。当前队伍是否能三星取决于实际练度与阵容。

## 文件与进度

便携包中的 `app/output/result.json` 记录本次的状态、已验证三星关卡、尝试战斗的关卡及错误原因；`app/output/run.log` 保存日志。每次运行都会重新读取游戏状态，不把旧报告当成通关依据。

源码仓库不包含账号配置、实机截图、运行日志、Python 安装目录或个人游戏数据。仓库中的日文 PNG 仅为负例测试夹具，不会被运行时识别器加载。

## 来源与许可证

本项目的适配代码按 **GPL-3.0-only** 提供，见 [LICENSE](LICENSE)。

| 部分 | 来源 |
| --- | --- |
| 游戏连接、图片/RGB 特征匹配、数字定位、自动战斗基础组件 | [pur1fying/blue_archive_auto_script](https://github.com/pur1fying/blue_archive_auto_script) |
| 本地 OCR 服务及其预构建分发 | [pur1fying/BAAS_Cpp](https://github.com/pur1fying/BAAS_Cpp)、[BAAS_Cpp_prebuild](https://github.com/pur1fying/BAAS_Cpp_prebuild) |
| 初始简中模板 | BAAS 的 `src/images/CN/` |
| 当前活动的汉化文字模板 | 从实际中文游戏画面裁取、重新校准，游戏图像权利归原权利人 |
| 程序图标 | 复用用户已有的举“OK”牌角色 ICO；原画作者未核实，不声明为本项目原创 |
| 中文启动窗口、任务范围封装、停止机制、便携打包和适配 | 本仓库 |

第三方运行库各自适用原许可证。游戏图像、角色图标、名称和商标不因代码的 GPL 许可而转移所有权。本项目与游戏官方没有隶属关系。详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 开发与构建

主程序源码位于仓库根目录，C# 启动器与打包脚本位于 `packaging/`。`vendor/baas/` 保存实际使用的 BAAS Python 源码快照与许可，提交为 `4b9fbfac851addf27b5c49a826ebf0e616d8a4ee`（1.4.3）。

构建需要 Windows、.NET Framework C# 编译器，以及已按上游说明初始化了 `.env` 和 `.venv` 的 BAAS 1.4.3 目录；项目不会自动下载或安装依赖。

```powershell
# 替换为你自己的 BAAS 目录。使用其自带的 Python 3.9 环境。
& 'C:\BAAS\.env\python.exe' '.\packaging\build_portable.py' `
  --baas-root 'C:\BAAS' --output '.\dist\BAEventMissions-Portable'

& 'C:\BAAS\.env\python.exe' '.\packaging\archive_portable.py' `
  --folder '.\dist\BAEventMissions-Portable' `
  --output '.\dist\BAEventMissions-Portable.zip'
```

便携版中的 `活动任务助手.exe --self-test` 执行离线环境检查。也可用包内 Python 运行 `app/test_mission_flow.py` 与 `app/test_visual_profile.py`；共 13 项离线测试，另完成了中文路径迁移、启动/停止按钮和 OCR 实机核验。
