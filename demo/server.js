// Local server for the case page. No dependencies: `node demo/server.js`, then open http://localhost:3000
//   GET  /                     the case page (demo/case.html)
//   GET  /api/topology         the camera graph
//   GET  /api/clips?case=A     which camera filmed which clip, and when
//   GET  /api/result?case=A    the agent's last result for a case
//   POST /api/find             run the agent on a report; streams its log line by line
//   GET  /raw/...              the clips (with byte-range support so the video player can seek)
const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const PORT = Number(process.env.PORT) || 3000;
const DEMO = __dirname;
const TYPES = { ".html": "text/html; charset=utf-8", ".json": "application/json", ".js": "text/javascript", ".mp4": "video/mp4", ".css": "text/css" };

function sendFile(req, res, file) {
  fs.stat(file, (err, st) => {
    if (err || !st.isFile()) { res.writeHead(404); return res.end("not found"); }
    const type = TYPES[path.extname(file)] || "application/octet-stream";
    const range = req.headers.range && /bytes=(\d*)-(\d*)/.exec(req.headers.range);
    if (range) {
      const start = range[1] ? Number(range[1]) : 0;
      const end = range[2] ? Number(range[2]) : st.size - 1;
      res.writeHead(206, { "Content-Type": type, "Content-Range": `bytes ${start}-${end}/${st.size}`, "Accept-Ranges": "bytes", "Content-Length": end - start + 1 });
      return fs.createReadStream(file, { start, end }).pipe(res);
    }
    res.writeHead(200, { "Content-Type": type, "Content-Length": st.size, "Accept-Ranges": "bytes" });
    fs.createReadStream(file).pipe(res);
  });
}

function readBody(req) {
  return new Promise(resolve => { let b = ""; req.on("data", c => (b += c)); req.on("end", () => resolve(b)); });
}

http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const p = decodeURIComponent(url.pathname);

  if (p === "/") return sendFile(req, res, path.join(DEMO, "case.html"));
  if (p === "/api/topology") return sendFile(req, res, path.join(DEMO, "mall_topology.json"));
  if (p === "/api/clips") return sendFile(req, res, path.join(DEMO, "pipeline", `clips-case-${(url.searchParams.get("case") || "A").replace(/[^A-Z]/gi, "")}.json`));
  if (p === "/api/result") return sendFile(req, res, path.join(DEMO, "results", `case-${(url.searchParams.get("case") || "A").replace(/[^A-Z]/gi, "")}-run.json`));
  if (p.startsWith("/raw/")) {
    const file = path.normalize(path.join(DEMO, p));
    if (!file.startsWith(path.join(DEMO, "raw"))) { res.writeHead(403); return res.end(); }
    return sendFile(req, res, file);
  }

  if (p === "/api/find" && req.method === "POST") {
    let r;
    try { r = JSON.parse(await readBody(req)); } catch { res.writeHead(400); return res.end("bad json"); }
    const caseId = String(r.case || "A").replace(/[^A-Z]/gi, "");
    res.writeHead(200, { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff" });
    const agent = spawn(process.execPath, [path.join(DEMO, "pipeline", "find-child.js"),
      "--case", caseId, "--child", String(r.child || ""), "--family", String(r.family || ""), "--arrived", String(r.arrived || "")],
      { env: process.env });
    agent.stdout.on("data", d => res.write(d));
    agent.stderr.on("data", d => res.write(d));
    agent.on("close", code => res.end(`\n[agent finished, exit code ${code}]\n`));
    res.on("close", () => { if (!res.writableEnded) agent.kill(); }); // browser went away mid-run
    return;
  }

  res.writeHead(404); res.end("not found");
}).listen(PORT, () => console.log(`Lost & Found case page: http://localhost:${PORT}`));
