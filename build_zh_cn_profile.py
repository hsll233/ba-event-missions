"""Extract real CN PNG templates; never translate/render Japanese images."""
import ast
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

FEATURES = (
    "activity_menu", "activity_task-info", "activity_mission-enter-task-button",
    "activity_mission-chosen-0", "activity_mission-chosen-1",
    "activity_formation", "activity_self-formation", "activity_fight-success-confirm",
    "normal_task_fight-confirm", "normal_task_fail-confirm", "normal_task_task-finish",
    "normal_task_prize-confirm", "purchase_ap_notice", "purchase_ap_notice-localized",
)
RGB_KEYS = (
    "loadingNotWhite", "loadingWhite", "reward_acquired", "relationship_rank_up", "level_up",
    "formation_edit1", "formation_edit2", "formation_edit3", "formation_edit4",
    "fighting_feature", "sideTaskNoPass", "sideTaskSSS",
)


def extract(root):
    root = Path(root)
    cn = root / "src/images/CN"
    metadata = {}
    for source in (cn / "x_y_range").glob("*.py"):
        values = {}
        for node in ast.parse(source.read_text(encoding="utf-8-sig")).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                name = getattr(node.targets[0], "id", "")
                if name in ("prefix", "path", "x_y_range"):
                    values[name] = ast.literal_eval(node.value)
        for name, area in values.get("x_y_range", {}).items():
            key = values["prefix"] + "_" + name
            if key in FEATURES:
                metadata[key] = (cn / values["path"] / (name + ".png"), area)
    if set(FEATURES) != set(metadata):
        raise ValueError("CN templates missing: " + str(set(FEATURES) - set(metadata)))
    destination = HERE / "assets/zh-CN"
    destination.mkdir(parents=True, exist_ok=True)
    features = {}
    for key in FEATURES:
        source, area = metadata[key]
        target = destination / (key + ".png")
        shutil.copy2(source, target)
        features[key] = {"file": target.relative_to(HERE).as_posix(), "area": list(area),
                         "source": source.relative_to(root).as_posix(),
                         "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    # JP's third tab layout has its center at x=811. Use the same Chinese
    # highlighted word image there, with its actual 60x38 dimensions.
    features["activity_mission-chosen-2"] = dict(features["activity_mission-chosen-0"],
                                               area=[781, 89, 841, 127])
    rgb = json.loads((root / "src/rgb_feature/JP.json").read_text(encoding="utf-8"))["rgb_feature"]
    profile = {"identifier": "JP_zh_cn", "ui_language": "zh-CN", "backend_server": "JP",
               "template_source": "CN", "rgb_layout": "JP",
               "mission_number_ocr": "en-us", "ocr_region_offsets": [-384, -8, 43, 28],
               "features": features, "rgb_feature": {key: rgb[key] for key in RGB_KEYS}}
    path = HERE / "visual.zh-CN.json"
    path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Extracted %d Chinese PNG files (%d feature positions)" % (len(FEATURES), len(features)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract a baseline CN template pack; backs up your calibrated pack first")
    parser.add_argument("--baas-root", required=True, type=Path)
    args = parser.parse_args()
    if (HERE / "visual.zh-CN.json").exists():
        raise SystemExit("Existing calibrated pack detected; extract in a fresh project folder")
    extract(args.baas_root)
