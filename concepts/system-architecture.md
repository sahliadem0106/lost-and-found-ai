# Lost & Found: system architecture (v3)

## Is this already solved?
Partly, and that's good news, because the hard part has known methods.

- **Following one person across many cameras** is a known research field called **multi-camera tracking** and **person re-identification (Re-ID)**. There are open-source models (FastReID, OSNet/torchreid) and yearly benchmarks (the AI City Challenge multi-camera tracking track).
- **Commercial security products** already offer "appearance search" (find this person on all cameras): Avigilon, BriefCam, Genetec, Milestone. BriefCam's "video synopsis" even packs a person's appearances into one short video.
- **Your "space geometry" idea** is also a standard technique, known as **camera link models** or **spatio-temporal constraints**:
  - Each camera's frame has **exit zones**: leaving on the left edge means the next camera must be COR-W.
  - Each pair of cameras has a **transit-time distribution**, learned from normal days.
  - Movement direction and speed carry over between cameras.

  This is what lets trackers tell apart people who look alike.

**What isn't solved:** these systems answer *where was this person*. They don't answer *what happened*:
- *When did the child stop being with them?*
- *Why did they separate?*
- *Is the child alone and upset?*
- *Find a boy in a red shirt when we have no photo of him.*

That part is language and understanding, and it's where CreativAI fits.

## The three layers

```
┌────────────────────────────────────────────────────────────────────┐
│ 1. ENROL (at the entrance gates)                                   │
│    Close-range gate camera: face + full-body + GROUP composition   │
│    → visit record  {visit_id, time_in, people:[man, woman, boy]}   │
└───────────────┬────────────────────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────────────────────┐
│ 2. TRACK (classic computer vision: "WHERE")                        │
│    person detection + Re-ID per camera                             │
│    + camera graph, exit zones, transit-time priors                 │
│    → path:  ENT-01 → ATR-01 → COR-W → STR-A → … → INF-01           │
│    → list of video segments where this group appears               │
└───────────────┬────────────────────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────────────────────┐
│ 3. UNDERSTAND (CreativAI: "WHAT, WHEN, WHY")                       │
│    index ONLY the group's segments  → "journey reel"               │
│    ask: "When is the child no longer with them?"                   │
│         "What were the parents doing at that moment?"              │
│    then index the cameras of THAT ZONE after that moment:          │
│         "small boy in red t-shirt alone, looking lost"             │
│    guard chat: "Where is the boy now? Show me."                    │
└───────────────┬────────────────────────────────────────────────────┘
                ▼
      Agent: dispatch nearest guard, case report, cause statistics
```

### Why this split works
- **Layer 2 is cheap and precise for "where."** It's built for that, and its output narrows the problem from *all cameras for 30 minutes* to *about 10 short segments*.
- **Layer 3 only processes the footage that matters** (your idea of importing only the relevant sections). That keeps the cost low, and the questions are language questions that a Re-ID model can't answer.
- **Two levels of search** (your "sub-domain"): first the **zone** where the separation happened, then **all the cameras inside that zone** after that time.

## The "everyone wears the same clothes" problem (KSA/UAE)
Black abayas and white thobes make single-person appearance matching weak. What still works:

1. **Track the group, not the individual.** *Man in thobe + woman in abaya + small boy + green shopping bag* is close to unique, even if each person alone isn't.
2. **Children aren't in uniform.** The kid's clothing is usually the most distinctive thing in the group. Track him through the group, then on his own.
3. **Small details:** a red vs. white shemagh, shoes, handbag, stroller, shopping bags, height difference, walking speed.
4. **Faces at the gates:** entrances are the only places where cameras are close and people face them, so that's where a face is useful.
5. **Geometry and time (your point, and the strongest cue):** which edge of the frame they left by, their speed, and the transit time to the next camera. Among 40 men in white thobes, usually only one or two are at the right camera at the right second.

A note on "women near clothing shops": guessing where people go from their gender is a weak signal and gives biased results. Movement direction and time are much stronger and fair, so use those.

## Faces: legal side
Data-protection laws in the Gulf treat **biometric data as sensitive**. A mall-run face database needs a legal basis, notice, short retention and security. A safer design for the demo:
- no stored faces of everyone
- the **parents consent** at the security desk, and the system matches them against today's footage only
- the case data is deleted when the case is closed

## What to build for the demo
The goal is to show CreativAI, so:
- **Layer 1–2 (simplified):** use the known camera graph and clips that are already labelled with camera and time. You can show the path-finding with the scripted tracker in `demo/camera-network.html`. Mention that a real deployment uses an existing Re-ID tracker here.
- **Layer 3 (the real CreativAI part, done for real):**
  1. upload the family's clips → *"When does the child stop being with the parents?"* → the STR-B moment
  2. upload the separation zone's clips after 14:19 → *"small boy alone, red shirt, looking lost"* → FC-02
  3. guard chat over the case: *"Where is the boy and how did he get there?"*
- **Pitch:** *"Trackers tell you where someone went. CreativAI tells you what happened, and finds the child from a sentence."*
