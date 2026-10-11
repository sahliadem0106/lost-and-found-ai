#!/usr/bin/env python3
"""Run the Map + Brain loop on a case with simulated Eyes (ground truth from mall_topology.json).

Usage:  python3 -m demo.engine.run_case A [--json out.json]

Case B is the blind test (demo/test-plan.md): it stays sealed until the code is
frozen, so this script refuses to run it unless --unseal is given.
"""
import argparse
import json
import sys

from .eyes import SimEyes
from .topology import Topology, fmt_t, parse_t
from .tracker import run_case

QUERIES = {
    "A": {
        "family": "a man in a long white robe (thobe) with a red-and-white checkered headscarf (shemagh) "
                  "carrying a dark green shopping bag, and a woman in a long black cloak (abaya) with a "
                  "light grey headscarf",
        "child": "a small boy of about 6 in a bright red t-shirt, blue jeans and white sneakers, alone, "
                 "with no adult next to them",
        "moment": "a small child walking away alone while the parents are busy and do not notice",
        "report_cam": "INF-01",
        "now": "14:27:00",
    },
}

# How the simulated Eyes rate each ground-truth track for each query. The decoy is
# a lookalike family, so it matches both queries fairly well: the Map and the
# "is the child alone?" question have to reject it.
SIM_SIMILARITY = {
    "family": {"family": 0.9, "decoy0": 0.6},
    "child": {"child": 0.9, "decoy0": 0.75},
    "moment": {"child": 0.8},
}


def describe(res, topo):
    name = lambda c: f"{c} ({topo.cameras[c].name})"
    lines = ["Parents' path:"]
    for h in res.family_path:
        lines.append(f"  {fmt_t(h.start)}–{fmt_t(h.end)}  {name(h.camera)}")
    s = res.separation
    if s is None:
        lines.append("No separation found: the child is with the parents in every sighting.")
        return "\n".join(lines)
    lines.append(f"Separation: {name(s.camera)} at {fmt_t(s.time)}")
    lines.append("Child's path:")
    for h in res.child_path:
        lines.append(f"  {fmt_t(h.start)}–{fmt_t(h.end)}  {name(h.camera)}")
    now = res.child_now
    where = "still there" if res.still_there else f"last seen {fmt_t(now.end)}"
    lines.append(f"Child now: {name(now.camera)}, {where}. If moving: {', '.join(res.next_likely)}")
    return "\n".join(lines)


def to_json(res):
    hit = lambda h: {"camera": h.camera, "start": fmt_t(h.start), "end": fmt_t(h.end), "score": round(h.score, 3)}
    s = res.separation
    return {
        "family_path": [hit(h) for h in res.family_path],
        "separation": s and {"camera": s.camera, "time": fmt_t(s.time)},
        "child_path": [hit(h) for h in res.child_path],
        "child_now": res.child_now and {**hit(res.child_now), "still_there": res.still_there,
                                        "next_likely": res.next_likely},
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--json")
    ap.add_argument("--unseal", action="store_true", help="allow the blind-test case")
    a = ap.parse_args(argv)

    topo = Topology.load()
    case = topo.data["cases"][a.case]
    if case.get("blind_test") and not a.unseal:
        sys.exit(f"Case {a.case} is the sealed blind test; see demo/test-plan.md.")
    q = QUERIES[a.case]
    now = parse_t(q["now"])
    eyes = SimEyes(case, {q[k]: v for k, v in SIM_SIMILARITY.items()}, until=now)
    res = run_case(topo, eyes, q["family"], q["child"], q["moment"], q["report_cam"], now)

    print(describe(res, topo))
    exp = case["expected"]
    ok_sep = res.separation and res.separation.camera == exp["separation"][0] \
        and abs(res.separation.time - parse_t(exp["separation"][1])) <= 3
    ok_now = res.child_now and res.child_now.camera == exp["child_now"]
    print(f"\nExpected separation {exp['separation'][0]} {exp['separation'][1]}: {'PASS' if ok_sep else 'FAIL'}")
    print(f"Expected child now {exp['child_now']}: {'PASS' if ok_now else 'FAIL'}")
    print(f"Eyes calls: {sum(c[0] == 'search' for c in eyes.calls)} searches, "
          f"{sum(c[0] == 'ask' for c in eyes.calls)} questions")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(to_json(res), f, indent=2)
    return 0 if ok_sep and ok_now else 1


if __name__ == "__main__":
    sys.exit(main())
