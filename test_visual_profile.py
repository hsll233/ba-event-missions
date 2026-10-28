"""Offline language regressions using the distributed PNGs, no game capture."""
import json
import logging
import os
import site
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from visual_profile import read_profile, install_profile, read_image

SETTINGS = json.loads((HERE / "settings.json").read_text(encoding="utf-8"))
ROOT = (HERE / SETTINGS["baas_root"]).resolve()
site.addsitedir(str(ROOT / ".venv/Lib/site-packages"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
import cv2
import numpy as np
from core import image, position
from baas_bridge import memory_config


class VisualProfileTests(unittest.TestCase):
    def setUp(self):
        self.context = SimpleNamespace(ratio=1.0)
        self.profile = install_profile(self.context, HERE / SETTINGS["visual_profile"])

    def test_active_pack_uses_only_real_cn_png_files(self):
        self.assertEqual(self.context.identifier, "JP_zh_cn")
        self.assertEqual(len(position.image_dic[self.context.identifier]), len(self.profile["features"]))
        for item in self.profile["features"].values():
            self.assertTrue(item["source"].startswith("src/images/CN/") or
                            item.get("source_language") == "zh-CN")
            self.assertIn("assets/zh-CN/", item["file"])

    def test_visual_language_does_not_change_game_server(self):
        config = memory_config(ROOT, ROOT / "config/default_config/config.json")
        self.assertEqual(config.config.server, "日服PC端")
        self.assertEqual(config.server_mode, "JP")
        self.assertEqual(self.profile["ui_language"], "zh-CN")
        self.assertEqual(self.profile["rgb_layout"], "JP")

    def test_old_japanese_namespace_is_not_reused(self):
        sentinel = object()
        position.image_dic["JP"] = {"sentinel": sentinel}
        install_profile(self.context, HERE / SETTINGS["visual_profile"])
        self.assertEqual(set(position.image_dic[self.context.identifier]), set(self.profile["features"]))
        self.assertNotIn("sentinel", position.image_dic[self.context.identifier])
        self.assertIs(position.image_dic["JP"]["sentinel"], sentinel)

    def test_japanese_labels_do_not_match_chinese_pack(self):
        cases = (
            ("activity_task-info", "activity/common/task-info.png", (578, 124, 702, 153)),
            ("activity_mission-chosen-0", "activity/common/mission-chosen-0.png", (901, 89, 987, 127)),
            ("activity_formation", "activity/common/unit-formation.png", (102, 10, 200, 40)),
        )
        for key, source, box in cases:
            with self.subTest(feature=key):
                frame = np.full((720, 1280, 3), 245, dtype=np.uint8)
                original = ROOT / "src/images/JP" / source
                fixture = HERE / "tests/fixtures/JP" / source
                jp = read_image(original if original.exists() else fixture)
                self.assertIsNotNone(jp)
                frame[box[1]:box[3], box[0]:box[2]] = jp
                self.context.latest_img_array = frame
                self.assertFalse(image.compare_image(self.context, key))

    def test_chinese_label_survives_same_small_jpeg_and_scale_changes_as_game_capture(self):
        # Use encoded screenshots at both supported sample sizes, rather than
        # just checking filenames or comparing the PNG bytes to themselves.
        for scale in (1, 2):
            for key in ("activity_task-info", "activity_mission-chosen-0", "activity_formation"):
                with self.subTest(scale=scale, feature=key):
                    frame = np.full((720, 1280, 3), 245, dtype=np.uint8)
                    box = self.profile["features"][key]["area"]
                    frame[box[1]:box[3], box[0]:box[2]] = position.image_dic[self.context.identifier][key]
                    frame = cv2.resize(frame, (1280 * scale, 720 * scale))
                    success, data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                    self.assertTrue(success)
                    self.context.latest_img_array = cv2.imdecode(data, cv2.IMREAD_COLOR)
                    self.context.ratio = scale
                    self.assertTrue(image.compare_image(self.context, key))


if __name__ == "__main__":
    unittest.main(verbosity=2)
