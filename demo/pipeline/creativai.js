// Small CreativAI REST client. Reads the key from CREATIVAI_API_KEY and never prints it.
const BASE = "https://ws.creativai-apis.com/api/v2";
const KEY = process.env.CREATIVAI_API_KEY;
if (!KEY) throw new Error("CREATIVAI_API_KEY is not set");

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function api(method, path, body, { retries = 5 } = {}) {
  for (let attempt = 0; ; attempt++) {
    try {
      const res = await fetch(BASE + path, {
        method,
        headers: { "X-API-Key": KEY, "Content-Type": "application/json" },
        body: body ? JSON.stringify(body) : undefined,
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) throw Object.assign(new Error(`${method} ${path} -> ${res.status} ${JSON.stringify(json)}`), { status: res.status });
      return json.data ?? json;
    } catch (e) {
      // Retry network errors and GETs; never blindly repeat a failed POST that reached the server.
      const reached = e.status !== undefined;
      if (attempt >= retries || (reached && (method !== "GET" || e.status < 500))) throw e;
      await sleep(5000);
    }
  }
}

async function uploadFile(url, buffer, contentType) {
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const res = await fetch(url, { method: "PUT", headers: { "Content-Type": contentType }, body: buffer });
      if (res.ok) return;
      throw new Error(`upload -> ${res.status} ${await res.text()}`);
    } catch (e) {
      if (attempt === 3) throw e;
      await sleep(5000);
    }
  }
}

module.exports = { api, uploadFile, sleep };
