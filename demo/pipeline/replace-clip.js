// Swap clips in a CreativAI collection for new versions of the same camera/time.
// Removes the old media from CreativAI and forgets its cached answers; then run ingest.js
// (with --index) to upload and index the new file, and find-child.js to ask about it again.
//
//   node demo/pipeline/replace-clip.js demo/pipeline/clips-case-A.json A4 A5
const fs = require("fs");
const path = require("path");
const { api } = require("./creativai");

const [manifestPath, ...ids] = process.argv.slice(2);
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const statePath = path.join(path.dirname(manifestPath), `state-${manifest.collection_name}.json`);
const state = JSON.parse(fs.readFileSync(statePath, "utf8"));
const cachePath = path.join(path.dirname(manifestPath), `cache-${state.collection_id}.json`);
const cache = fs.existsSync(cachePath) ? JSON.parse(fs.readFileSync(cachePath, "utf8")) : {};

(async () => {
  const old = ids.filter(id => state.media[id]).map(id => state.media[id].media_id);
  if (old.length) {
    const res = await api("DELETE", `/collections/${state.collection_id}/media`, { media_ids: old });
    console.log("removed from CreativAI:", ids.join(", "), JSON.stringify(res).slice(0, 200));
  }
  for (const id of ids) {
    delete state.media[id];
    for (const k of Object.keys(cache)) if (k.startsWith(id + "::")) delete cache[k];
  }
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
  fs.writeFileSync(cachePath, JSON.stringify(cache, null, 2));
  console.log(`Forgot ${ids.join(", ")} in state and cache. Next: node demo/pipeline/ingest.js ${manifestPath} --index`);
})().catch(e => { console.error("ERROR", e.message); process.exit(1); });
