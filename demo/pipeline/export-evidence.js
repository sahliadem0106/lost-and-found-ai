// Export proof that the answers in the replay came from CreativAI.
// Fetches every data plate the agent created in the case's collection, straight from CreativAI,
// and saves each plate's ID, creation time, clips and stored answers to demo/results/.
//
//   node demo/pipeline/export-evidence.js demo/pipeline/clips-case-A.json
const fs = require("fs");
const path = require("path");
const { api } = require("./creativai");

const manifestPath = process.argv[2];
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const dir = path.dirname(manifestPath);
const state = JSON.parse(fs.readFileSync(path.join(dir, `state-${manifest.collection_name}.json`), "utf8"));
const cid = state.collection_id;
const cache = JSON.parse(fs.readFileSync(path.join(dir, `cache-${cid}.json`), "utf8"));
const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, "");

(async () => {
  const list = await api("POST", "/data-plates/list", { collection_id: cid });
  const plates = Object.values(list).filter(p => p && p.plate_id && /^lost-found/.test(p.name || ""));
  const current = Object.fromEntries(Object.entries(state.media).map(([id, m]) => [m.file.replace(/\.mp4$/, ""), id]));
  const out = { collection_id: cid, exported_at: new Date().toISOString(), note: "Fetched directly from CreativAI's API. 'in_replay' is true when the stored answer is identical to the one the replay shows.", plates: [] };
  let matched = 0, total = 0;
  for (const p of plates.sort((a, b) => (a.created_at || "").localeCompare(b.created_at || ""))) {
    const full = await api("POST", "/data-plates/get", { collection_id: cid, plate_id: p.plate_id });
    const segments = full.segments.map(seg => {
      const file = (JSON.stringify(seg).match(/A\d_[0-9a-f]{8}/) || ["?"])[0];
      const clip = current[file] || null; // null = an earlier version of a clip that was later replaced
      const answers = Object.entries(seg.extracted_info || {}).map(([question, answer]) => {
        const key = clip && Object.keys(cache).find(k => k.startsWith(clip + "::") && norm(k.split("::")[1]) === norm(question));
        const inReplay = !!key && cache[key] === answer;
        if (clip) { total++; if (inReplay) matched++; }
        return { question, answer, in_replay: inReplay };
      });
      return { file, clip: clip || "(replaced version)", answers };
    });
    out.plates.push({ plate_id: p.plate_id, name: p.name, created_at: full.created_at, segments });
  }
  out.summary = `${matched} of ${total} answers for the current clips are identical to the replay.`;
  const dest = path.join(dir, "..", "results", `creativai-evidence-${manifest.collection_name.replace(/^lost-found-/, "")}.json`);
  fs.writeFileSync(dest, JSON.stringify(out, null, 2));
  console.log(`${out.plates.length} plates exported → ${path.relative(path.join(dir, "..", ".."), dest)}`);
  console.log(out.summary);
})().catch(e => { console.error("ERROR", e.message); process.exit(1); });
