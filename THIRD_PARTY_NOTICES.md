# 第三方来源说明

本文件区分本仓库的封装/适配与复用的上游组件，不将第三方代码、模型或游戏图像声明为原创。

## Blue Archive Auto Script（BAAS）

- 作者与贡献者：pur1fying、Kiramei 及 BAAS contributors。
- 主项目：<https://github.com/pur1fying/blue_archive_auto_script>
- 本机来源镜像：<https://gitee.com/pur1fy/blue_archive_auto_script>
- 实际源码提交：[`4b9fbfac851addf27b5c49a826ebf0e616d8a4ee`](https://github.com/pur1fying/blue_archive_auto_script/tree/4b9fbfac851addf27b5c49a826ebf0e616d8a4ee)，版本 1.4.3。
- 许可：GPL-3.0-only；原许可证保存在 `vendor/baas/LICENSE`，本仓库根目录也附有完整 GPLv3 文本。

`vendor/baas/core/`、`module/`、`gui/` 是复用的上游 Python 代码。便携版调用其中的窗口连接、图像/RGB 特征匹配、关卡数字 OCR、自动技能与倍速等组件。`baas_bridge.py` 在这些组件之上增加范围限制、实机图片集合、直接窗口截屏、内存配置和停止处理。

初版简中 PNG 来自上游 `src/images/CN/`；随后在当前汉化画面中裁取了对应区域。`visual.zh-CN.json` 逐项记录图片来源和 SHA-256。`local_game_capture/…` 是来源说明，不是随仓库公开的完整游戏截图。

## BAAS 本地 OCR 服务

- 源码项目：<https://github.com/pur1fying/BAAS_Cpp>
- 上游预构建项目：<https://github.com/pur1fying/BAAS_Cpp_prebuild>
- 实际使用的预构建镜像：<https://gitee.com/pur1fy/baas_-cpp_prebuild>
- 本机预构建提交：`0457cd0db559f4ac32afebfc94b9abef20182900`。

Release 中的 `BAAS_ocr_server.exe`、IPC 库、OCR 模型及其伴随库复用该预构建分发，不是本仓库自行实现或重新训练的 OCR。本仓库不声称知道该预构建对应的确切 C++ 源码提交；预构建提交与主源码项目分别列出，避免将二者错误等同。原项目的许可证和模型/依赖许可分别适用。

## 便携运行环境

便携包包含 CPython 3.9.13 以及运行所需第三方组件。CPython 原许可位于 `engine/.env/LICENSE.txt`，Python 包的元数据和许可保留在 `engine/.venv/Lib/site-packages/*.dist-info/` 及各包自带的许可文件中。

主要组件包括：PyQt5 5.15.11、Qt 5.15.2、PyQt-Fluent-Widgets 1.2.0、PyQt5-Frameless-Window 0.8.2、OpenCV Python 4.8.1.78、NumPy 1.24.4、Pillow 11.3.0、PyAutoGUI 0.9.54、MSS 10.0.0、pywin32 312、Requests 2.32.5、adbutils 2.2.1、uiautomator2 2.16.23、Rich 15.0.0 等。它们适用各自原有许可证，具体版本以包内元数据为准。

## 游戏图像与图标

界面文字截图、游戏角色、游戏名称与商标的权利归原权利人。用户提供并选择的 `packaging/app.ico` 来自既有 ICO 文件，表现为举“OK”牌的白发角色；当前未确认原始画师或图源授权信息，因此不将其标为本仓库原创，也不以 GPL 为第三方画作另行授予权利。

如权利人希望补充署名或处理素材，请通过仓库 Issue 联系维护者。
