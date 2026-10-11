"""Tests on Case A only (Case B is the sealed blind test).  Run: python3 -m unittest demo.engine.test_engine"""
import copy
import unittest

from .eyes import Hit, SimEyes
from .run_case import QUERIES, SIM_SIMILARITY
from .topology import Topology, parse_t
from .tracker import SEGMENT_S, run_case, zone_sweep

TOPO = Topology.load()
CASE_A = TOPO.data["cases"]["A"]
Q = QUERIES["A"]
NOW = parse_t(Q["now"])


class SegmentEyes(SimEyes):
    """Like CreativAI: hits come back as ~16 s segments, not whole sightings."""

    def search(self, query, camera, t0, t1):
        out = []
        for h in super().search(query, camera, t0, t1):
            t = h.start
            while t < h.end:
                e = min(t + SEGMENT_S, h.end)
                if t <= t1 and e >= t0:
                    out.append(Hit(h.camera, t, e, h.score, h.ref))
                t = e
        return out


def solve(case=CASE_A, eyes_cls=SimEyes, sims=SIM_SIMILARITY):
    eyes = eyes_cls(case, {Q[k]: v for k, v in sims.items()}, until=NOW)
    return run_case(TOPO, eyes, Q["family"], Q["child"], Q["moment"], Q["report_cam"], NOW)


class TopologyTests(unittest.TestCase):
    def test_windows_and_plausibility(self):
        lo, hi = TOPO.transit_window(25, "adult")
        self.assertLess(lo, 25 / 1.8)
        self.assertGreater(hi, 25 / 0.6)
        self.assertGreater(TOPO.plausibility(25, 20, "adult"), 0.5)
        self.assertEqual(TOPO.plausibility(25, 2, "adult"), 0.0)     # 12 m/s: impossible
        self.assertEqual(TOPO.plausibility(25, 300, "adult"), 0.0)   # far too slow for one hop

    def test_distances(self):
        self.assertEqual(TOPO.dist("STR-B", "FC-02"), 20 + 25 + 18 + 12)
        self.assertEqual(TOPO.within_hops("FC-02", 2), {"FC-02": 0, "FC-01": 1, "COR-W": 2})

    def test_story_timeline_is_walkable(self):
        for track, who in (("family", "adult"), ("child", "child")):
            rows = CASE_A[track]
            for a, b in zip(rows, rows[1:]):
                dt = parse_t(b[1]) - parse_t(a[2])
                self.assertGreater(TOPO.plausibility(TOPO.dist(a[0], b[0]), dt, who), 0, (a, b))


class CaseATests(unittest.TestCase):
    def check(self, res):
        self.assertEqual([h.camera for h in res.family_path], [r[0] for r in CASE_A["family"]])
        self.assertEqual(res.separation.camera, "STR-B")
        self.assertLessEqual(abs(res.separation.time - parse_t("14:19:10")), 3)
        self.assertEqual([h.camera for h in res.child_path], [r[0] for r in CASE_A["child"]])
        self.assertEqual(res.child_now.camera, "FC-02")
        self.assertTrue(res.still_there)

    def test_whole_sightings(self):
        self.check(solve())

    def test_segmented_hits(self):
        self.check(solve(eyes_cls=SegmentEyes))

    def test_blind_spot_two_hop_jump(self):
        case = copy.deepcopy(CASE_A)
        case["child"] = [r for r in case["child"] if r[0] != "COR-W"]  # camera was down
        res = solve(case)
        self.assertEqual([h.camera for h in res.child_path], ["STR-B", "ATR-01", "FC-01", "FC-02"])
        self.assertEqual(res.child_now.camera, "FC-02")

    def test_lookalike_decoy_rejected_by_sweep(self):
        eyes = SimEyes(CASE_A, {Q[k]: v for k, v in SIM_SIMILARITY.items()}, until=parse_t("14:25:00"))
        hits = zone_sweep(TOPO, eyes, Q["child"], "STR-B", parse_t("14:19:10"), parse_t("14:25:00"), "child")
        self.assertNotIn("decoy0#0", [h.ref for h in hits])
        self.assertEqual(hits[0].camera, "FC-02")

    def test_no_separation_when_child_always_with_family(self):
        case = copy.deepcopy(CASE_A)
        case["family"] = [r[:3] + ["with_child"] for r in case["family"]]
        res = solve(case)
        self.assertIsNone(res.separation)


if __name__ == "__main__":
    unittest.main()
