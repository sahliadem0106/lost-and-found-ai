// The Map: camera graph + walking times. No AI, just geometry and time.
// Answers "after camera X at time t, which cameras could this person reach, and when?"
const fs = require("fs");
const path = require("path");

const topo = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "mall_topology.json"), "utf8"));

// "14:00" and "14:00:00" both mean 2 pm.
const toSec = t => { const p = t.split(":").map(Number); return p[0] * 3600 + (p[1] || 0) * 60 + (p[2] || 0); };
const toClock = s => [Math.floor(s / 3600), Math.floor(s / 60) % 60, Math.round(s % 60)].map(n => String(n).padStart(2, "0")).join(":");

const cameras = Object.fromEntries(topo.cameras.map(c => [c.id, c]));
const adj = {};
for (const e of topo.edges) {
  (adj[e.a] ||= []).push({ to: e.b, dist: e.dist_m });
  (adj[e.b] ||= []).push({ to: e.a, dist: e.dist_m });
}

function speeds(who) {
  const v = topo.walking_speed_mps;
  return who === "child" ? [v.child_min, v.child_max] : [v.adult_min, v.adult_max];
}

// Cameras reachable from `from` in at most `maxHops` walkway hops, with total distance.
function reachable(from, maxHops = 1) {
  const best = { [from]: { dist: 0, hops: 0, via: [from] } };
  let frontier = [from];
  for (let h = 1; h <= maxHops; h++) {
    const next = [];
    for (const c of frontier)
      for (const { to, dist } of adj[c] || []) {
        const d = best[c].dist + dist;
        if (to === from || (best[to] && best[to].dist <= d)) continue;
        best[to] = { dist: d, hops: h, via: [...best[c].via, to] };
        next.push(to);
      }
    frontier = next;
  }
  delete best[from];
  return best;
}

// Time windows (in seconds) when someone who was at `from` at time `t` could appear at each reachable camera.
// direction "forward" = later sightings; "backward" = earlier ones. `slack` widens the window for dwell time.
function nextWindows(from, t, { who = "adult", direction = "forward", maxHops = 1, slack = 60 } = {}) {
  const [vmin, vmax] = speeds(who);
  return Object.entries(reachable(from, maxHops)).map(([cam, r]) => {
    const fast = r.dist / vmax, slow = r.dist / vmin;
    const [lo, hi] = direction === "forward" ? [t + fast, t + slow + slack] : [t - slow - slack, t - fast];
    return { camera: cam, name: cameras[cam].name, hops: r.hops, via: r.via, dist_m: r.dist, from: lo, to: hi };
  });
}

// Is a move from (a, ta) to (b, tb) physically possible on foot? Returns the implied speed and a 0..1 score.
function plausibility(a, ta, b, tb, who = "adult") {
  if (a === b) return { ok: true, speed: 0, score: 1, dist_m: 0 };
  const r = reachable(a, 6)[b];
  if (!r) return { ok: false, score: 0, reason: "not connected" };
  const dt = Math.abs(tb - ta);
  const speed = dt > 0 ? r.dist / dt : Infinity;
  const [, vmax] = speeds(who);
  // Too fast = impossible; slower is fine (people stop and browse), but very slow loses a bit of confidence.
  const score = speed > vmax * 1.2 ? 0 : speed > vmax ? 0.5 : Math.min(1, 0.4 + 0.6 * Math.min(1, speed / 0.3 || 0));
  return { ok: score > 0, speed: +speed.toFixed(2), score: +score.toFixed(2), dist_m: r.dist, via: r.via };
}

module.exports = { topo, cameras, adj, reachable, nextWindows, plausibility, toSec, toClock };

if (require.main === module) {
  // Demo: node demo/pipeline/graph.js STR-B 14:19:10 child
  const [cam = "STR-B", t = "14:19:10", who = "child"] = process.argv.slice(2);
  console.log(`From ${cam} at ${t} (${who}), forward, up to 2 hops:`);
  for (const w of nextWindows(cam, toSec(t), { who, maxHops: 2 }))
    console.log(`  ${w.camera.padEnd(6)} ${w.name.padEnd(28)} ${w.hops} hop(s) ${String(w.dist_m).padStart(3)} m  ${toClock(w.from)}–${toClock(w.to)}  via ${w.via.join(" → ")}`);
}
