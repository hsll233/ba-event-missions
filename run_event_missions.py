"""Default is offline checking. Only --run can initialize the game backend."""
import argparse
import json
import logging
import os
import site
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # Support BAAS's isolated embedded Python (_pth).
from mission_flow import clear_missions
from visual_profile import read_profile


def read_settings():
    settings = json.loads((HERE / "settings.json").read_text(encoding="utf-8"))
    settings["baas_root"] = str((HERE / settings["baas_root"]).resolve())
    return settings


def check_files(settings):
    root = Path(settings["baas_root"])
    profile = root / "config" / settings["profile"] / "config.json"
    required = [root / p for p in (
        "core/Baas_thread.py", "module/activities/activity_utils.py", "config/static.json",
        "core/ocr/baas_ocr_client/bin/BAAS_ocr_server.exe",
        "core/ocr/baas_ocr_client/bin/config/global_setting.json", "src/rgb_feature/JP.json",
        ".env/python.exe", ".venv/Lib/site-packages")]
    missing = [str(p) for p in required + [profile] if not p.exists()]
    if missing:
        raise RuntimeError("Missing installed files: " + ", ".join(missing))
    data = json.loads(profile.read_text(encoding="utf-8"))
    if data["server"] != "日服PC端":
        raise RuntimeError("Expected the local JP PC profile")
    return root, profile


def main(argv=None):
    parser = argparse.ArgumentParser(description="Event Mission/Quest 01-12 only; default: offline check")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Offline file/config check only (default)")
    mode.add_argument("--verify-libraries", action="store_true", help="Offline imports/template check; no game access")
    mode.add_argument("--run", action="store_true", help="Manually opt in to BAAS game automation")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=12)
    parser.add_argument("--resume-results", action="store_true", help="Finish an interrupted event result screen before checking stages")
    args = parser.parse_args(argv)
    if not 1 <= args.start <= args.end <= 12:
        parser.error("Range must satisfy 1 <= start <= end <= 12")
    settings = read_settings()
    root, profile = check_files(settings)
    visual_path = HERE / settings["visual_profile"]
    visual = read_profile(visual_path)
    plan = {"mode": "offline_check", "baas_root": str(root), "server": "JP PC",
            "task": "event_mission_only", "stages": list(range(args.start, args.end + 1)),
            "team": "current_in_game_formation", "max_attempts_per_stage": 1,
            "ui_language": visual["ui_language"], "active_template_source": "CN",
            "visual_profile": str(visual_path), "japanese_templates_active": 0,
            "game_automation_started": False, "current_event_live_verified": False}
    if not args.run and not args.verify_libraries:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    site.addsitedir(str(root / ".venv/Lib/site-packages"))
    sys.path.insert(0, str(root))
    os.chdir(root)
    from baas_bridge import BaasMissionPort, verify_libraries
    if args.verify_libraries:
        plan.update(verify_libraries(root, visual_path))
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    output = HERE / "output"
    output.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(output / "run.log", encoding="utf-8"),
                                  logging.StreamHandler()])

    def report(result):
        temp = output / "result.tmp"
        temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        temp.replace(output / "result.json")

    port = None
    report({"status": "initializing", "verified": [], "fought": [], "current": None})
    try:
        port = BaasMissionPort(root, profile, output, visual_path)
        if args.resume_results:
            port.return_to_mission_list()
        result = clear_missions(port, args.start, args.end, report)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except BaseException as exc:
        previous = json.loads((output / "result.json").read_text(encoding="utf-8"))
        previous.update(status="stopped", error=str(exc) or type(exc).__name__)
        report(previous)
        logging.error("Stopped: %s", exc)
        return 1
    finally:
        if port:
            port.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
