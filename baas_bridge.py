"""Adapter to the user's installed BAAS 1.4.3.

Only constructed by an explicit --run. Reuses BAAS template matching,
English-digit OCR, stage search and auto-battle controls. No scheduler.
"""
import json
import logging
import signal
import socket
import time
from pathlib import Path

from mission_flow import MissionStopped
from visual_profile import install_profile


REQUIRED_IMAGES = (
    "activity_menu", "activity_task-info", "activity_mission-enter-task-button",
    "activity_mission-chosen-0", "activity_mission-chosen-1", "activity_mission-chosen-2",
    "activity_formation", "activity_self-formation", "normal_task_fight-confirm", "normal_task_fail-confirm",
    "activity_fight-success-confirm", "normal_task_task-finish", "normal_task_prize-confirm",
    "purchase_ap_notice", "purchase_ap_notice-localized",
)


class LogSignal:
    def emit(self, level, message):
        logging.log({1: logging.INFO, 2: logging.WARNING, 3: logging.ERROR,
                     4: logging.CRITICAL}.get(level, logging.INFO), message)


def verify_libraries(root, visual_path):
    """Imports and template loading only: never constructs a device or OCR server."""
    from types import SimpleNamespace
    from core import position
    from core.Baas_thread import Baas_thread  # Validate transitive dependencies too.
    from core.ocr.ocr import Baas_ocr
    context = SimpleNamespace()
    visual = install_profile(context, visual_path)
    images = position.image_dic[context.identifier]
    missing = [name for name in REQUIRED_IMAGES if name not in images]
    if missing:
        raise MissionStopped("Missing templates: " + ", ".join(missing))
    rgb = context.rgb_feature
    needed = ("sideTaskSSS", "sideTaskNoPass", "fighting_feature", "formation_edit1")
    if any(key not in rgb for key in needed):
        raise MissionStopped("Required JP color features are missing")
    return {"library_imports": "ok", "visual_identifier": context.identifier,
            "ui_language": visual["ui_language"], "active_template_source": "CN",
            "active_feature_positions": len(images), "japanese_templates_active": 0,
            "device_initialized": False, "ocr_started": False, "input_sent": False}


def memory_config(root, profile):
    """Implement the small ConfigSet interface in memory; never save source config."""
    from core.config.generated_user_config import Config
    from core.config.generated_static_config import StaticConfig

    class MemoryConfig:
        def get(self, key, default=None):
            return getattr(self.config, key, default)

        def set(self, key, value):
            setattr(self.config, key, value)

    data = json.loads(profile.read_text(encoding="utf-8"))
    if data["server"] != "日服PC端":
        raise MissionStopped("This extracted entry currently targets the installed JP PC client")
    data.update(open_emulator_stat=False, autostart=False, then="无动作",
                push_after_error=False, push_after_completion=False,
                screenshot_method="mss", control_method="pyautogui")
    config = MemoryConfig()
    config.config = Config(**data)
    config.config_dir = str(profile.parent)
    config.server_mode = "JP"
    config.static_config = StaticConfig(**json.loads(
        (root / "config/static.json").read_text(encoding="utf-8")))
    return config


