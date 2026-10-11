"""The Eyes interface. The real one wraps CreativAI; SimEyes answers from a case's ground truth."""
from dataclasses import dataclass

from .topology import parse_t


@dataclass(frozen=True)
class Hit:
    """One sighting: a camera, an absolute time span and how well it matches the query."""
    camera: str
    start: float
    end: float
    score: float
    ref: str = ""  # clip / segment id from the Eyes, for showing the proof clip


class Eyes:
    def search(self, query, camera, t0, t1):
        """Hits for `query` on `camera` overlapping [t0, t1], best first."""
        raise NotImplementedError

    def ask(self, question, camera, t0, t1):
        """Probability that the answer to a yes/no `question` is yes for this span."""
        raise NotImplementedError


class SimEyes(Eyes):
    """A stand-in for CreativAI built from `mall_topology.json` → cases.

    `signatures` maps a query keyword to {track_name: similarity}, e.g. the child
    query matches the child track strongly and the lookalike decoy a bit less.
    Used to test the Map + Brain loop before we have footage.
    """

    def __init__(self, case, signatures, until=None):
        self.until = until  # footage only exists up to "now"
        self.tracks = {}
        fam = []
        for cam, s, e, note in case["family"]:
            fam.append((cam, parse_t(s), parse_t(e), note))
        self.tracks["family"] = fam
        self.tracks["child"] = [(cam, parse_t(s), parse_t(e), "alone") for cam, s, e in case["child"]]
        for i, (cam, s, e, note) in enumerate(case.get("decoys", [])):
            self.tracks[f"decoy{i}"] = [(cam, parse_t(s), parse_t(e), note)]
        self.signatures = signatures
        self.calls = []

    def _key(self, query):
        for k in self.signatures:
            if k in query:
                return k
        return None

    def search(self, query, camera, t0, t1):
        self.calls.append(("search", camera, t0, t1))
        sims = self.signatures.get(self._key(query), {})
        hits = []
        for name, rows in self.tracks.items():
            sim = sims.get(name, 0.0)
            if sim <= 0:
                continue
            for i, (cam, s, e, _) in enumerate(rows):
                if self.until is not None:
                    e = min(e, self.until)
                if cam == camera and s <= t1 and e >= t0 and s <= e:
                    hits.append(Hit(cam, s, e, sim, f"{name}#{i}"))
        return sorted(hits, key=lambda h: -h.score)

    def ask(self, question, camera, t0, t1):
        self.calls.append(("ask", camera, t0, t1))
        mid = (t0 + t1) / 2
        if question == "with_child":
            for cam, s, e, note in self.tracks["family"]:
                if cam == camera and s <= mid <= e:
                    if note.startswith("child_leaves_"):
                        return 1.0 if mid < parse_t(note.rsplit("_", 1)[1]) else 0.0
                    return 1.0 if note == "with_child" else 0.0
            return 0.5
        if question == "alone":
            for name, rows in self.tracks.items():
                for cam, s, e, _ in rows:
                    if cam == camera and s <= mid <= e:
                        return 0.95 if name == "child" else 0.05
            return 0.5
        raise ValueError(question)
