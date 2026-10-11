// Upload a case's clips to CreativAI, tag them with camera + start time, and index them.
// Usage: node demo/pipeline/ingest.js demo/pipeline/clips-case-A.json [--index]
// Progress is saved to state-<collection>.json next to the manifest, so a rerun resumes.
const fs = require("fs");
const path = require("path");
const { api, uploadFile, sleep } = require("./creativai");

const manifestPath = process.argv[2];
const doIndex = process.argv.includes("--index");
const repo = path.resolve(__dirname, "..", "..");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const statePath = path.join(path.dirname(manifestPath), `state-${manifest.collection_name}.json`);
const state = fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, "utf8")) : { media: {} };
const save = () => fs.writeFileSync(statePath, JSON.stringify(state, null, 2));
const toSec = t => t.split(":").reduce((a, b) => a * 60 + Number(b), 0);

(async () => {
  if (!state.collection_id) {
    const list = await api("GET", "/collections");
    const existing = Object.values(list.collections || {}).find(c => c.collection_name === manifest.collection_name);
    state.collection_id = existing ? existing.collection_id : (await api("POST", "/collections", {
      collection_name: manifest.collection_name, model: "video_only",
      description: "Lost & Found demo clips, tagged with camera and start time",
    })).collection_id;
    save();
  }
  const cid = state.collection_id;
  console.log("collection", cid);

  // 1. Upload each clip once.
  for (const clip of manifest.clips) {
    if (state.media[clip.id]) continue;
    const up = await api("POST", `/collections/${cid}/upload-url`, { filename: `${clip.id}.mp4`, content_type: "video/mp4" });
    await uploadFile(up.upload_url, fs.readFileSync(path.join(repo, clip.file)), "video/mp4");
    state.media[clip.id] = { media_id: up.media_id, file: up.unique_filename, confirmed: false };
    save();
    console.log("uploaded", clip.id, up.unique_filename);
  }

  // 2. Confirm with tags + metadata (camera, absolute start time).
  const pending = manifest.clips.filter(c => !state.media[c.id].confirmed);
  if (pending.length) {
    const tags = {}, metadata = {};
    for (const c of pending) {
      const m = state.media[c.id].media_id;
      tags[m] = [`clip:${c.id.toLowerCase()}`, `camera:${c.camera.toLowerCase()}`];
      metadata[m] = {
        clip: { datatype: "string", value: c.id },
        camera: { datatype: "string", value: c.camera },
        start_time: { datatype: "string", value: c.start },
        start_sec: { datatype: "number", value: toSec(c.start) },
      };
    }
    const job = await api("POST", `/collections/${cid}/confirm-upload`, { media_ids: Object.keys(tags), tags, metadata });
    console.log("confirm job", JSON.stringify(job));
    if (job.job_id) {
      for (let i = 0; i < 60; i++) {
        await sleep(5000);
        const st = await api("GET", `/collections/${cid}/confirm-upload/jobs/${job.job_id}`);
        if (/complete|done|success|fail|error/i.test(st.status || "")) { console.log("confirm", JSON.stringify(st).slice(0, 400)); break; }
      }
    }
    for (const c of pending) state.media[c.id].confirmed = true;
    save();
  }

  // 3. Wait for preprocessing (16 s chunks, thumbnails).
  let pre;
  for (let i = 0; i < 90; i++) {
    pre = await api("GET", `/indexing/preprocessing-status/${cid}`);
    const s = JSON.stringify(pre);
    if (i === 0 || i % 6 === 0) console.log("preprocessing", s.slice(0, 300));
    if (pre.can_start_indexing || pre.videos_failed) break;
    await sleep(10000);
  }

  // 4. Price check, then index only with --index.
  const est = await api("POST", "/indexing/chunk-based/estimate-cost", { collection_id: cid });
  console.log("indexing estimate", JSON.stringify(est));
  if (!doIndex) return console.log("Not indexing (run again with --index).");
  const idx = await api("POST", "/indexing/chunk-based", { collection_id: cid });
  state.indexing_id = idx.indexing_id || idx.job_id || idx.id;
  save();
  console.log("indexing started", JSON.stringify(idx).slice(0, 300));
  for (let i = 0; i < 120 && state.indexing_id; i++) {
    await sleep(10000);
    const st = await api("GET", `/indexing/chunk-based/${state.indexing_id}/status`);
    const s = JSON.stringify(st);
    if (i % 3 === 0) console.log("indexing", s.slice(0, 300));
    if (/"status"\s*:\s*"(completed|done|failed|error)"/i.test(s)) { console.log("indexing final", s.slice(0, 600)); break; }
  }
})().catch(e => { console.error("ERROR", e.message); process.exit(1); });