class BaasMissionPort:
    def __init__(self, root, profile, output, visual_path):
        from core.Baas_thread import Baas_thread
        from core import color, image, picture
        from core.ocr.ocr import Baas_ocr
        from core.ocr.baas_ocr_client.Client import BaasOcrClient, ServerConfig
        from module import main_story

        self.color, self.image, self.picture = color, image, picture
        self.battle = main_story
        self.visual_path = visual_path
        self.stop_file = output / "STOP"
        if self.stop_file.exists():
            raise MissionStopped("STOP file exists; remove it manually before a new run")
        self.client = None
        self.context = None
        self.deadline = None
        self.previous_signals = {}
        owner = self

        class MissionContext(Baas_thread):
            def get_screenshot_array(self):
                # Capture the game's client bitmap directly. Desktop MSS can
                # read a displaced region under Windows display scaling.
                import ctypes
                import numpy as np
                import win32gui
                import win32ui
                owner.ensure_running()
                self.screenshot.ensure_interval()
                window = self.connection.app_process_window
                width, height = window.get_resolution(activate=False)
                dc = win32gui.GetDC(window._hwnd)
                source = win32ui.CreateDCFromHandle(dc)
                memory = source.CreateCompatibleDC()
                bitmap = win32ui.CreateBitmap()
                bitmap.CreateCompatibleBitmap(source, width, height)
                memory.SelectObject(bitmap)
                try:
                    if not ctypes.windll.user32.PrintWindow(window._hwnd, memory.GetSafeHdc(), 3):
                        raise MissionStopped("Game window capture failed")
                    frame = np.frombuffer(bitmap.GetBitmapBits(True), dtype=np.uint8).reshape(height, width, 4)[:, :, :3].copy()
                    if frame.std() < 2:
                        raise MissionStopped("Game returned an empty frame")
                    self.handle_resolution_dynamic_change()
                    self.screenshot.last_screenshot_time = time.time()
                    return frame
                finally:
                    win32gui.DeleteObject(bitmap.GetHandle())
                    memory.DeleteDC()
                    source.DeleteDC()
                    win32gui.ReleaseDC(window._hwnd, dc)

            def init_image_resource(self):
                owner.visual = install_profile(self, owner.visual_path)
                return True

            def get_ocr_language(self):
                # Words are recognized with actual CN PNG templates. OCR is
                # restricted to the shared 01-12 digits, not Japanese text.
                self.ocr_language = "en-us"

            # Synchronous input: no queued click threads left after a stop.
            def click(self, x, y, count=1, rate=0, duration=0, wait_over=False):
                for _ in range(count):
                    owner.ensure_running()
                    self.control.click(int(x * self.ratio), int(y * self.ratio))
                    if rate + duration > 0:
                        time.sleep(rate + duration)

            def update_screenshot_array(self):
                owner.ensure_running()
                super().update_screenshot_array()
                if any(image.compare_image(self, name) for name in (
                    "purchase_ap_notice", "purchase_ap_notice-localized")):
                    raise MissionStopped("AP exhausted; stopped at the purchase dialog")
                if image.compare_image(self, "normal_task_fail-confirm"):
                    raise MissionStopped("Battle failed; no automatic replay")

            def check_resolution(self):
                # Read dimensions only; do not resize the game window.
                self.resolution = self.connection.app_process_window.get_resolution(activate=False)
                self.check_screen_ratio(*self.resolution)
                self.ratio = self.resolution[0] / 1280

            def handle_resolution_dynamic_change(self):
                resolution = self.connection.app_process_window.get_resolution(activate=False)
                if resolution != self.resolution:
                    raise MissionStopped("Game resolution changed; restart after setting a stable size")

            def to_main_page(self, *args, **kwargs):
                raise MissionStopped("Home navigation is outside the extracted task")

            def solve(self, *args, **kwargs):
                raise MissionStopped("General BAAS task dispatch is disabled")

        try:
            # Bypass Main() and the regular client constructor: no Git updates,
            # old-log deletion, config rewriting, scheduler or other daily tasks.
            self.context = MissionContext(memory_config(root, profile), LogSignal())
            self.context.static_config = self.context.config_set.static_config
            self.context.flag_run = True
            for sig in (signal.SIGINT, signal.SIGTERM):
                self.previous_signals[sig] = signal.signal(sig, self._interrupt)
            client = BaasOcrClient.__new__(BaasOcrClient)
            client.exe_path = str(root / "core/ocr/baas_ocr_client/bin/BAAS_ocr_server.exe")
            client.config = ServerConfig()
            client.server_process = None
            if client.config.host not in ("localhost", "127.0.0.1"):
                raise MissionStopped("Only a local OCR server is supported")
            with socket.socket() as probe:
                if probe.connect_ex((client.config.host, int(client.config.port))) == 0:
                    raise MissionStopped("OCR port is occupied; close the other BAAS instance first")
            self.client = client
            ocr = Baas_ocr.__new__(Baas_ocr)
            ocr.logger, ocr.client = self.context.logger, client
            client.start_server()
            ocr.enable_thread_pool(2)
            ocr.init_model(["en-us"])
            from visual_profile import read_image
            test_image = read_image(root / "core/ocr/baas_ocr_client/bin/resource/ocr_models/test_images/en-us.png")
            ocr.ocr_for_single_line("en-us", log_info="test en-us", origin_image=test_image, pass_method=1)
            self.context.set_ocr(ocr)
            self.context.ocr_img_pass_method = 1  # Local PNG transfer; no shared-memory lifecycle.
            if not self.context.init_config() or not self.context.init_device():
                raise MissionStopped("BAAS game initialization failed")
            self.context.current_game_activity = None  # No stale event overlay/banner.
            if not self.context.init_image_resource():
                raise MissionStopped("Recognition resource initialization failed")
        except BaseException:
            self.close()
            raise

    def _interrupt(self, signum, frame):
        if self.context:
            self.context.flag_run = False
        raise KeyboardInterrupt("Stopped by signal")

    def ensure_running(self):
        if self.stop_file.exists() or (self.context and not self.context.flag_run):
            raise MissionStopped("Stopped by user")
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise MissionStopped("Stage transition timed out; stopped without retrying")

    def _co(self, **kwargs):
        # Small per-transition timeout; no fallback restart or blind clicking.
        return self.picture.co_detect(self.context, **dict({"time_out": 90}, **kwargs))

    def require_mission_list(self):
        self.context.update_screenshot_array()
        if not any(self.image.compare_image(self.context, "activity_mission-chosen-%d" % i)
                   for i in range(3)):
            raise MissionStopped("Open the event Quest/Mission list manually before starting")
        if not self.image.compare_image(self.context, "activity_menu"):
            raise MissionStopped("Event list layout is not recognized; no input sent")

    def inspect(self, number):
        self.deadline = time.monotonic() + 90
        self.require_mission_list()
        # Same bounded OCR search as BAAS, using this Chinese pack's geometry.
        # Do not call the upstream server-indexed helper: identifier and server
        # deliberately differ for a JP client with a Chinese UI.
        position = self.image.swipe_search_target_str(
            self.context, "activity_mission-enter-task-button", (1060, 143, 1195, 686),
            0.8, ["%02d" % i for i in range(1, 13)], target_str_index=number - 1,
            swipe_params=(907, 432, 907, 156, 0.5, 0.5), ocr_language="en-us",
            ocr_region_offsets=tuple(self.visual["ocr_region_offsets"]),
            ocr_str_replace_func=lambda text: text.replace("l", "1"),
            max_swipe_times=10, ocr_candidates="0123456789l", first_retry_dir=1)
        if position is None:
            raise MissionStopped("Cannot locate Quest %02d using Chinese entry-button templates" % number)
        self._co(img_ends="activity_task-info", img_reactions={
            "activity_menu": (1124, position[1] + 10)}, skip_first_screenshot=True)
        # Require the three actual star features; do not use the story/no-goals shortcut.
        return self.color.check_sweep_availability(self.context)

    def fight_current_team(self):
        self.deadline = time.monotonic() + 90
        self.context.update_screenshot_array()
        if not self.image.compare_image(self.context, "activity_task-info"):
            raise MissionStopped("Stage detail panel is not recognized")
        self._co(rgb_ends=["formation_edit%d" % i for i in range(1, 5)],
                 img_ends=["activity_formation", "activity_self-formation"],
                 img_reactions={"activity_task-info": (940, 538)})
        # Use the formation already selected in the game. Never edit students,
        # load a preset, buy AP or enter story/challenge stages.
        state = self._co(rgb_ends="fighting_feature", img_ends="normal_task_fight-confirm", img_reactions={
            "activity_formation": (1156, 659), "activity_self-formation": (1156, 659)},
            rgb_reactions={"formation_edit%d" % i: (1156, 659) for i in range(1, 5)})
        if state == "fighting_feature":
            self.context.update_screenshot_array()
            self.battle.set_acc_and_auto(self.context)

    def return_to_mission_list(self):
        self.deadline = time.monotonic() + 360
        self._co(time_out=360, img_ends="activity_menu", img_reactions={
            "activity_task-info": (1128, 141),
            "activity_fight-success-confirm": (640, 663),
            "normal_task_fight-confirm": (1168, 659),
            "normal_task_task-finish": (1038, 662),
            "normal_task_prize-confirm": (776, 655)})
        if self.image.compare_image(self.context, "activity_mission-not-chosen-0"):
            self.context.click(945, 110, duration=0.5, wait_over=True)
            self._co(img_ends=["activity_mission-chosen-%d" % i for i in range(3)])
        self.require_mission_list()

    def close(self):
        if self.context:
            self.context.flag_run = False
        if self.client and self.client.server_process:
            try:
                self.client.stop_server()
            except Exception:
                process = self.client.server_process
                if process and process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
        for sig, handler in self.previous_signals.items():
            signal.signal(sig, handler)
        self.previous_signals.clear()
