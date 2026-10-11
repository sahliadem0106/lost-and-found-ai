"""The Brain's search loop: Map says where/when to look, Eyes look, repeat.

Steps follow demo/graph-tracking-method.md:
  anchor -> trace the family backwards -> find the separation -> trace the child
  forwards (zone sweep as fallback) -> where the child is now.
"""
from dataclasses import dataclass, field

from .eyes import Hit
from .topology import SLACK_S

SEGMENT_S = 16        # CreativAI analyses video in ~16 s segments
BLIND_SPOT_PENALTY = 0.5
ENTRANCE_BONUS = 1.0
MIN_SCORE = 0.15


@dataclass
class Path:
    hits: list
    score: float = 0.0

    @property
    def last(self):
        return self.hits[-1]


def _same(a, b):
    return a.camera == b.camera and a.start == b.start and a.end == b.end


def _extend(eyes, query, hit, forward):
    """Grow a sighting along its own camera (needed when the Eyes return short segments)."""
    while True:
        t0, t1 = (hit.end, hit.end + SEGMENT_S) if forward else (hit.start - SEGMENT_S, hit.start)
        more = [h for h in eyes.search(query, hit.camera, t0, t1)
                if (h.end > hit.end if forward else h.start < hit.start) and h.score >= MIN_SCORE]
        if not more:
            return hit
        h = more[0]
        hit = Hit(hit.camera, min(hit.start, h.start), max(hit.end, h.end), max(hit.score, h.score), hit.ref)


def _candidates(topo, eyes, query, hit, who, forward, hop_targets, penalty, verify):
    out = []
    for cam, dist in hop_targets:
        lo, hi = topo.transit_window(dist, who)
        if forward:
            t0, t1 = hit.end + lo, hit.end + hi
        else:
            t0, t1 = hit.start - hi, hit.start - lo
        for h in eyes.search(query, cam, t0, t1):
            dt = (h.start - hit.end) if forward else (hit.start - h.end)
            if dt < -SLACK_S:
                continue  # can't be in two cameras at once
            p = topo.plausibility(dist, max(dt, 0.0), who)
            if p <= 0:
                continue
            score = h.score * p * penalty
            if verify:
                score *= eyes.ask(verify, h.camera, h.start, h.end)
            if score >= MIN_SCORE:
                out.append((score, _extend(eyes, query, h, forward)))
    return out


def trace(topo, eyes, query, anchor, who, forward, beam=3, max_steps=30, verify=None):
    """Beam search over the camera graph from `anchor`. Returns paths in time order, best first."""
    live = [Path([anchor], anchor.score)]
    done = []
    for _ in range(max_steps):
        nxt = []
        for p in live:
            cur = p.last
            one_hop = list(topo.neighbours(cur.camera).items())
            cands = _candidates(topo, eyes, query, cur, who, forward, one_hop, 1.0, verify)
            if not cands:  # blind spot: allow a two-hop jump with a wider window
                two_hop = [(c, topo.dist(cur.camera, c)) for c, h in topo.within_hops(cur.camera, 2).items()
                           if h == 2]
                cands = _candidates(topo, eyes, query, cur, who, forward, two_hop, BLIND_SPOT_PENALTY, verify)
            cands = [(s, h) for s, h in cands if not any(_same(h, x) for x in p.hits)]
            if not cands:
                done.append(p)
                continue
            for s, h in cands:
                nxt.append(Path(p.hits + [h], p.score + s))
        if not nxt:
            break
        nxt.sort(key=lambda p: -p.score)
        live = nxt[:beam]
    done.extend(live if nxt else [])

    def rank(p):
        bonus = ENTRANCE_BONUS if not forward and topo.cameras[p.last.camera].zone == "entrance" else 0
        return p.score + bonus

    done.sort(key=lambda p: -rank(p))
    for p in done:
        if not forward:
            p.hits.reverse()
    return done


@dataclass
class Separation:
    camera: str
    time: float
    last_with: Hit
    first_without: Hit
    hit: Hit = None


