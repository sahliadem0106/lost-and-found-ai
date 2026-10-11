"""The Map: camera graph, walking-time windows and path plausibility. No AI."""
import heapq
import json
import math
from dataclasses import dataclass
from pathlib import Path

DEFAULT_TOPOLOGY = Path(__file__).resolve().parent.parent / "mall_topology.json"

# A camera sees a few metres of floor around its node, so a walk between two
# cameras can look a little shorter or longer than the walkway length.
SLACK_S = 8.0


def parse_t(s):
    """'14:19:10' -> seconds since midnight."""
    h, m, *sec = (int(x) for x in s.split(":"))
    return h * 3600 + m * 60 + (sec[0] if sec else 0)


def fmt_t(t):
    t = int(round(t))
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


@dataclass(frozen=True)
class Camera:
    id: str
    name: str
    zone: str
    pos: tuple


class Topology:
    def __init__(self, data):
        self.data = data
        self.cameras = {c["id"]: Camera(c["id"], c["name"], c["zone"], tuple(c["pos"]))
                        for c in data["cameras"]}
        self.adj = {cid: {} for cid in self.cameras}
        for e in data["edges"]:
            self.adj[e["a"]][e["b"]] = e["dist_m"]
            self.adj[e["b"]][e["a"]] = e["dist_m"]
        self.speeds = data["walking_speed_mps"]
        self._dist = {c: self._dijkstra(c) for c in self.cameras}

    @classmethod
    def load(cls, path=DEFAULT_TOPOLOGY):
        return cls(json.loads(Path(path).read_text()))

    def _dijkstra(self, src):
        dist = {src: 0.0}
        heap = [(0.0, src)]
        while heap:
            d, c = heapq.heappop(heap)
            if d > dist[c]:
                continue
            for n, w in self.adj[c].items():
                if d + w < dist.get(n, math.inf):
                    dist[n] = d + w
                    heapq.heappush(heap, (d + w, n))
        return dist

    def dist(self, a, b):
        return self._dist[a].get(b, math.inf)

    def neighbours(self, cam):
        return self.adj[cam]

    def within_hops(self, cam, hops):
        """Cameras reachable in at most `hops` edges (including cam itself)."""
        seen, frontier = {cam: 0}, [cam]
        for h in range(1, hops + 1):
            nxt = []
            for c in frontier:
                for n in self.adj[c]:
                    if n not in seen:
                        seen[n] = h
                        nxt.append(n)
            frontier = nxt
        return seen

    def speed_range(self, who):
        return self.speeds[f"{who}_min"], self.speeds[f"{who}_max"]

    def transit_window(self, dist_m, who, slack=SLACK_S):
        """(min, max) seconds to walk dist_m."""
        vmin, vmax = self.speed_range(who)
        return max(0.0, dist_m / vmax - slack), dist_m / vmin + slack

    def plausibility(self, dist_m, dt, who):
        """1.0 for a normal walking speed, falling off for too fast or too slow."""
        lo, hi = self.transit_window(dist_m, who)
        if dt < lo or dt > hi:
            return 0.0
        vmin, vmax = self.speed_range(who)
        typical = dist_m / ((vmin + vmax) / 2)
        spread = (hi - lo) / 2 or 1.0
        return math.exp(-((dt - typical) / spread) ** 2)

    def nearest_camera(self, pos, among=None):
        among = among or self.cameras
        return min(among, key=lambda c: math.dist(self.cameras[c].pos, pos))
