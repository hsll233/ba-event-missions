"""Language-specific PNG/coordinate pack, independent of the game's server."""
import hashlib
import json
from pathlib import Path


def read_profile(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["ui_language"] != "zh-CN" or data["template_source"] != "CN":
        raise ValueError("This entry requires real Simplified Chinese templates")
    if data["backend_server"] != "JP":
        raise ValueError("The JP PC backend must stay separate from the visual language")
    base = path.parent
    for name, item in data["features"].items():
        target = (base / item["file"]).resolve()
        if base not in target.parents:
            raise ValueError("Template path is outside the extracted package: " + name)
        if not (item["source"].startswith("src/images/CN/") or
                (item["source"].startswith("local_game_capture/") and item.get("source_language") == "zh-CN")):
            raise ValueError("Non-Chinese template source: " + name)
        if hashlib.sha256(target.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("Template checksum mismatch: " + name)
        x1, y1, x2, y2 = item["area"]
        if not (0 <= x1 < x2 <= 1280 and 0 <= y1 < y2 <= 720):
            raise ValueError("Invalid template coordinates: " + name)
    return data


def install_profile(context, path):
    """Replace the complete active feature namespace; no Japanese-image fallback."""
    import cv2
    from core import position
    path = Path(path).resolve()
    profile = read_profile(path)
    pictures, coordinates = {}, {}
    for name, item in profile["features"].items():
        picture = read_image(path.parent / item["file"])
        area = item["area"]
        if picture is None or picture.shape[:2] != (area[3] - area[1], area[2] - area[0]):
            raise ValueError("Template image/coordinate size mismatch: " + name)
        prefix, suffix = name.rsplit("_", 1)
        pictures[name] = picture
        coordinates.setdefault(prefix, {})[suffix] = tuple(area)
    identifier = profile["identifier"]
    position.image_dic[identifier] = pictures
    position.image_x_y_range[identifier] = coordinates
    position.initialized_image[identifier] = True
    context.identifier = identifier
    context.rgb_feature = profile["rgb_feature"]
    return profile


def read_image(path):
    """OpenCV's Windows filename API cannot reliably open Chinese paths."""
    import cv2
    import numpy as np
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
