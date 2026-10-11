# Project plan: **Lost & Found** (working name)

> **One line:** When a child goes missing in a mall, our system rebuilds the family's path across the security cameras, finds the moment and place they were separated, and then finds where the child is now. It combines **our own camera-graph engine** with **CreativAI's video understanding**.

## In plain words: what we are building

**A website for mall security.** A guard types: *"Lost boy, about 6, red t-shirt. Family came in around 2 pm."*
The website shows **on the mall map**: where the family walked, **where the boy got separated**, and **where the boy is now**, with the video clips as proof.

It has only **three pieces**:

| Piece | Nickname | Its only job | Who makes it |
|---|---|---|---|
| Camera graph | **The Map** | Knows which cameras are next to each other and how long the walk takes. Answers: *"After camera X at 14:19, check cameras Y and Z between 14:19:30 and 14:20:10."* No AI, just simple code. | Us (Python) |
| CreativAI | **The Eyes** | Watches the clips the Map points to and answers in words: *"Is this family here?"*, *"Is the child still with them?"*, *"Is there a lost boy in red here?"* | CreativAI API |
| Claude agent | **The Brain** | Runs the loop (Map → Eyes → Map → Eyes …), talks to the guard and writes the alert. | Claude API |

**The loop works like a detective walking room to room:** the Map says which rooms to check next, the Eyes look, the Map moves forward, and this repeats until the path is complete.

**Parked for later, so ignore these for now:** face scanning at gates, Re-ID models, guessing direction from shop types, separation hotspot statistics.

---

This file is the single source of truth. The older documents in `concepts/` and `IDEAS.md` are the brainstorm that led here.

---

## 1. The goal

**Main goal:** build a working demo that shows a lost child being found from **real or realistic multi-camera footage** in minutes, not hours, and explains *why* the separation happened.

**What the demo must prove:**
1. **Where:** we can follow a family from camera to camera using the camera graph (our contribution).
2. **What and when:** CreativAI finds the exact moment the child stopped being with the parents, using a plain-language question.
3. **Find:** CreativAI finds the child in that zone from a *description* ("small boy, red shirt, alone, looking lost"). No photo of the child is needed.
4. **Act:** an agent sends the nearest guard a location, a clip and the path, and writes a case report with the cause.

**Audience:** CreativAI / Prof. Elhoseiny's team, KAUST judges, potential customers (mall operators, event security).

**Pitch line:** *"Trackers tell you where someone went. CreativAI tells you what happened, and finds the child from a sentence."*

---

## 2. Confirmation of what we agreed (and three tweaks)

✅ **Yes, it's a combo:** camera-graph tracking (our way) + CreativAI + an AI agent.

**Tweak 1: the graph decides *where and when* to look, and CreativAI does the looking.**
We don't build a heavy face-recognition tracker; that already exists commercially. Our engine uses the camera map, the exit edges of each frame and walking times to pick **which cameras and which seconds** to check next. CreativAI is then asked to search exactly those clips. This keeps CreativAI at the centre and makes the graph our own contribution.

