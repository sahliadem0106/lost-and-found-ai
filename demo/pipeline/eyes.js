// The Eyes: ask CreativAI questions about specific clips.
// For the clips the Map picked, it builds a data plate from just those clips, adds one bundled
// set of questions (knowledge extraction), and reads the answers back. Answers are cached per
// clip + question in cache-<collection>.json, so a repeat run costs nothing.
const fs = require("fs");
const path = require("path");
const { api, sleep } = require("./creativai");

// CreativAI stores each question as a column name with punctuation changed ("." -> "_", final
// full stop dropped), so answers are matched on letters and digits only.
const norm = s => s.toLowerCase().replace(/[^a-z0-9]/g, "");
const answerFor = (info, q) => {
  if (!info) return undefined;
  const k = Object.keys(info).find(k => norm(k) === norm(q));
  return k === undefined ? undefined : info[k];
};

class Eyes {
  constructor(statePath, log = console.log) {
    this.statePath = statePath;
    this.state = JSON.parse(fs.readFileSync(statePath, "utf8"));
    this.cid = this.state.collection_id;
    this.cachePath = path.join(path.dirname(statePath), `cache-${this.cid}.json`);
    this.cache = fs.existsSync(this.cachePath) ? JSON.parse(fs.readFileSync(this.cachePath, "utf8")) : {};
    this.log = log;
    this.creditsUsed = 0;
  }

  key(clipId, question) { return `${clipId}::${question}`; }

  // questions: array of strings. Returns { clipId: { question: answer } }.
  async ask(clipIds, questions) {
    const missing = clipIds.filter(c => questions.some(q => !(this.key(c, q) in this.cache)));
    if (missing.length) await this.#extract(missing, questions);
    return Object.fromEntries(clipIds.map(c => [c, Object.fromEntries(questions.map(q => [q, this.cache[this.key(c, q)]]))]));
  }

  async #extract(clipIds, questions) {
    const before = (await api("GET", "/users/me/info")).credits;
    this.log(`    [CreativAI] asking ${questions.length} question(s) about ${clipIds.join(", ")} ...`);
    const mediaIds = clipIds.map(c => this.state.media[c].media_id);
    const job = await api("POST", "/data-plates/create-from-collection",
      { collection_id: this.cid, name: `lost-found ${clipIds.join("+")} ${Date.now()}`, video_urls: mediaIds });
    let st;
    for (let i = 0; i < 60; i++) {
      await sleep(2000);
      st = await api("GET", `/data-plates/jobs/${job.job_id}`);
      if (/completed|failed|error/.test(st.status)) break;
    }
    const plateId = st.data_plate?.plate_id || st.plate_id;
    if (!plateId) throw new Error("plate creation failed: " + JSON.stringify(st).slice(0, 300));

    const ke = await api("POST", "/knowledge-extraction/columns/add",
      { collection_id: this.cid, plate_id: plateId, question: questions, model_version: "pro" });
    const keJob = ke.job_id || ke.jobs?.[0]?.job_id;
    for (let i = 0; keJob && i < 120; i++) {
      await sleep(5000);
      const s = await api("GET", `/knowledge-extraction/jobs/${keJob}`);
      if (/completed|failed|error/.test(s.status || "")) break;
    }

    // Read the answers back and map each segment to its clip by file name.
    let plate;
    for (let i = 0; i < 12; i++) {
      plate = await api("POST", "/data-plates/get", { collection_id: this.cid, plate_id: plateId });
      const filled = (plate.segments || []).every(s => questions.every(q => answerFor(s.extracted_info, q) !== undefined));
      if (filled) break;
      await sleep(5000);
    }
    const byFile = Object.fromEntries(Object.entries(this.state.media).map(([id, m]) => [m.file.replace(/\.mp4$/, ""), id]));
    for (const seg of plate.segments || []) {
      const s = JSON.stringify(seg);
      const clip = Object.entries(byFile).find(([f]) => s.includes(f))?.[1];
      if (!clip) continue;
      for (const q of questions) {
        const a = answerFor(seg.extracted_info, q);
        if (a !== undefined) this.cache[this.key(clip, q)] = typeof a === "string" ? a : JSON.stringify(a);
      }
    }
    fs.writeFileSync(this.cachePath, JSON.stringify(this.cache, null, 2));
    const used = before - (await api("GET", "/users/me/info")).credits;
    this.creditsUsed += used;
    this.log(`    [CreativAI] done (${used.toFixed(1)} credits)`);
  }
}

module.exports = { Eyes };
