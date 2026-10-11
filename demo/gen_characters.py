#!/usr/bin/env python3
"""Generate the character pictures with Higgsfield (Grok Image 2.0).

For each character: the reference sheet first (16:9, text only), then the
front and back photos (2:3) with the sheet passed as the image reference so
all three show the same person.

Usage:
  HIGGSFIELD_API_KEY=... python3 demo/gen_characters.py [KEY ...] [--only sheet,front,back]

Saves demo/assets/characters/<KEY>_{sheet,front,back}.png and records each
request in demo/assets/characters/log.json (the sheet URL is reused later).
"""
import json
import os
import sys
import time
import uuid
import urllib.request
from pathlib import Path

API = "https://api.higgsfield.ai"
ENDPOINT = "xai/grok-imagine-image-2.0"
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "assets" / "characters"
LOG = OUT / "log.json"

SAME_PERSON = ("The person must be exactly the same person as in the reference image: "
               "same face, same age, same body, same clothes and colours, same accessories. ")


def call(method, url, body=None):
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body else None)
    if os.environ.get("HIGGSFIELD_API_KEY"):
        req.add_header("Authorization", "Key " + os.environ["HIGGSFIELD_API_KEY"])
    # else: the agent proxy injects the Higgsfield credential for api.higgsfield.ai
    req.add_header("Content-Type", "application/json")
    if body:
        req.add_header("Idempotency-Key", str(uuid.uuid4()))
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {url} -> {e.code}: {e.read().decode()[:500]}")


def generate(prompt, aspect, refs=None):
    body = {"prompt": prompt, "resolution": "2k", "aspect_ratio": aspect, "quality": "medium"}
    if refs:
        body["image_urls"] = refs
    sub = call("POST", f"{API}/{ENDPOINT}", body)
    print("   request", sub.get("request_id"), flush=True)
    for _ in range(120):
        time.sleep(5)
        st = call("GET", sub["status_url"])
        if st["status"] in ("completed", "failed", "nsfw", "canceled"):
            break
    if st["status"] != "completed":
        raise SystemExit(f"   {st['status']}: {st}")
    return sub["request_id"], st["images"][0]["url"]


def download(url, path):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        path.write_bytes(r.read())


def main():
    args = sys.argv[1:]
    only = {"sheet", "front", "back"}
    if "--only" in args:
        i = args.index("--only")
        only = set(args[i + 1].split(","))
        del args[i:i + 2]
    chars = json.loads((ROOT / "prompts" / "prompts.json").read_text())["characters"]
    if args:
        chars = [c for c in chars if c["key"] in args]
    OUT.mkdir(parents=True, exist_ok=True)
    log = json.loads(LOG.read_text()) if LOG.exists() else {}

    for c in chars:
        k = c["key"]
        entry = log.setdefault(k, {})
        print(f"== {k}", flush=True)
        if "sheet" in only:
            rid, url = generate(c["images"]["sheet"], "16:9")
            entry["sheet"] = {"request_id": rid, "url": url, "model": ENDPOINT}
            download(url, OUT / f"{k}_sheet.png")
            LOG.write_text(json.dumps(log, indent=2))
        sheet_url = entry["sheet"]["url"]
        for view in ("front", "back"):
            if view not in only:
                continue
            rid, url = generate(SAME_PERSON + c["images"][view], "2:3", [sheet_url])
            entry[view] = {"request_id": rid, "url": url, "model": ENDPOINT}
            download(url, OUT / f"{k}_{view}.png")
            LOG.write_text(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
