// The agent: from a guard's report to "where was the child lost, and where is the child now".
//
//   node demo/pipeline/find-child.js --case A \
//     --child "a small boy of about 6 in a bright red t-shirt and blue jeans" \
//     --family "a man in a long white robe (thobe) with a red-and-white checkered headscarf ..." \
//     --arrived 14:00
//
// Or give one sentence and let the agent split it:
//   node demo/pipeline/find-child.js --case A --report "Lost: small boy, about 6, red t-shirt and jeans. Came with: man in white thobe and red shemagh, woman in black abaya and grey hijab. Arrived: 14:00"
//
// Loop: the Map (graph.js) says which cameras and minutes are physically possible next;
// the Eyes (CreativAI, eyes.js) look only at that footage; repeat until the path is complete.
const fs = require("fs");
const path = require("path");
const G = require("./graph");
const { Eyes } = require("./eyes");

// ---------- inputs ----------
const args = {};
for (let i = 2; i < process.argv.length; i += 2) args[process.argv[i].replace(/^--/, "")] = process.argv[i + 1];
if (args.report) {
  const r = args.report;
  args.child ||= (r.match(/lost[^:]*:\s*([^.]*(?:\.\d[^.]*)*)\./i) || [])[1];
  args.family ||= (r.match(/came with[^:]*:\s*([^.]*)\./i) || [])[1];
  args.arrived ||= (r.match(/arrived[^:]*:\s*(\d{1,2}:\d{2})/i) || [])[1];
}
for (const k of ["case", "child", "family", "arrived"])
  if (!args[k]) { console.error(`Missing --${k}. See the usage at the top of find-child.js.`); process.exit(1); }

const dir = __dirname;
const manifest = JSON.parse(fs.readFileSync(path.join(dir, `clips-case-${args.case}.json`), "utf8"));
const statePath = path.join(dir, `state-${manifest.collection_name}.json`);
const footage = manifest.clips.map(c => ({ ...c, t0: G.toSec(c.start), t1: G.toSec(c.start) + 15 }));
const lines = [];
const log = (s = "") => { console.log(s); lines.push(s); };
const eyes = new Eyes(statePath, log);
// Structured trace of every step, for the animated replay (demo/replay.html).
const trace = [];
const ev = e => trace.push(e);
const win = w => ({ camera: w.camera, hops: w.hops ?? 0, via: w.via ?? [w.camera], from: G.toClock(Math.max(0, w.from)), to: G.toClock(w.to) });
const sighting = h => ({ id: h.id, camera: h.camera, time: G.toClock(h.t0), family: h.family, child: h.child, leaves: h.leaves, why: h.why });

// ---------- the questions (same for every case; only the descriptions change) ----------
const Q = {
  family: `Are these adults visible in this video: ${args.family}? Start your answer with "yes" or "no", then give one short reason.`,
  child: `Look for this child: ${args.child}. Start your answer with exactly one of: "with these adults" (the child is together with ${args.family}), "alone" (the child has no adult with them at the end of the video), "with other adults", or "not present". Then give one short reason.`,
  leaves: `If the child (${args.child}) walks away from the adults they came with in this video, at what second does it happen? Answer with the number of seconds only, or "none".`,
};
const questions = [Q.family, Q.child, Q.leaves];

function read(ans) {
  const fam = /^\W*yes/i.test(ans[Q.family] || "");
  const c = (ans[Q.child] || "").toLowerCase();
  const child = /^\W*with these adults/.test(c) ? "with_family" : /^\W*alone/.test(c) ? "alone"
    : /^\W*with other adults/.test(c) ? "with_others" : "absent";
  const m = (ans[Q.leaves] || "").match(/(\d+(?:\.\d+)?)/);
  const leaves = m && !/none/i.test(ans[Q.leaves]) ? Number(m[1]) : null;
  return { family: fam, child, leaves, why: { family: ans[Q.family], child: ans[Q.child], leaves: ans[Q.leaves] } };
}

// Footage that overlaps any of the Map's time windows.
function candidates(windows, seen) {
  return footage.filter(f => !seen.has(f.id) && windows.some(w => w.camera === f.camera && f.t0 <= w.to && f.t1 >= w.from));
}

async function look(clips, phase) {
  if (!clips.length) return [];
  ev({ type: "ask", phase, clips: clips.map(c => c.id) });
  const ans = await eyes.ask(clips.map(c => c.id), questions);
  const out = clips.map(c => ({ ...c, ...read(ans[c.id]) }));
  ev({ type: "answers", phase, results: out.map(sighting) });
  return out;
}

const fmt = s => G.toClock(s);
const describe = o => `${o.id} @ ${o.camera} (${G.cameras[o.camera].name}) ${fmt(o.t0)}`;

