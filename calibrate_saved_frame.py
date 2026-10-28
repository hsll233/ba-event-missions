"""Calibrate only explicitly named features from a manually inspected game frame."""
import hashlib
import json
import shutil
import site
import sys
from pathlib import Path
BASE = Path(__file__).resolve().parent
settings = json.loads((BASE / "settings.json").read_text(encoding="utf-8"))
site.addsitedir(str((BASE / settings["baas_root"]).resolve() / ".venv/Lib/site-packages"))
import cv2
label, *names = sys.argv[1:]
saved = BASE / "output" / (label + ".png")
shutil.copy2(BASE / "output/probe-game.png", saved)
frame = cv2.imread(str(saved))
path = BASE / settings["visual_profile"]
data = json.loads(path.read_text(encoding="utf-8"))
for name in names:
    item = data["features"][name]
    x1, y1, x2, y2 = item["area"]
    target = BASE / item["file"]
    cv2.imwrite(str(target), frame[y1:y2, x1:x2])
    for linked in data["features"].values():
        if linked["file"] == item["file"]:
            linked.update(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                          source="local_game_capture/" + saved.name, source_language="zh-CN")
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Calibrated: " + ", ".join(names))
