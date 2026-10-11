# Lost & Found demo: footage plan (v2, timeline-based)

> ⚠️ **Superseded.** The current prompts (two cases, trick clips, 15-credit plan) are in [`demo/prompts/`](prompts/README.md).

The mall has a **real camera network**: 12 fixed cameras connected by walkways (`mall_topology.json`). Each clip we generate is a **recording from one of those cameras at a specific time**. Together they tell one story across 30 minutes, the way a security team would actually see it. No two clips show the same moment.

Budget: Kling 3.0 via Higgsfield, ~$0.945 per 15 s clip, ~$15 total.
Plan: **11 clips (~$10.40) + 4 spares (~$3.80).**

## The camera network

```
 ┌──────────────┬──────────────┬──────────────┐
 │  STR-A       │  STR-B       │  STR-C       │
 │ Fashion House│  TechZone    │  ToyLand     │
 └──────┬───────┴──────┬───────┴──────┬───────┘
        │              │              │
 ═══ COR-W ═════════ ATR-01 ═════════ COR-E ═══ ENT-02 (parking)
        │           │      │          │     │
     FC-01        ENT-01  INF-01 ─────┘   WC-01
   (seating)     (main   (info &
        │       entrance) security)
     FC-02
   (counters)
```
Each line is a walkway with a known length. That gives the minimum and maximum time a person can take to get from one camera to the next, which is the basis of the graph search.

## The characters

Paste these descriptions **word for word** in every prompt. AI video won't keep faces identical between clips, but it keeps **clothing** well. That's also what a real system would use (see the method doc).

- **[FATHER]** *a tall Gulf Arab man in his 40s wearing a white thobe and a red-and-white checkered shemagh, black sandals, carrying a dark green shopping bag*
- **[MOTHER]** *a woman in a black abaya with a light grey headscarf, carrying a beige handbag*
- **[BOY]** *a 6-year-old boy with short black hair in a bright red t-shirt, blue jeans and white sneakers*

**Style block for every prompt:**
> *Security camera footage. Fixed ceiling-mounted CCTV camera, high angle looking down about 40 degrees, wide-angle lens with slight fisheye, completely static camera, no camera movement, no zoom. Modern shopping mall, bright LED lighting, polished floor, realistic everyday crowd. Slightly soft surveillance video quality. No on-screen text.*

## The timeline: what we generate

| # | Time | Camera | What happens (prompt after the style block) | Role in the demo |
|---|---|---|---|---|
| 1 | 14:02:00 | **ENT-01** Main entrance | Shoppers walk in through glass sliding doors. [FATHER], [MOTHER] and [BOY] enter together, the boy holding his mother's hand, and walk past the camera into the mall. | Start of the family's path. The boy's look is captured here |
| 2 | 14:08:00 | **STR-A** Fashion House | Inside a clothing store with racks of dresses. [MOTHER] browses a rack while [BOY] stands close, holding her abaya. [FATHER] waits nearby holding the shopping bag. | Family together (with child) |
| 3 | 14:18:50 | **STR-B** TechZone | Electronics store with phone display tables. [FATHER] tests a phone at a display table, [MOTHER] talks on her mobile phone, turned away. [BOY] gets bored, wanders between the tables toward the store entrance and walks out of frame alone. Neither parent notices. | ⭐ **The separation moment** |
| 4 | 14:20:00 | **ATR-01** Atrium | Wide atrium with a fountain and crowds crossing. [BOY] walks alone across the atrium, looking around. | Boy's path |
| 5 | 14:21:00 | **COR-W** West corridor | Long corridor with shopfronts. [BOY] walks alone slowly toward the food court, looking left and right. | Boy's path |
| 6 | 14:23:00 | **FC-02** Food court counters | Busy food court with restaurant counters and queues. [BOY] stands still alone next to a counter, looking around anxiously, almost crying. Adults queue around him without noticing. | **The lost child**, still there now |
| 7 | 14:25:00 | **COR-E** East corridor | [FATHER] and [MOTHER] hurry along the corridor in the opposite direction, looking around in a panic. The mother calls out and the father checks behind pillars. | Parents searching **the wrong way** |
| 8 | 14:27:00 | **INF-01** Info & security desk | Mall security desk. [FATHER] and [MOTHER] speak urgently to a uniformed guard and show a child's height with a hand. The guard holds up a tablet and takes a photo of the father. | ⭐ **The report + "scan"**: the start of the search |
| 9 | 14:10:00 | **ENT-01** Main entrance | Another family enters: a man in a grey thobe, a woman in a black abaya, and a boy around 8 in an **orange** t-shirt and black shorts. | **Decoy** (similar family) |
| 10 | 14:22:00 | **FC-01** Food court seating | Families eating at tables. A boy in a red t-shirt sits **with his parents** eating fries. | **Decoy** (red shirt, but not alone and wrong boy) |
| 11 | 14:33:00 | **FC-02** Food court counters | The guard walks in with [FATHER] and [MOTHER]. The mother runs to [BOY] and hugs him. | Reunion (ending) |
| 12–15 | | | Spares for failed generations | |

Cameras STR-C, WC-01 and ENT-02 get **no clips**. That's realistic: most cameras show nothing relevant, and the system has to rule them out.

## Overlays (camera name + running clock)
```bash
./demo/cctv_overlay.sh raw/03.mp4 final/STR-B_1418.mp4 "STR-B TECHZONE" "2026-10-12 14:18:50"
```
Name each final file `<CAMERA>_<HHMM>.mp4`. The tracker reads the camera and the start time from the filename and tags.

## Generation tips
- Make **one still image of each character** (cheap image model) and use it as the reference or start frame for every clip that character is in.
- Write "static camera, no camera movement" in the prompt. If a clip pans or zooms, regenerate it.
- Keep each camera's look consistent: clips 1 and 9 (ENT-01) and clips 6 and 11 (FC-02) are the same camera at different times. Generate a still of the **empty scene** first and use it as the start frame for both.
- If Higgsfield bills per second, 8–10 s clips are enough and almost double your budget.
