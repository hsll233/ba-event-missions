"""Bounded event Quest 01-12 workflow. No desktop or BAAS imports."""


class MissionStopped(RuntimeError):
    pass


def clear_missions(port, start=1, end=12, report=None):
    """Verify each stage, fight at most once, then verify three stars again.

    The port must confirm that the selected tab is Mission/Quest. Results
    stored on disk never replace a fresh in-game verification.
    """
    if not 1 <= start <= end <= 12:
        raise ValueError("Stage range must satisfy 1 <= start <= end <= 12")
    result = {"status": "running", "verified": [], "fought": [], "current": None}

    def publish():
        if report:
            report(result)

    try:
        port.require_mission_list()
        for number in range(start, end + 1):
            result["current"] = number
            publish()
            state = port.inspect(number)
            if state not in ("sss", "pass", "no-pass"):
                raise MissionStopped("Quest %02d: unrecognized stage status" % number)
            if state != "sss":
                result["fought"].append(number)
                publish()
                port.fight_current_team()
                port.return_to_mission_list()
                if port.inspect(number) != "sss":
                    raise MissionStopped(
                        "Quest %02d: three stars not verified; stopped without retrying" % number
                    )
            result["verified"].append(number)
            port.return_to_mission_list()
            publish()
        result.update(status="complete", current=None)
        publish()
        return result
    except BaseException as exc:
        result.update(status="stopped", error=str(exc) or type(exc).__name__)
        publish()
        raise
