"""Offline behavior tests; fake port, never initializes BAAS or a desktop."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mission_flow import MissionStopped, clear_missions


class FakePort:
    def __init__(self, states=None, win=True, mission_tab=True):
        self.states = dict(states or {})
        self.win, self.mission_tab = win, mission_tab
        self.number = None
        self.calls = []

    def require_mission_list(self):
        self.calls.append(("require_mission",))
        if not self.mission_tab:
            raise MissionStopped("Wrong tab")

    def inspect(self, number):
        self.calls.append(("inspect", number))
        self.number = number
        return self.states.get(number, "no-pass")

    def fight_current_team(self):
        self.calls.append(("fight", self.number))
        self.states[self.number] = "sss" if self.win else "pass"

    def return_to_mission_list(self):
        self.calls.append(("return_mission",))


class MissionTests(unittest.TestCase):
    def test_all_twelve_verified_after_one_battle_each(self):
        port = FakePort()
        result = clear_missions(port)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["verified"], list(range(1, 13)))
        self.assertEqual(result["fought"], list(range(1, 13)))
        self.assertEqual(sum(c[0] == "inspect" for c in port.calls), 24)

    def test_existing_three_stars_are_skipped(self):
        port = FakePort({i: "sss" for i in range(1, 13)})
        result = clear_missions(port)
        self.assertEqual(result["fought"], [])
        self.assertFalse(any(c[0] == "fight" for c in port.calls))

    def test_one_star_clear_does_not_count_as_success_or_retry(self):
        port = FakePort({1: "sss"}, win=False)
        reports = []
        with self.assertRaises(MissionStopped):
            clear_missions(port, report=lambda r: reports.append({k: v[:] if isinstance(v, list) else v
                                                               for k, v in r.items()}))
        self.assertEqual(reports[-1]["status"], "stopped")
        self.assertEqual(reports[-1]["verified"], [1])
        self.assertEqual(reports[-1]["fought"], [2])
        self.assertNotIn(("inspect", 3), port.calls)
        self.assertEqual(port.calls.count(("fight", 2)), 1)

    def test_unknown_recognition_sends_no_battle(self):
        port = FakePort({1: "unknown"})
        with self.assertRaises(MissionStopped):
            clear_missions(port)
        self.assertFalse(any(c[0] == "fight" for c in port.calls))

    def test_story_or_challenge_tab_stops_before_opening_stage(self):
        port = FakePort(mission_tab=False)
        with self.assertRaises(MissionStopped):
            clear_missions(port)
        self.assertEqual(port.calls, [("require_mission",)])

    def test_resume_range_still_verifies_live_status(self):
        port = FakePort({10: "sss"})
        result = clear_missions(port, 10, 12)
        self.assertEqual(result["verified"], [10, 11, 12])
        self.assertEqual(result["fought"], [11, 12])
        self.assertNotIn(("inspect", 9), port.calls)

    def test_cancellation_stops_before_next_stage(self):
        class CancelPort(FakePort):
            def fight_current_team(self):
                raise KeyboardInterrupt("test cancellation")
        reports = []
        with self.assertRaises(KeyboardInterrupt):
            clear_missions(CancelPort(), report=lambda r: reports.append(dict(r)))
        self.assertEqual(reports[-1]["status"], "stopped")
        self.assertEqual(reports[-1]["verified"], [])

    def test_invalid_range_has_no_port_interactions(self):
        for start, end in ((0, 12), (1, 13), (5, 4)):
            port = FakePort()
            with self.assertRaises(ValueError):
                clear_missions(port, start, end)
            self.assertEqual(port.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