(async () => {
  const t0 = Date.now();
  const result = { case: args.case, report: { child: args.child, family: args.family, arrived: args.arrived }, steps: [] };
  log(`CASE ${args.case}: lost child report`);
  log(`  child : ${args.child}`);
  log(`  family: ${args.family}`);
  log(`  arrived around ${args.arrived}\n`);
  ev({ type: "report", ...result.report, questions: Q });

  // ① Entry: entrance cameras within ±30 min of the reported arrival.
  const arrived = G.toSec(args.arrived);
  const entrances = Object.values(G.cameras).filter(c => c.zone === "entrance").map(c => c.id);
  log(`① ENTRY: checking entrance cameras ${entrances.join(", ")} between ${fmt(arrived - 1800)} and ${fmt(arrived + 1800)}`);
  const seen = new Set();
  let entryClips = footage.filter(f => entrances.includes(f.camera) && Math.abs(f.t0 - arrived) <= 1800);
  entryClips.forEach(f => seen.add(f.id));
  ev({ type: "map", phase: "entry", who: "adult", from: null, candidates: entryClips.map(c => c.id),
    windows: entrances.map(c => ({ camera: c, hops: 0, via: [c], from: fmt(arrived - 1800), to: fmt(arrived + 1800) })) });
  let hits = (await look(entryClips, "entry")).filter(h => h.family);
  if (!hits.length) {
    log("  The family was not found at any entrance. Stopping.");
    ev({ type: "decision", phase: "entry", kind: "stop", text: "The family was not found at any entrance." });
    return finish(result);
  }
  let at = hits.sort((a, b) => a.t0 - b.t0)[0];
  const familyPath = [at];
  log(`  ✔ family found: ${describe(at)}; child: ${at.child.replace("_", " ")}\n`);
  result.steps.push({ step: "entry", sighting: at });
  ev({ type: "decision", phase: "entry", kind: "found", clip: at.id, camera: at.camera, time: fmt(at.t0), child: at.child });

  // ② Follow the family forward until the child is no longer with them.
  let separation = null;
  log(`② FOLLOW THE FAMILY (adult walking speeds, up to 3 hops for blind spots, up to 15 min in a shop)`);
  while (!separation) {
    if (at.leaves !== null && at.child !== "absent") { separation = { camera: at.camera, t: at.t0 + at.leaves, clip: at.id }; break; }
    const windows = G.nextWindows(at.camera, at.t1, { who: "adult", maxHops: 3, slack: 900 })
      .concat([{ camera: at.camera, from: at.t1, to: at.t1 + 900 }]);
    const cand = candidates(windows, seen);
    cand.forEach(f => seen.add(f.id));
    log(`  from ${describe(at)} → Map allows ${windows.length} camera windows; footage there: ${cand.map(c => c.id).join(", ") || "none"}`);
    ev({ type: "map", phase: "family", who: "adult", from: { camera: at.camera, time: fmt(at.t1), clip: at.id }, windows: windows.map(win), candidates: cand.map(c => c.id) });
    if (!cand.length) {
      log("  No more footage on the family's possible path.");
      ev({ type: "decision", phase: "family", kind: "stop", text: "No more footage on the family's possible path." });
      break;
    }
    const seenHere = await look(cand, "family");
    for (const h of seenHere) log(`    ${h.id} ${h.camera.padEnd(6)} family: ${h.family ? "yes" : "no "}  child: ${h.child.padEnd(11)} leaves at: ${h.leaves ?? "-"}`);
    // Read the footage in time order: the first clip where the described child walks away from
    // adults is the separation, even if a later clip is ambiguous; otherwise the first clip
    // with the family is the next sighting.
    let next = null;
    for (const h of seenHere.sort((a, b) => a.t0 - b.t0)) {
      if (h.leaves !== null && (h.child === "alone" || h.child === "with_family")) {
        familyPath.push(h);
        separation = { camera: h.camera, t: h.t0 + h.leaves, clip: h.id };
        log(`  ✔ ${h.id}: the child walks away from the adults ${h.leaves} s into the clip`);
        ev({ type: "decision", phase: "family", kind: "separation", clip: h.id, camera: h.camera, time: fmt(h.t0 + h.leaves), offset: h.leaves, walk: G.plausibility(at.camera, at.t1, h.camera, h.t0, "adult") });
        break;
      }
      if (h.family) { next = h; break; }
    }
    if (separation) break;
    if (!next) { log("  The family doesn't appear in any of it. Stopping the family track."); break; }
    const p = G.plausibility(at.camera, at.t1, next.camera, next.t0, "adult");
    log(`  ✔ next sighting: ${describe(next)} (walk ${p.dist_m} m at ${p.speed} m/s, plausible)`);
    ev({ type: "decision", phase: "family", kind: "next", clip: next.id, camera: next.camera, time: fmt(next.t0), child: next.child, walk: p });
    if (next.child === "absent" && familyPath.at(-1).child === "with_family") {
      separation = { camera: familyPath.at(-1).camera, t: familyPath.at(-1).t1, clip: familyPath.at(-1).id, approx: true };
    }
    familyPath.push(next);
    at = next;
  }
  result.family_path = familyPath.map(({ id, camera, t0, child }) => ({ id, camera, time: fmt(t0), child }));
  if (!separation) { log("\nNo separation found on the family's path."); return finish(result); }
  log(`\n③ SEPARATION: ${separation.camera} (${G.cameras[separation.camera].name}) at ${fmt(separation.t)}${separation.approx ? " (approx.)" : ""}, clip ${separation.clip}\n`);
  result.separation = { camera: separation.camera, time: fmt(separation.t), clip: separation.clip };

  // ④ Follow the child forward from the separation point; only "alone" sightings count.
  log(`④ FOLLOW THE CHILD (child walking speeds, up to 4 hops, from ${separation.camera} ${fmt(separation.t)})`);
  let cur = { camera: separation.camera, t1: separation.t, id: separation.clip };
  const childPath = [];
  const rejected = [];
  for (;;) {
    const windows = G.nextWindows(cur.camera, cur.t1, { who: "child", maxHops: 4, slack: 240 })
      .concat([{ camera: cur.camera, from: cur.t1, to: cur.t1 + 240 }]);
    const cand = candidates(windows, new Set([...childPath.map(c => c.id), ...rejected.map(r => r.id), ...familyPath.map(f => f.id)]));
    log(`  from ${cur.camera} ${fmt(cur.t1)} → footage on the child's possible path: ${cand.map(c => c.id).join(", ") || "none"}`);
    ev({ type: "map", phase: "child", who: "child", from: { camera: cur.camera, time: fmt(cur.t1), clip: cur.id }, windows: windows.map(win), candidates: cand.map(c => c.id) });
    if (!cand.length) break;
    const seenHere = await look(cand, "child");
    for (const h of seenHere) {
      log(`    ${h.id} ${h.camera.padEnd(6)} child: ${h.child.padEnd(11)} family: ${h.family ? "yes" : "no"}`);
      if (h.child !== "alone") {
        rejected.push({ id: h.id, camera: h.camera, time: fmt(h.t0), why: h.child === "with_family" || h.child === "with_others" ? "a child matching the description, but with adults, not alone" : "child not seen" });
        ev({ type: "decision", phase: "child", kind: "reject", clip: h.id, camera: h.camera, time: fmt(h.t0), text: rejected.at(-1).why });
      }
    }
    const next = seenHere.filter(h => h.child === "alone").sort((a, b) => a.t0 - b.t0)[0];
    if (!next) break;
    const p = G.plausibility(cur.camera, cur.t1, next.camera, next.t0, "child");
    log(`  ✔ child alone: ${describe(next)} (${p.dist_m} m via ${p.via.join(" → ")}, ${p.speed} m/s)`);
    ev({ type: "decision", phase: "child", kind: "child_alone", clip: next.id, camera: next.camera, time: fmt(next.t0), walk: p });
    childPath.push(next);
    cur = next;
  }
  result.child_path = childPath.map(({ id, camera, t0 }) => ({ id, camera, time: fmt(t0) }));
  result.rejected = rejected;

  // ⑤ Act: where is the child now, and the alert for the nearest guard.
  const last = childPath.at(-1);
  if (last) {
    result.child_now = { camera: last.camera, name: G.cameras[last.camera].name, last_seen: fmt(last.t1), clip: last.id };
    log(`\n⑤ CHILD NOW: last seen alone at ${last.camera} (${G.cameras[last.camera].name}), ${fmt(last.t1)}, clip ${last.id}`);
    result.alert = `LOST CHILD: ${args.child}. Separated from parents at ${G.cameras[separation.camera].name} (${separation.camera}) around ${fmt(separation.t)}. ` +
      `Path: ${[separation.camera, ...childPath.map(c => c.camera)].join(" → ")}. Last seen ALONE at ${G.cameras[last.camera].name} (${last.camera}) at ${fmt(last.t1)}. Nearest guard: go there now. Proof: clip ${last.id}.`;
    log(`\nALERT → ${result.alert}`);
    ev({ type: "alert", text: result.alert, child_now: result.child_now, separation: result.separation });
    if (rejected.length) log(`Ignored: ${rejected.map(r => `${r.id} (${r.why})`).join("; ")}`);
  } else log("\nThe child was not seen alone on any reachable camera after the separation.");
  finish(result);

  function finish(res) {
    res.creativai_credits = +eyes.creditsUsed.toFixed(1);
    res.seconds = Math.round((Date.now() - t0) / 1000);
    res.log = lines;
    res.trace = trace;
    const out = path.join(dir, "..", "results", `case-${args.case}-run.json`);
    fs.mkdirSync(path.dirname(out), { recursive: true });
    fs.writeFileSync(out, JSON.stringify(res, null, 2));
    console.log(`\n(${res.seconds}s, ${res.creativai_credits} CreativAI credits; saved ${path.relative(path.join(dir, "..", ".."), out)})`);
  }
})().catch(e => { console.error("ERROR", e.message); process.exit(1); });
