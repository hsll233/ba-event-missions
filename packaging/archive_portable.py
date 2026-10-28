"""Archive the portable folder without machine/test session artifacts."""
import json
import argparse
import zipfile
from pathlib import Path

parser = argparse.ArgumentParser(description="Archive a portable bundle without session data")
parser.add_argument("--folder", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
folder = args.folder.resolve()
archive = args.output.resolve()
if archive.exists():
    raise SystemExit("Archive exists; preserve it and select a new version")

excluded = {"launcher-check.json", "launcher-check.log", "STOP"}
count = 0
with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
    for file in sorted(folder.rglob("*")):
        if not file.is_file():
            continue
        relative = file.relative_to(folder)
        if "__pycache__" in relative.parts or file.suffix == ".pyc" or file.name in excluded:
            continue
        if relative.as_posix().startswith(("app/output/", "engine/core/ocr/baas_ocr_client/bin/output/")):
            continue
        output.write(file, (Path(folder.name) / relative).as_posix())
        count += 1
with zipfile.ZipFile(archive) as verification:
    broken = verification.testzip()
    if broken:
        raise RuntimeError("Archive CRC failure: " + broken)
print(json.dumps({"archive": str(archive), "size_mb": round(archive.stat().st_size / 1024**2, 1),
                  "files": count, "crc_check": "passed"}, ensure_ascii=False, indent=2))
