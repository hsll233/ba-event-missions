"""Read-only live recognition test. Never activates windows or sends input."""
import ctypes
import json
import os
import site
import sys
import time
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
settings = json.loads((HERE / "settings.json").read_text(encoding="utf-8"))
root = (HERE / settings["baas_root"]).resolve()
site.addsitedir(str(root / ".venv/Lib/site-packages"))
sys.path.insert(0, str(root))
os.chdir(root)
import cv2
import mss
import numpy as np
from core import image
from core.device.window_capture.windows.window_info import win32_WindowInfo
from visual_profile import install_profile


def probe():
    output = HERE / "output"
    output.mkdir(exist_ok=True)
    report = {"mode": "live_read_only", "input_sent": False, "window_activated": False}
    static = json.loads((root / "config/static.json").read_text(encoding="utf-8"))
    window = win32_WindowInfo(static["PC_app_process_name"]["JP"])
    if "--wait" in sys.argv and window.is_valid_window():
        deadline = time.monotonic() + 45
        while ctypes.windll.user32.GetForegroundWindow() != window._hwnd and time.monotonic() < deadline:
            time.sleep(0.5)
    if not window.is_valid_window():
        report.update(status="blocked", reason="game_window_not_found")
    elif ctypes.windll.user32.GetForegroundWindow() != window._hwnd and "--window-capture" not in sys.argv:
        report.update(status="blocked", reason="game_not_foreground_no_capture")
    else:
        width, height = window.get_resolution(activate=False)
        if width <= 0 or height <= 0 or abs(width / height - 16 / 9) > 0.05:
            raise RuntimeError("Invalid game capture size")
        left, top, right, bottom = window.get_region()
        if "--window-capture" in sys.argv:
            import win32gui
            import win32ui
            dc = win32gui.GetDC(window._hwnd)
            source = win32ui.CreateDCFromHandle(dc)
            memory = source.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(source, width, height)
            memory.SelectObject(bitmap)
            try:
                ok = ctypes.windll.user32.PrintWindow(window._hwnd, memory.GetSafeHdc(), 3)
                if not ok:
                    raise RuntimeError("Game window does not support background capture")
                frame = np.frombuffer(bitmap.GetBitmapBits(True), dtype=np.uint8).reshape(height, width, 4)[:, :, :3].copy()
                if frame.std() < 2:
                    raise RuntimeError("Game returned an empty background capture")
            finally:
                win32gui.DeleteObject(bitmap.GetHandle())
                memory.DeleteDC()
                source.DeleteDC()
                win32gui.ReleaseDC(window._hwnd, dc)
            report["capture_method"] = "PrintWindow_no_activation"
        else:
            with mss.mss() as grabber:
                frame = cv2.cvtColor(np.array(grabber.grab(
                    {"left": left, "top": top, "width": width, "height": height})), cv2.COLOR_BGRA2BGR)
        context = SimpleNamespace(ratio=width / 1280, latest_img_array=frame)
        profile = install_profile(context, HERE / settings["visual_profile"])
        matches = {name: bool(image.compare_image(context, name)) for name in profile["features"]}
        screenshot = output / "probe-game.png"
        success, encoded = cv2.imencode(".png", frame)
        if not success:
            raise RuntimeError("Cannot encode game capture")
        encoded.tofile(str(screenshot))
        mission_list = matches["activity_menu"] and any(matches["activity_mission-chosen-%d" % i] for i in range(3))
        report.update(status="recognized" if mission_list else "unrecognized", resolution=[width, height],
                      mission_list_recognized=mission_list, matches=matches, screenshot=str(screenshot))
    (output / "probe-result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "recognized" else 2


if __name__ == "__main__":
    raise SystemExit(probe())