def find_separation(eyes, family_path, moment_query):
    """Q2 per sighting, refine the boundary in segments, then Q3 to pin the second."""
    answers = [(h, eyes.ask("with_child", h.camera, h.start, h.end)) for h in family_path]
    last_yes = max((i for i, (_, p) in enumerate(answers) if p >= 0.5), default=None)
    if last_yes is None or last_yes == len(answers) - 1:
        return None
    # The boundary is inside the last "yes" sighting, the first "no" one, or the walk between.
    span = family_path[last_yes:last_yes + 2]
    segs = []
    for h in span:
        t = h.start
        while t < h.end:
            e = min(t + SEGMENT_S, h.end)
            segs.append((h.camera, t, e, eyes.ask("with_child", h.camera, t, e)))
            t = e
    yes = [s for s in segs if s[3] >= 0.5]
    no = [s for s in segs if s[3] < 0.5 and (not yes or s[1] >= yes[-1][2])]
    lw, fw = (yes[-1] if yes else segs[0]), no[0]
    best = None
    for cam in dict.fromkeys([lw[0], fw[0]]):
        for h in eyes.search(moment_query, cam, lw[1], fw[2]):
            if best is None or h.score > best.score:
                best = h
    cam, t = (best.camera, best.start) if best else (fw[0], fw[1])
    return Separation(cam, t, Hit(lw[0], lw[1], lw[2], lw[3]), Hit(fw[0], fw[1], fw[2], fw[3]), best)


def zone_sweep(topo, eyes, query, origin_cam, t_from, t_to, who):
    """Search every camera the child could have walked to since the separation; keep hits where
    the child is alone and got there at a possible speed. Latest sighting first."""
    hits = []
    for cam in topo.cameras:
        dist = topo.dist(origin_cam, cam)
        lo, _ = topo.transit_window(dist, who)
        if t_from + lo > t_to:
            continue  # too far to reach by now
        for h in eyes.search(query, cam, t_from + lo, t_to):
            s = h.score * eyes.ask("alone", h.camera, h.start, h.end)
            if s >= MIN_SCORE:
                hits.append(Hit(h.camera, h.start, h.end, s, h.ref))
    return sorted(hits, key=lambda h: (-h.end, -h.score))


@dataclass
class CaseResult:
    anchor: Hit
    family_path: list
    separation: Separation
    child_path: list = field(default_factory=list)
    child_now: Hit = None
    still_there: bool = False
    next_likely: list = field(default_factory=list)


def run_case(topo, eyes, family_query, child_query, moment_query, report_cam, now, lookback=120):
    # 1. Anchor: the family at the desk camera right now.
    found = eyes.search(family_query, report_cam, now - lookback, now)
    if not found:
        raise RuntimeError(f"family not found at {report_cam}")
    anchor = _extend(eyes, family_query, _extend(eyes, family_query, found[0], False), True)

    # 2. Parents' path, backwards through the graph.
    family_path = trace(topo, eyes, family_query, anchor, "adult", forward=False)[0].hits

    # 3. Separation moment.
    sep = find_separation(eyes, family_path, moment_query)
    res = CaseResult(anchor, family_path, sep)
    if sep is None:
        return res

    # 4. Child forwards from the separation; zone sweep if the trace goes nowhere.
    start = sep.hit or Hit(sep.camera, sep.time, sep.time, 1.0)
    paths = trace(topo, eyes, child_query, start, "child", forward=True, verify="alone")
    child_path = paths[0].hits if paths else [start]
    if len(child_path) == 1:
        swept = zone_sweep(topo, eyes, child_query, sep.camera, sep.time, now, "child")
        if swept:
            child_path = [start, swept[0]]
    res.child_path = child_path
    res.child_now = child_path[-1]
    res.still_there = res.child_now.end >= now - SEGMENT_S
    res.next_likely = sorted(topo.neighbours(res.child_now.camera), key=topo.neighbours(res.child_now.camera).get)
    return res