**Tweak 2: track the group, not one face.**
Abayas and thobes look alike, so the "signature" is the **group**: *man in white thobe + red shemagh, woman in black abaya, boy in red t-shirt, green shopping bag*. Faces are used only at the entrance gate (the one place they're clear), and only with consent. Geometry and time (your idea) are the main tie-breaker.

**Tweak 3: footage = real first, generated second.**
No free dataset contains a "lost child" story, so:
- **Plan A (best): film it ourselves** with 4–6 phones and friends. It's free and the people are real, so they look the same in every camera.
- **Plan B: Kling clips** (the 11-shot plan in `demo/lost-and-found-mall-shotlist.md`), if filming isn't possible.
- **Free public datasets** for testing the graph engine on real security footage and as background crowd clips (section 4).

---

## 3. How it works

```
             ┌────────────────────────── CASE OPENED ───────────────────────────┐
             │ Parents report at the desk → guard photo → GROUP SIGNATURE        │
             └───────────────┬──────────────────────────────────────────────────┘
                             ▼
 ① ENTRY LOOKUP      Search the entrance cameras for the group → time they came in
                             ▼
 ② GRAPH TRACKING    from the current camera: neighbours + time windows (graph engine)
    (our code)       → ask CreativAI only about those clips → best match → next hop
                     → full path ENT-01 → … → INF-01 + list of matched segments
                             ▼
 ③ JOURNEY REEL      ffmpeg joins the matched segments into one video
                     → CreativAI: "When is the child no longer with them?"
                     → separation moment + camera (e.g. STR-B 14:19:10)
                             ▼
 ④ ZONE SWEEP        all cameras within N hops of the separation point, after that time
                     → CreativAI: "small boy in red t-shirt alone, looking lost"
                     → graph engine checks the boy's path is physically possible
                             ▼
 ⑤ ACT               Agent: alert the nearest guard (location + clip + path)
                     Case report: path map, separation clip, cause
                     Over many cases: separation hotspots → recommendations
```

### Components

| Component | What it is | Status |
|---|---|---|
| **Camera topology** | 12 cameras, positions, field of view, walkways in metres | ✅ `demo/mall_topology.json` |
| **Network viewer** | Floor plan, timeline replay, step-by-step search | ✅ `demo/camera-network.html` ([live](https://claude.ai/artifact/HVa3WZ1nZ6RJsJfK1hpYfL)) |
| **CCTV overlay tool** | Camera label + running clock on clips | ✅ `demo/cctv_overlay.sh` |
| **Footage** | ~11 clips following the story timeline | ⏳ to film or generate |
| **Ingest script** | Upload clips to CreativAI with `camera` + `start_time` tags, index them | ⏳ to build |
| **Graph engine** | Neighbours, time windows, beam search, path plausibility | ⏳ to build (Python) |
| **Journey reel builder** | Cuts the matched segments and joins them with ffmpeg | ⏳ to build |
| **Agent** | Claude + CreativAI MCP: runs the case, explains, writes the alert and report | ⏳ to build |
| **Case dashboard** | The viewer, upgraded to show real results and clips | ⏳ to build |

### Where CreativAI is used

| Step | CreativAI feature |
|---|---|
| Store the footage | `media.upload_file` + `confirm_upload(tags=…)` + `indexing.start` |
| Find the group/child in candidate clips | `search.query(…, search_type="hybrid")` |
| "Is the child with them?" for each segment | `data_plates` + `knowledge_extraction.add_columns` |
| Separation moment in the journey reel | `search.query` / `agentic_chat` on the reel collection |
| Guard asks questions | `agentic_chat` ("Where is the boy now? Show me.") |
| The agent's hands | CreativAI MCP server (62 tools) |

---

## 4. Assets & materials

### 4.1 Footage

**Plan A: film it ourselves (recommended, free)**
- **4–6 phones** on tripods or shelves, placed **high (2.5–3 m) and angled down**, landscape, 1080p, all clocks synced (film a phone stopwatch at the start of each recording).
- **A location with corridors and rooms:** a university building, a hall or a friend's office floor. Map it to the camera graph (rename the zones to match). Filming inside a real mall needs written permission from mall management.
- **Cast:** 3 people for the family (an adult can play the "child" in a distinctive outfit), plus 5–10 friends as the crowd, plus one decoy wearing similar clothes.
- **Consent:** a short written OK from everyone filmed, since the video will be shown publicly.

**Plan B: Kling 3.0 via Higgsfield (~$10.40 of ~$15)**
- 11 clips plus 4 spares, prompts ready in `demo/lost-and-found-mall-shotlist.md`.
- Weakness: faces change between clips (clothing usually holds), and the look is a bit "AI".

**Synthetic multi-camera dataset (best one to start testing with, no filming needed)**

| Dataset | What it has | Licence | Use for |
|---|---|---|---|
| **[NVIDIA PhysicalAI-SmartSpaces](https://huggingface.co/datasets/nvidia/PhysicalAI-SmartSpaces/tree/main/MTMC_Tracking_2024)** (the AI City Challenge 2024 data) | Computer-generated indoor spaces (retail-like, warehouse) filmed by **many fixed cameras at once**, with a `video.mp4` + `calibration.json` per camera and the **true path of every person** | **CC BY 4.0** (reuse allowed with credit) | Test the Map + Eyes loop end to end before we have story footage. Download **one scene** (the whole set is ~217 GB). |

**Free stock clips (single camera, for background crowds)**
- **[Mixkit: mall videos](https://mixkit.co/free-stock-video/mall/)**: free, no watermark, Mixkit licence. Good for "other cameras" full of shoppers.
- Pexels and Pixabay also have free mall and crowd videos (search "mall", "shopping center", "Dubai mall"). Check each clip's licence page.

**Free public multi-camera datasets** (real security-style footage, for testing the graph engine and as background)

| Dataset | What it has | Licence | Use for |
|---|---|---|---|
| **[MEVA](https://mevadata.org)** (Kitware/IARPA) | 38 real ground cameras at one facility (indoor + outdoor), actors performing scripted activities, documented camera layout | **CC BY 4.0** (reuse allowed with credit) | **Best match:** a real multi-camera network to run the graph engine on |
| **[CAVIAR](https://homepages.inf.ed.ac.uk/rbf/CAVIARDATA1/)** (EC project, INRIA) | **Shopping-centre corridor in Lisbon**, 2 synced views (along and across), people walking, browsing, entering shops; ground truth included | **CC BY-SA** (credit the CAVIAR project) | Real mall corridor footage; old and low-res (384×288) |
| **[WILDTRACK](https://www.epfl.ch/labs/cvlab/data/data-wildtrack/)** (EPFL) | 7 HD cameras with overlapping views of a busy public area, calibrated | Check the download page (research use) | Testing person matching across overlapping cameras |
| **[MMPTRACK](https://paperswithcode.com/dataset/mmptrack)** (Microsoft) | ~9.6 h, calibrated cameras in **retail, lobby, café, office** scenes, identity labels | Check before use | The closest to a store layout, if available |

| **[EPFL multi-camera pedestrians](https://www.epfl.ch/labs/cvlab/data/data-pom-index-php/)** | Terrace, Passageway, **Laboratory (indoor, 4 cameras)**, Campus; 3–4 synced views, 6–11 people, calibration + some ground truth | Research use (copyright CVLab-EPFL) | Small and easy to start with; low resolution |
| **[MTMMC](https://sites.google.com/view/mtmmc)** (CVPR 2024) | 16 fixed real cameras densely covering a **campus building** and a factory, RGB + thermal | Check the project page | Most realistic building-wide camera network, if access is granted |

⚠️ Avoid **DukeMTMC**: it was withdrawn for privacy reasons. None of these datasets contains a lost-child story or Gulf-style clothing, so they support the demo but can't replace the story footage.

**Mixed option:** use MEVA or CAVIAR clips as the "other cameras" (crowds, cameras with no match) and our own filmed or generated clips for the story cameras. It's realistic, and the system has to ignore the irrelevant cameras.

### 4.2 Accounts & keys
- **CreativAI API key** (`sk_live_…`), plus the welcome credits (`users.claim_welcome_credits()`). ⏳ needed
- **Claude API key** for the agent and the photo → group description step. ⏳ needed
- **Higgsfield** (you have it): only for Plan B.
- **GitHub repo** (this one).

### 4.3 Software
- Python 3.10+, `creativai` SDK, `anthropic` SDK, `ffmpeg`.
- Optional later: an open-source person detector + Re-ID model (e.g. YOLO + OSNet) as an extra matching signal.

---

## 5. Build plan

| Phase | Output | Depends on |
|---|---|---|
| **0. Footage** | 11 story clips, renamed `CAM_HHMMSS.mp4`, overlays added | Plan A or B |
| **1. Ingest** | All clips in one CreativAI collection with camera/time tags; test 5 manual searches | CreativAI key |
| **2. Graph engine** | Python module: given a sighting, return candidate (camera, window) pairs; beam search over CreativAI hits | topology ✅ |
| **3. Separation + sweep** | Journey reel + "child no longer with them" query + zone sweep for the child | 1, 2 |
| **4. Agent + dashboard** | Case flow end to end; dashboard shows path, clips, alert, report | 3 |
| **5. Demo** | A 3-minute screen recording + a live run + pitch slides | 4 |

**First checks once we have a CreativAI key** (they decide details of phase 2):
1. Does each search hit return the clip name and its time inside the clip? (needed to get absolute time)
2. Can search be limited to tagged clips (one camera), or do we filter afterwards?
3. How long does indexing take for one 15-second clip? (decides "minutes, not hours")
4. Can a photo be used as a search query?

---

## 6. Risks & how we handle them

| Risk | Plan |
|---|---|
| Lookalike clothing (abayas, thobes) | Group signature + the child's clothes + geometry/time windows |
| CreativAI can't filter by camera | Filter hits after search using tags or file names |
| AI-generated clips look inconsistent | Prefer Plan A (self-filmed); with Kling, use reference stills and fixed outfit text |
| Privacy | Search only when a case is open, consent for faces, delete case data after closing, no permanent face database |
| Budget (Kling) | 11 clips + 4 spares; shorter 8–10 s clips if billing is per second |

---

## 7. Files in this repo

| Path | What |
|---|---|
| `PROJECT.md` | This plan |
| `demo/prompts/` | **Every prompt to generate**: characters, Case A, Case B (blind test), extras, negative prompt, CreativAI questions |
| `demo/test-plan.md` | Two cases + trick clips + the blind-test rule |
| `demo/game-plan.html` | Game plan page with copy buttons ([live](https://claude.ai/artifact/2jrYuhKgMx3jxgKuhXANSf)) |
| `demo/mall_topology.json` | Camera network + ground-truth story timeline |
| `demo/camera-network.html` | Interactive viewer ([live](https://claude.ai/artifact/HVa3WZ1nZ6RJsJfK1hpYfL)) |
| `demo/lost-and-found-mall-shotlist.md` | 11-clip shot list with prompts (Plan B / filming script for Plan A) |
| `demo/graph-tracking-method.md` | Graph search method in detail |
| `demo/cctv_overlay.sh` | Adds the camera label + clock to clips |
| `concepts/system-architecture.md` | Why tracking + CreativAI; lookalike clothing; legal notes |
| `concepts/lost-and-found.md`, `concepts/guardian-at-home.md` | Original concept docs (Guardian at Home is parked for later) |
| `IDEAS.md` | The brainstorm |

---

## Current status & next step (for a new session)

- ✅ Plan, camera map, two cases, trick clips, blind-test rule, all prompts (`demo/prompts/`).
- ✅ Higgsfield auth is a **network secret** on host `platform.higgsfield.ai`: the proxy adds `Authorization: Key KEY_ID:KEY_SECRET` by itself, so call the API **without** an auth header and never read the key. Docs: https://docs.higgsfield.ai/docs/authentication. (A plain `HIGGSFIELD_API_KEY` env var was added earlier and should be removed.) CreativAI will be set up the same way, on host `ws.creativai-apis.com` with the header `X-API-Key`. They also need to allow-list `higgsfield.ai` (and subdomains), `creativ-ai.com` and `creativai-apis.com` under Network access. `CREATIVAI_API_KEY` comes later.
- **User's instruction: do NOT run a separate test call with the key.** The first API call is real work: generating the character pictures.

### Next, in this order
1. **Character pictures** (image credits, not video credits). Model: **Nano Banana Pro** (`nano_banana_pro`, 2k).
   - For each of the 7 characters in `demo/prompts/01-characters.md`, generate the **reference sheet** first (aspect 16:9).
   - Then generate the **front** and **back** photos (aspect 2:3), passing the sheet as an `image_references` input, so all three show the same person.
   - Save to `demo/assets/characters/<KEY>_{sheet,front,back}.png`, look at each one, and redo any that don't match the description.
   - Commit and push, then show the user the pictures.
2. **Ask the user's OK**, then generate **A1 + A3 only**. Model: **Kling 3.0 Omni** (`kling_o3_image_reference`, up to 7 reference images = our characters).
   - Settings: 16:9, 15 s, mode `std`, sound `off` (cheaper, audio not needed).
   - Use the prompt text from `02-clips-case-A.md`. Replace the `@Tag` mentions by referring to the reference images in order, e.g. "the father is the man in image 1".
   - Save to `demo/raw/case-A/`.
3. Early CreativAI test on A1 + A3 (needs `CREATIVAI_API_KEY`).
4. The rest, in the order in `demo/prompts/README.md`.

**Budget rule:** at most **15 videos** in total, and ask the user before every paid video batch. The Higgsfield connector showed a free web account with 10 credits; the user says the API key's account holds the paid credit. Check the balance through the API before the first video.

### CreativAI credits (from their pricing page)
- **Plan: Free**, with 2,500 welcome credits and unlimited searches. Our expected total use is about 1,000–1,500 credits:
  - video-only indexing of 3.5 min ≈ 25 credits per pass
  - knowledge extraction ≈ 3 credits per 16 s segment per run
  - agentic chat ≈ 6 credits per query
- **Use video-only indexing.** Our clips are generated with sound off, and multimodal indexing is a Plus feature.
- **If credits run out:** a one-time top-up of $10 = 5,000 credits. Only take Plus (50% student discount, so $10/month) if basic indexing turns out too weak in the early test.

### API facts verified in this session
- **CreativAI works:** base URL `https://ws.creativai-apis.com` (pass `base_url` to the SDK; its default `creativai-apis.com` doesn't get the key). The account has **2,500 credits**.
- **Higgsfield API base is `https://api.higgsfield.ai`**, not platform.higgsfield.ai. The network secret must target `api.higgsfield.ai`; until then the API answers 401.
- **Higgsfield models via the API:**
  - Images: **Soul V2** `POST /higgsfield-ai/soul/v2/standard`. Nano Banana is **not** in the API catalog.
  - Kling 3.0:
    - `/kling-video/v3.0-turbo/{text,image}-to-video` (budget; no sound or elements field; 720p default; 3–15 s)
    - `/kling-video/v3.0/std/{text,image}-to-video` (`sound` off/on; `elements` = Kling element IDs)
  - Character references: `/kling-video/o3/image-reference` (Kling 3.0 Omni, `image_urls`, sound off by default)
  - Free price check: `POST /estimate/<endpoint>` with the same body. Uploads: `POST /files/generate-upload-url`, then a PUT to the presigned URL. Poll `status_url`.

### Higgsfield key: final setup
- The Higgsfield **network secret didn't work** (401 even after its host was changed to `api.higgsfield.ai`). The user replaced it with an **environment variable** `HIGGSFIELD_API_KEY` holding the whole `KEY_ID:KEY_SECRET` string.
- Send it yourself: `Authorization: Key $HIGGSFIELD_API_KEY` to `https://api.higgsfield.ai`. Never print the key.
- First call: `POST /estimate/...` (free) for Kling 3.0 Turbo / Std (sound off) / O3 image-reference and Soul V2. Then **generate the first character picture right away** (BOY_A). The user doesn't want a separate key test.
- CreativAI stays a network secret on `ws.creativai-apis.com` (works; 2,500 credits).

### Session 2026-10-11: models chosen and character sheets done
- **API key works** (`HIGGSFIELD_API_KEY` user env var, `Authorization: Key …`). Full model list: `GET https://api.higgsfield.ai/models` (85 models). Free price check: `POST /estimate/<slug>` (16 credits = $1).
- **Images: Qwen Image 3** (`alibaba/qwen-image-3/text-to-image`, ~0.64 credits/picture). Soul V2 (0.09 credits) can't draw young children (it gave an adult, then a teenager), so it's not used. Qwen gives 1280×720 for 16:9.
- **All 7 character sheets are done:** `demo/assets/characters/<KEY>_sheet.png`. The `.url` files next to them hold the hosted image URL to pass as `image_urls`. GirlB's prompt needed "Saudi Arab girl" added (without it she came out East Asian).
- **Front/back photos skipped for now:** the plan is to pass the sheets straight to the video model, and only make front photos if the first clip shows the model treating a 3-view sheet as 3 people.
- **Video model: Kling O3 image-reference, mode std, sound off** (`kling-video/o3/image-reference`):
  - **~1.14 credits per second** (5 s = 5.7, 15 s = 17.1 credits, about $1.07). Price doesn't depend on the number of reference images. Pro mode or sound on = 22.8 credits for 15 s.
  - Compared (15 s unless noted): Grok Imagine 1.5 ref 19.7; Wan 2.7 ref 13.6 for 10 s max; Kling Omni ref 15.2 for 10 s max; Happy Horse 1.1 ref 36.7; Wan 3.0 ref $0.10/s at 720p. Seedance 2.x, MiniMax H3 and Wan 2.6 reference modes require a reference *video*, so they don't fit.
  - Kling 3.0 Std text/image-to-video is cheaper (10.1 credits for 15 s) but takes only one start image, so it can't hold 2–3 characters consistent.

### Session 2026-10-11 (later): case A clips, CreativAI ingest, first searches
- **All 14 clips generated** (A1–A8, B1–B6) for $14.11 in total; the user approved case A. Clips are local in `demo/raw/` (not committed, ~130 MB). Case B is untouched (blind test).
- **CreativAI key works** (`CREATIVAI_API_KEY` user env var, header `X-API-Key`, base `https://ws.creativai-apis.com/api/v2`, full spec at `/openapi.json`). 2,500 credits, free plan.
- **Ingest done** with `demo/pipeline/ingest.js` + `clips-case-A.json`: collection `lostfoundcasea_d47c1295`, A1–A6 tagged `camera:<id>` and `clip:<id>`, metadata `camera`, `start_time`, `start_sec`. Indexing cost 10 credits and took ~3 min.
- **Answers to the "first checks" in section 5:**
  1. Hits return the clip, but **CreativAI cuts videos into 16 s chunks, so a 15 s clip is one chunk**: every hit is "0–15 s", with no second inside the clip. Exact timing has to come from data plates / agentic chat, not search.
  2. **Filtering by camera works**: `tags: ["camera:fc-01", ...]` limits results to those cameras.
  3. Indexing 6 × 15 s took ~3 min.
  4. Image queries need a `multimodal` collection (ours is `video_only`).
- **Search ranking is weak on these clips:** scores are rank-fusion values (~0.030–0.033) that barely differ, and the default `min_score` hides everything (pass `min_score: 0`). Q1 (family arriving): A1 #2. Q3 (separation): A3 #2. Q4 (boy alone): A4 #5, A5 #4, so it fails top-3. Search alone can't be the Eyes; it can only narrow down by camera tag, and yes/no questions per clip need data plates or agentic chat.

### Session 2026-10-11 (end): the agent, the case console and the README — shipped
- **Built:** `graph.js` (the Map), `eyes.js` (CreativAI data plates + questions, cached), `find-child.js` (the agent), `server.js` + `case.html` (the case console), `package.json` scripts, and a portfolio **README** with the use case, how it works, results, limits and a tutorial.
- **Case A solved end to end:** separation STR-B 14:19:04, child now FC-02, lookalike family ruled out; A4 wrongly ruled out (wide atrium shot). First run ~3 min / ~27 CreativAI credits; reruns are free from the cache, and need no key.
- **Decision (user): the case B blind test is dropped.** B1–B6 exist locally but were never uploaded or run; the README says so.
- **Not committed:** the 14 clips in `demo/raw/` (gitignored), pending the user's choice of whether to publish them.
