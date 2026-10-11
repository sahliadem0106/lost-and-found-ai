// Run one CreativAI search on a case collection and print the hits as clip / camera / time.
// Usage: node demo/pipeline/search.js demo/pipeline/state-lost-found-case-a.json "query" [tag ...] [--raw]
const fs = require("fs");
const { api, sleep } = require("./creativai");

const [statePath, query, ...rest] = process.argv.slice(2);
const raw = rest.includes("--raw");
const tags = rest.filter(a => a !== "--raw");
const state = JSON.parse(fs.readFileSync(statePath, "utf8"));
const byFile = {};
for (const [id, m] of Object.entries(state.media)) byFile[m.file.replace(/\.mp4$/, "")] = id;

const clipOf = hit => {
  const s = JSON.stringify(hit);
  for (const [f, id] of Object.entries(byFile)) if (s.includes(f)) return id;
  return "?";
};

(async () => {
  const body = { collection_id: state.collection_id, text_query: query, search_type: "hybrid", page_size: 20, min_score: 0 };
  if (tags.length) body.tags = tags;
  let res = await api("POST", "/search", body);
  const jobId = res.search_job_id || res.job_id;
  for (let i = 0; jobId && i < 60; i++) {
    await sleep(2000);
    res = await api("GET", `/search/jobs/${jobId}`);
    if (/completed|failed/.test(res.status || "")) break;
  }
  if (raw) return console.log(JSON.stringify(res, null, 1).slice(0, 6000));
  // Results come back ranked in three buckets; each hit is one 16 s chunk of a media file.
  const hits = [];
  for (const bucket of ["high", "medium", "low"])
    for (const h of res[bucket] || []) hits.push({ bucket, ...h });
  console.log(`"${query}"${tags.length ? " tags=" + tags : ""} -> ${hits.length} hits`);
  hits.forEach((h, i) => {
    const e = h.entity || {};
    const camera = (e.tags || []).find(t => t.startsWith("camera:")) || "";
    console.log(`  #${i + 1}  ${clipOf(h)}  ${camera.replace("camera:", "").toUpperCase().padEnd(6)}  ${Number(e.start).toFixed(0)}-${Number(e.end).toFixed(0)}s  score=${(h.ranking_score ?? 0).toFixed(4)}  ${h.bucket}`);
  });
})().catch(e => { console.error("ERROR", e.message); process.exit(1); });
