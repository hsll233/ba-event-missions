"""Build a relocatable portable folder from the installed, tested runtime."""
import ast
import argparse
import importlib
import json
import os
import shutil
import site
import subprocess
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description="Build the standalone portable bundle from an initialized BAAS 1.4.3 tree")
parser.add_argument("--baas-root", type=Path, required=True)
parser.add_argument("--output", type=Path, default=SOURCE / "dist/BAEventMissions-Portable")
args = parser.parse_args()
INSTALLED = args.baas_root.resolve()
DEST = args.output.resolve()
if DEST.exists():
    raise SystemExit("Output already exists; use a new output directory to preserve existing files")

site_packages = INSTALLED / ".venv/Lib/site-packages"
site.addsitedir(str(site_packages))
sys.path.insert(0, str(INSTALLED))
os.chdir(INSTALLED)
from core.Baas_thread import Baas_thread
# Cover the PC-only lazy imports used after initialization as well as the
# import-time graph. Importing these does not send desktop input.
for name in ("pyautogui", "mss", "win32gui", "win32ui", "win32con"):
    importlib.import_module(name)

used = set()
for module in list(sys.modules.values()):
    file = getattr(module, "__file__", None)
    if file:
        try:
            used.add(Path(file).resolve().relative_to(site_packages.resolve()).parts[0])
        except ValueError:
            pass

ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".git", "output", "log", "logs")
engine = DEST / "engine"
engine.mkdir(parents=True)
shutil.copytree(INSTALLED / ".env", engine / ".env", ignore=ignore)
for name in ("core", "module", "gui"):
    shutil.copytree(INSTALLED / name, engine / name, ignore=ignore)
packages = engine / ".venv/Lib/site-packages"
packages.mkdir(parents=True)
# Shared binary directories and package metadata are necessary even when
# their contents don't appear as modules in sys.modules.
for item in site_packages.iterdir():
    if item.name in used or item.name.endswith((".dist-info", ".libs")) or (item.is_file() and item.suffix in (".py", ".pyd")) or item.name in ("pywin32.pth", "_distutils_hack"):
        if item.is_dir():
            shutil.copytree(item, packages / item.name, ignore=ignore)
        else:
            shutil.copy2(item, packages / item.name)

(engine / "src/rgb_feature").mkdir(parents=True)
shutil.copy2(INSTALLED / "src/rgb_feature/JP.json", engine / "src/rgb_feature/JP.json")
(engine / "config/default_config").mkdir(parents=True)
shutil.copy2(INSTALLED / "config/static.json", engine / "config/static.json")
(engine / "config/gui.json").write_text(json.dumps({"MainWindow": {"Language": "zh_CN"}}), encoding="utf-8")
# Create a fresh profile from upstream defaults; never copy a user's push
# credentials, account resource counters, profile history, or logs.
tree = ast.parse((INSTALLED / "core/config/default_config.py").read_text(encoding="utf-8"))
for node in tree.body:
    if isinstance(node, ast.Assign) and any(getattr(target, "id", "") == "DEFAULT_CONFIG" for target in node.targets):
        profile = json.loads(ast.literal_eval(node.value))
        break
else:
    raise RuntimeError("Default config not found")
profile.update(name="活动任务助手", server="日服PC端", screenshot_method="mss", control_method="pyautogui",
               open_emulator_stat=False, autostart=False, then="无动作", push_after_error=False,
               push_after_completion=False)
(engine / "config/default_config/config.json").write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

app = DEST / "app"
app.mkdir()
for filename in ("run_event_missions.py", "baas_bridge.py", "mission_flow.py", "visual_profile.py", "probe_game.py",
                 "visual.zh-CN.json", "test_visual_profile.py", "test_mission_flow.py", "LICENSE.BAAS.txt"):
    shutil.copy2(SOURCE / filename, app / filename)
shutil.copytree(SOURCE / "assets", app / "assets")
for relative in ("activity/common/task-info.png", "activity/common/mission-chosen-0.png", "activity/common/unit-formation.png"):
    target = app / "tests/fixtures/JP" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(INSTALLED / "src/images/JP" / relative, target)
(app / "settings.json").write_text(json.dumps({"baas_root": "../engine", "profile": "default_config",
                                             "visual_profile": "visual.zh-CN.json"}, indent=2), encoding="utf-8")
shutil.copy2(SOURCE / "LICENSE.BAAS.txt", DEST / "LICENSE.BAAS.txt")
shutil.copytree(SOURCE / "packaging", DEST / "source/packaging", ignore=ignore)
(DEST / "source").joinpath("BUILD.txt").write_text(
    "Launcher.cs: compile with Windows .NET Framework csc, references System.Windows.Forms, System.Drawing, System.Web.Extensions.\n"
    "Python application sources are in ../app; vendored BAAS sources in ../engine.\n"
    "Upstream: https://github.com/pur1fying/blue_archive_auto_script (GPL-3.0-only).\n", encoding="utf-8")
(DEST / "README.txt").write_text(
    "活动任务助手 · 独立便携版\n\n"
    "双击 活动任务助手.exe 打开窗口。无需安装 Python 或 BAAS。\n"
    "请保留整个文件夹；可以整体复制到其他目录。程序和数据都保存在这个文件夹内。\n\n"
    "1. 打开日服 PC 游戏，并进入中文的活动「任务」列表。\n"
    "2. 准备好出战队伍，选择关卡范围（默认 1～12）。\n"
    "3. 点击「开始任务」，需要暂停时点击「停止」。\n\n"
    "已三星的关卡自动跳过；每次运行每关最多战斗一次；不购买体力。\n"
    "此版本已在当前赛车活动上完成 01～12 三星实机测试。\n"
    "其他活动沿用同样布局时可复用；界面、译词、字体变化时需要更新 app/assets/zh-CN 和视觉清单。\n"
    "支持日服 PC 简体中文汉化画面，不支持 Android 模拟器或其他服务器。\n"
    "报告和日志：app/output。模板清单：app/visual.zh-CN.json。\n"
    "首次使用可先点击「检查环境」，这不会操作游戏。\n\n"
    "程序使用本地 OCR 和图片匹配，不需要 OpenAI API，也不需要连接原 BAAS 安装目录。\n"
    "原项目代码和图片版权归原作者，许可见 LICENSE.BAAS.txt；源代码随包附带。\n",
    encoding="utf-8-sig")
csc = Path(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
custom_icon = SOURCE / "packaging/app.ico"
icon_arguments = []
if custom_icon.exists():
    shutil.copy2(custom_icon, DEST / "app.ico")
    icon_arguments = ["/win32icon:" + str(DEST / "app.ico")]
subprocess.run([str(csc), "/nologo", "/target:winexe", "/platform:x64",
                "/reference:System.Windows.Forms.dll", "/reference:System.Drawing.dll",
                "/reference:System.Web.Extensions.dll", "/out:" + str(DEST / "活动任务助手.exe"),
                str(SOURCE / "packaging/Launcher.cs")] + icon_arguments, check=True)
size = sum(file.stat().st_size for file in DEST.rglob("*") if file.is_file())
print(json.dumps({"portable_folder": str(DEST), "size_mb": round(size / 1024**2, 1),
                  "packages": sorted(used)}, ensure_ascii=False, indent=2))
